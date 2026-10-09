"""Offline, evaluation-only encoder/classifier comparison on synthetic data.

Never imports api/.env. No tuning on validation or consumed holdout data.
The encoder is not a safety classifier; fitted logits are research outputs,
not clinical probabilities. Subject/time remain outside this experiment.
"""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Step 12 - Packaging/package'))
sys.path.insert(0, str(ROOT))
from mental_health_screening.safety import evaluate, POLICY_VERSION
from scripts.source_fingerprint import fingerprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer
    from sklearn.linear_model import LogisticRegression
    art = Path(args.artifacts)
    manifest = json.loads((art / 'manifest.json').read_text())
    for name, expected in manifest['hashes'].items():
        if hashlib.sha256((art / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Artifact fingerprint mismatch')
    start = time.perf_counter()
    tokenizer = Tokenizer.from_file(str(art / 'tokenizer.json'))
    tokenizer.no_truncation()
    tokenizer.enable_padding()
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    opts.inter_op_num_threads = 1
    session = ort.InferenceSession(str(art / 'onnx/model.onnx'), opts,
                                   providers=['CPUExecutionProvider'])
    cold_load_ms = (time.perf_counter() - start)*1000
    def encode(text):
        enc = tokenizer.encode(text)
        if len(enc.ids) > 256:
            raise ValueError('Evaluation encoder input exceeds 256 wordpieces; not truncated')
        values = dict(input_ids=np.array([enc.ids], dtype=np.int64),
                      attention_mask=np.array([enc.attention_mask], dtype=np.int64),
                      token_type_ids=np.array([enc.type_ids], dtype=np.int64))
        output = session.run(None, {i.name: values[i.name] for i in session.get_inputs()})[0]
        mask = values['attention_mask'][...,None]
        pooled = (output*mask).sum(1)/np.maximum(mask.sum(1),1)
        return pooled[0]/np.maximum(np.linalg.norm(pooled[0]),1e-9)
    dataset_path = ROOT / 'evaluation/semantic-development-v1.json'
    dataset = json.loads(dataset_path.read_text())
    development = [c for c in dataset['cases'] if c['split']=='development']
    validation = [c for c in dataset['cases'] if c['split']=='validation']
    normalize = lambda text: ' '.join(text.casefold().split())
    known = {}
    for name in ('cases','expansion','holdout','holdout2'):
        for c in json.loads((ROOT / f'tests/safety_corpus/{name}.json').read_text())['cases']:
            known[normalize(c['input'])] = c['case_id']
    overlaps = [c['case_id'] for c in dataset['cases'] if normalize(c['input']) in known]
    dev_texts = {normalize(c['input']) for c in development}
    split_overlap = [c['case_id'] for c in validation if normalize(c['input']) in dev_texts]
    if overlaps or split_overlap:
        raise ValueError('Exact normalized split/corpus overlap found')
    X = np.stack([encode(c['input']) for c in development])
    classifier = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    classifier.fit(X, [c['label'] for c in development])
    rows=[]
    for c in validation:
        start=time.perf_counter()
        vector=encode(c['input'])
        prediction=str(classifier.predict([vector])[0])
        scores=classifier.decision_function([vector])[0]
        latency=(time.perf_counter()-start)*1000
        baseline=evaluate(c['input'],urgency_flagged=False)
        baseline_label=('urgent' if baseline.level in {'HIGH','IMMEDIATE'} else
                        'concerning' if baseline.level in {'CONCERNING','NEEDS_CLARIFICATION'} else 'benign')
        rows.append(dict(case_id=c['case_id'],expected=c['label'],baseline=baseline_label,
                         baseline_level=baseline.level,candidate=prediction,
                         logits={str(k):float(v) for k,v in zip(classifier.classes_,scores)},
                         latency_ms=latency))
    def metrics(name):
        urgent=[r for r in rows if r['expected']=='urgent']
        benign=[r for r in rows if r['expected']=='benign']
        return dict(total=len(rows),correct=sum(r[name]==r['expected'] for r in rows),
                    urgent_total=len(urgent),urgent_detected=sum(r[name]=='urgent' for r in urgent),
                    benign_total=len(benign),benign_urgent_escalations=sum(r[name]=='urgent' for r in benign),
                    mismatches=[r['case_id'] for r in rows if r[name]!=r['expected']])
    latency=sorted(r['latency_ms'] for r in rows)
    report=dict(candidate='MiniLM embeddings + LogisticRegression C=1, seed=42, argmax',
                enabled_in_production=False,independent_final_evaluation=False,clinically_reviewed=False,
                training_method='Frozen published encoder; classifier fitted on developer development rows only',
                validation_tuning=False,policy_version=POLICY_VERSION,
                artifact=manifest,data_version=dataset['version'],
                data_sha256=hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
                development_count=len(development),validation_count=len(validation),
                development_labels=dict(Counter(c['label'] for c in development)),
                exact_existing_corpus_overlaps=overlaps,exact_split_overlap=split_overlap,
                near_duplicate_review='Families share support concepts; this is synthetic engineering data, not independent samples',
                metrics={name:metrics(name) for name in ['baseline','candidate']},results=rows,
                runtime=dict(python=platform.python_version(),platform=platform.platform(),
                             packages={n:importlib.metadata.version(n) for n in ['onnxruntime','tokenizers','numpy','scikit-learn']}),
                measurements=dict(concurrency=1,provider='CPUExecutionProvider',intra_op_threads=2,
                                  cold_load_ms=cold_load_ms,cold_load_samples=1,
                                  warm_samples=len(latency),p50_ms=float(np.median(latency)),
                                  p95_ms=latency[min(len(latency)-1,int(len(latency)*.95))],
                                  p99_ms=latency[min(len(latency)-1,int(len(latency)*.99))],
                                  quantile='sorted floor(n*q) index, capped; median p50',
                                  max_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
                source_fingerprint=fingerprint(ROOT),limitations=[
                    'No validated subject/time/capability assessment',
                    'No calibration, clinical probability or generalization claim',
                    'No final evaluation or external review',
                    'English short inputs only; >256 wordpieces rejected',
                    'Model-card training-data licensing not independently established'])
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['metrics'],indent=2))
    print(json.dumps(report['measurements'],indent=2))


if __name__=='__main__':
    main()
