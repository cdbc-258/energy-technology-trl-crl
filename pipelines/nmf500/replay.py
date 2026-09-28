"""Portable 500-theme gate replay from original evidence plus taxonomy overlay.

python pipelines/nmf500/replay.py --output /tmp/trl-nmf500
No sibling repository, embedding model or original large corpus is needed.
"""
import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from trl_crl.pipeline import INPUT_NAMES,write_outputs


def replay(output):
    overlay=REPO/'tests/fixtures/nmf500/taxonomy_overlay'
    with TemporaryDirectory(prefix='trl-nmf500-') as tmp:
        for name in INPUT_NAMES:
            source=overlay/(name+'.json')
            if not source.exists():
                source=REPO/'data'/(name+'.json')
            (Path(tmp)/(name+'.json')).write_bytes(source.read_bytes())
        return write_outputs(Path(tmp),output)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(replay(args.output),ensure_ascii=False,indent=2))
