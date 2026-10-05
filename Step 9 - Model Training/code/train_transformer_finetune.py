"""
Step 9c -- transformer fine-tuning (MentalBERT / DistilBERT). HANDOFF SCRIPT
-- NOT run in this sandbox (2 vCPUs, no GPU; see item 33 in the paper-details
doc). Ready to run as-is on Colab or any CUDA machine with `transformers`,
`datasets`, `torch`, `scikit-learn`, `pandas` installed.

Input text: Step 5's `text` column (Step 4's CLEANED text -- case and
punctuation intact), deliberately NOT `text_lemmatized`. Transformer
tokenizers (WordPiece/BPE) build their own subword vocabulary and expect
natural casing/punctuation; feeding them Step 5's lemmatized, lowercased,
punctuation-stripped tokens would throw away information the pretrained
model already knows how to use (case carries signal -- "I'M AT THE EDGE" vs
"i'm at the edge") and doesn't match the distribution the model was
pretrained on. This is the one place in the whole pipeline where Step 5's
output is deliberately NOT used.

Excludes Step 6's garbage-flagged rows, same as Steps 7-9's other models.

Usage:
    python train_transformer_finetune.py primary   # 7-class
    python train_transformer_finetune.py urgency    # binary

Swap MODEL_NAME to try MentalBERT vs DistilBERT vs MentalRoBERTa -- default
is MentalBERT (mental/mental-bert-base-uncased), a BERT further pretrained
on mental-health-subreddit text, which is why it's the first choice over
plain DistilBERT for this specific task.
"""
import sys
import json
import numpy as np
import pandas as pd
import torch
from pathlib import Path
from sklearn.metrics import f1_score, classification_report, confusion_matrix
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    Trainer, TrainingArguments, DataCollatorWithPadding,
)
from datasets import Dataset

MODEL_NAME = "mental/mental-bert-base-uncased"  # fallback: "distilbert-base-uncased"
MAX_LENGTH = 256
REPO_ROOT = Path(__file__).resolve().parents[2]
IN_DIR = REPO_ROOT / "Step 5 - Text Preprocessing" / "output"
GARBAGE_PATH = REPO_ROOT / "Step 6 - EDA on Cleaned Data" / "findings" / "garbage_flagged_rows.csv"
WEIGHTS_PATH = REPO_ROOT / "Step 8 - Class Imbalance Handling" / "output" / "class_weights.json"
OUT_DIR = REPO_ROOT / "Step 9 - Model Training" / "output"

DATASETS = {
    "primary": {
        "file": "primary_dataset_clean_preprocessed.csv",
        "name": "primary_dataset",
        "classes": ["Normal", "Depression", "Suicidal", "Anxiety", "Bipolar",
                    "Stress", "Personality disorder"],
    },
    "urgency": {
        "file": "urgency_dataset_clean_preprocessed.csv",
        "name": "urgency_dataset",
        "classes": ["non-suicide", "suicide"],
    },
}


class WeightedTrainer(Trainer):
    """Applies Step 8's class weights to the cross-entropy loss."""
    def __init__(self, *args, class_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        loss_fct = torch.nn.CrossEntropyLoss(weight=self.class_weights.to(logits.device))
        loss = loss_fct(logits, labels)
        return (loss, outputs) if return_outputs else loss


def main(dataset_key):
    cfg = DATASETS[dataset_key]
    classes = cfg["classes"]
    label2id = {c: i for i, c in enumerate(classes)}

    df = pd.read_csv(f"{IN_DIR}/{cfg['file']}")
    garbage_df = pd.read_csv(GARBAGE_PATH)
    garbage_texts = set(
        garbage_df.loc[garbage_df["dataset"] == cfg["name"], "text"].astype(str)
    )
    df = df[~df["text"].astype(str).isin(garbage_texts)].reset_index(drop=True)
    df["label_id"] = df["label"].map(label2id)

    with open(WEIGHTS_PATH) as f:
        w = json.load(f)[cfg["name"]]["class_weights_train"]
    class_weights = torch.tensor([w[c] for c in classes], dtype=torch.float32)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=MAX_LENGTH)

    splits = {}
    for split_name in ("train", "val", "test"):
        sub = df[df["split"] == split_name][["text", "label_id"]].rename(columns={"label_id": "labels"})
        ds = Dataset.from_pandas(sub, preserve_index=False)
        splits[split_name] = ds.map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=len(classes))
    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    args = TrainingArguments(
        output_dir=f"{OUT_DIR}/transformer_{cfg['name']}",
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        num_train_epochs=4,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        fp16=torch.cuda.is_available(),
        logging_steps=100,
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=1)
        return {"f1_macro": f1_score(labels, preds, average="macro")}

    trainer = WeightedTrainer(
        model=model, args=args,
        train_dataset=splits["train"], eval_dataset=splits["val"],
        data_collator=collator, compute_metrics=compute_metrics,
        class_weights=class_weights,
    )
    trainer.train()

    test_pred = trainer.predict(splits["test"])
    preds = np.argmax(test_pred.predictions, axis=1)
    labels = test_pred.label_ids
    macro_f1 = f1_score(labels, preds, average="macro")
    report = classification_report(labels, preds, target_names=classes, output_dict=True, zero_division=0)
    cm = confusion_matrix(labels, preds).tolist()

    with open(f"{OUT_DIR}/metrics/{cfg['name']}_transformer.json", "w") as f:
        json.dump({
            "model_name": MODEL_NAME, "macro_f1_test": macro_f1,
            "report_test": report, "confusion_matrix_test": cm, "labels_order": classes,
        }, f, indent=2, default=str)

    trainer.save_model(f"{OUT_DIR}/models/{cfg['name']}_transformer_best")
    tokenizer.save_pretrained(f"{OUT_DIR}/models/{cfg['name']}_transformer_best")
    print(f"[{cfg['name']}] test macro-F1 = {macro_f1:.4f}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "primary"
    main(target)
