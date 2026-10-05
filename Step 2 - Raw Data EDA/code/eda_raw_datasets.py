import pandas as pd
import numpy as np
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "datasets" / "text datasets"

ENGLISH_STOPWORDS = set("""the a an is are was were be been being to of and in on for with
that this it as at by from or but not have has had do does did i you he she we they
my your his her our their me him them what which who whom this these those am""".split())

def word_tokens(s):
    return re.findall(r"[a-zA-Z']+", str(s).lower())

def eda(name, df, text_col, label_col, sample_n=3000):
    print(f"\n{'='*70}\n{name}\n{'='*70}")
    n = len(df)
    print(f"rows: {n:,}")

    # missing / empty text
    empty_mask = df[text_col].isna() | (df[text_col].astype(str).str.strip() == "")
    print(f"empty/NaN text rows: {empty_mask.sum():,} ({empty_mask.mean()*100:.2f}%)")

    # exact duplicate text rows
    dup_mask = df[text_col].astype(str).duplicated(keep=False)
    print(f"exact duplicate text rows: {dup_mask.sum():,} ({dup_mask.mean()*100:.2f}%)")

    # removed/deleted junk markers (common on Reddit exports)
    junk_pat = re.compile(r"^\s*\[(removed|deleted)\]\s*$", re.IGNORECASE)
    junk_mask = df[text_col].astype(str).str.match(junk_pat)
    print(f"'[removed]'/'[deleted]' rows: {junk_mask.sum():,} ({junk_mask.mean()*100:.2f}%)")

    # text length in words
    lengths = df[text_col].astype(str).apply(lambda s: len(word_tokens(s)))
    print(f"word length -> min:{lengths.min()} max:{lengths.max()} mean:{lengths.mean():.1f} "
          f"median:{lengths.median():.0f} p95:{lengths.quantile(0.95):.0f}")
    very_short = (lengths <= 2).sum()
    print(f"very short (<=2 words) rows: {very_short:,} ({very_short/n*100:.2f}%)")

    # quick English-likelihood heuristic on a sample
    sample = df[text_col].astype(str).sample(min(sample_n, n), random_state=42)
    def english_ratio(s):
        toks = word_tokens(s)
        if not toks:
            return 0.0
        hits = sum(1 for t in toks if t in ENGLISH_STOPWORDS)
        return hits / len(toks)
    ratios = sample.apply(english_ratio)
    likely_non_english = (ratios == 0).mean()
    print(f"sample rows (n={len(sample)}) with ZERO common-English-stopword hits: "
          f"{likely_non_english*100:.2f}% (rough non-English / junk proxy)")

    # class balance
    print(f"\nclass distribution ({label_col}):")
    vc = df[label_col].value_counts()
    for k, v in vc.items():
        print(f"  {k:<25} {v:>8,}  ({v/n*100:5.1f}%)")
    print(f"  imbalance ratio (largest:smallest): {vc.max()/vc.min():.1f} : 1")

    return {
        "rows": n, "empty": int(empty_mask.sum()), "dupes": int(dup_mask.sum()),
        "junk_markers": int(junk_mask.sum()), "very_short": int(very_short),
        "len_mean": float(lengths.mean()), "len_median": float(lengths.median()),
        "class_counts": vc.to_dict(),
    }

results = {}

df1 = pd.read_csv(f"{DATA_DIR}/Combined Data.csv")
results["Combined Data.csv"] = eda("Combined Data.csv (primary, 7-class)", df1, "statement", "status")

df2 = pd.read_csv(f"{DATA_DIR}/Suicide_Detection.csv/Suicide_Detection.csv")
results["Suicide_Detection.csv"] = eda("Suicide_Detection.csv (urgency layer)", df2, "text", "class")

df3 = pd.read_csv(f"{DATA_DIR}/Emotion_Sentiment_DataSet.csv")
text_col3 = "Text" if "Text" in df3.columns else df3.columns[1]
label_col3 = "Emotion" if "Emotion" in df3.columns else df3.columns[-1]
results["Emotion_Sentiment_DataSet.csv"] = eda("Emotion_Sentiment_DataSet.csv (10-class emotion)", df3, text_col3, label_col3)

print("\n\nDONE")
