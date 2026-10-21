"""Three isolated simulator processes for the frozen offset follow-up.

Changes execution scheduling only; the serial driver remains reproducible.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments import bsds_offset20 as pilot


def worker(row):
    folder=ROOT/row['path']
    path=folder/'result.json'
    if not path.exists():
        result=subprocess.run([sys.executable,str(ROOT/'experiments/bsds_offset20.py'),
                               '--worker',row['case'],str(row['seed'])],cwd=ROOT,capture_output=True,text=True)
        (pilot.OUT/(folder.name+'.log')).write_text(result.stdout+result.stderr,encoding='utf8')
        if result.returncode:raise RuntimeError(result.stderr)
    record=pilot.read(path)
    assert record['protocol_sha256']==pilot.sha(pilot.OUT/'protocol.json')
    return row


if __name__=='__main__':
    protocol=pilot.prepare()
    execution={'driver':Path(__file__).name,'sha256':pilot.sha(__file__),'processes':3,
               'scope':'Execution scheduling only; ideal simulator concurrency precludes runtime comparison'}
    path=pilot.OUT/'execution_driver.json'
    if path.exists():assert pilot.read(path)==execution
    else:pilot.write(path,execution)
    todo=[r for r in pilot.ledger(protocol) if r['path'].startswith(str(pilot.OUT.relative_to(ROOT)))]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(worker,row) for row in todo]
        for number,future in enumerate(as_completed(futures),1):
            future.result();print(f'Completed {number}/45 new offset runs',flush=True)
    pilot.verify(protocol);pilot.report(protocol)
    print('Completed and verified: '+str(pilot.OUT/'report.md'),flush=True)
