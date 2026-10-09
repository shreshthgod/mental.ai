"""Explicit build/setup download for isolated evaluation; no disclosure upload.

Never imported by application code. Pin repository revision and hash downloaded
files in a manifest. No request-time dependency downloads.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

REPOSITORY = 'sentence-transformers/all-MiniLM-L6-v2'
REVISION = '10dbd2f06a8baf40ad285b037edda610c1b9a57c'
FILES = ('config.json', 'tokenizer.json', 'README.md', 'onnx/model.onnx')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in FILES:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}'
        with urllib.request.urlopen(url, timeout=60) as response, target.open('wb') as dest:
            while chunk := response.read(1024 * 1024):
                dest.write(chunk)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        print(name, target.stat().st_size, hashes[name], flush=True)
    manifest = dict(repository=REPOSITORY, revision=REVISION,
                    license='apache-2.0 (model card)', hashes=hashes,
                    role='isolated_unvalidated_evaluation_only')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
