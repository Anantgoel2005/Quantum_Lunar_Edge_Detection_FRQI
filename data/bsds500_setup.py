"""Fetch pinned file inventory only; selected validation assets load in the pilot."""
import json
from pathlib import Path
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments.bsds_pilot import REVISION,CACHE
from experiments.benchmark_encodings import write_json


def main():
    path=CACHE/'tree.json'
    if path.exists():
        inventory=json.loads(path.read_text())
    else:
        request=urllib.request.Request(
            f'https://api.github.com/repos/BIDS/BSDS500/git/trees/{REVISION}?recursive=1',
            headers={'User-Agent':'Quantum-edge-development-pilot'})
        with urllib.request.urlopen(request,timeout=45) as response:
            inventory=json.load(response)
    if inventory.get('sha')!=REVISION or inventory.get('truncated'):
        raise ValueError('Unexpected or truncated pinned repository inventory')
    write_json(path,inventory)
    print(f'Pinned BSDS500 inventory ready: {REVISION}. No image or annotation contents fetched.')


if __name__=='__main__':main()
