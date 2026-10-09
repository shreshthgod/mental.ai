"""Explicit build-time resource installation; never imported by request code."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
import nltk

RESOURCES = ('vader_lexicon','punkt','punkt_tab','averaged_perceptron_tagger',
             'averaged_perceptron_tagger_eng','wordnet')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='nltk_data')
    args=parser.parse_args()
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    # NLTK refuses download paths beneath world/group-writable ancestors,
    # including /tmp and some CI workspaces. Download in a private home staging
    # directory, then copy public resources into the build bundle.
    with tempfile.TemporaryDirectory(prefix='.mental-ai-nltk-build-',dir=Path.home()) as staging:
        for resource in RESOURCES:
            if not nltk.download(resource,download_dir=staging,quiet=True,raise_on_error=True):
                raise RuntimeError('Required build resource installation failed')
        shutil.copytree(staging,output,dirs_exist_ok=True)
    manifest={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(output.rglob('*')) if p.is_file() and p.name!='build-manifest.json'}
    (output/'build-manifest.json').write_text(json.dumps({'nltk_version':nltk.__version__,
        'resources':RESOURCES,'hashes':manifest},indent=2)+'\n')


if __name__=='__main__':
    main()
