"""Execute the frozen BSDS pilot with one isolated process per encoding.

Parallelism changes scheduling only. Seeds, inputs, budgets and evaluators are
the same as bsds_pilot.py. Runtime comparisons are expressly out of scope.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments import bsds_pilot as pilot


def method_run(method):
    import numpy as np
    manifest=json.loads((pilot.OUTPUT/'dataset.json').read_text())
    tasks=pilot.tasks_for(manifest['cases'])
    np.random.default_rng(20261019).shuffle(tasks)
    tasks=[t for t in tasks if pilot.CONFIGS[t[1]][0]==method]
    for number,(case,config,seed) in enumerate(tasks,1):
        path=pilot.OUTPUT/'runs'/f'{case}_{config}_{seed}'/'result.json'
        if not path.exists():pilot.worker(config,case,seed)
        result=json.loads(path.read_text())
        if result['protocol_sha256']!=pilot.digest(pilot.OUTPUT/'protocol.json'):
            raise ValueError('Protocol mismatch')
        print(f"{method} {number}/{len(tasks)} {case} {config} {seed} F1={result['metrics']['best_f1']:.4f}",flush=True)


def run():
    manifest=pilot.prepare()
    pilot.classical(manifest)
    pilot.write_json(pilot.OUTPUT/'execution_driver.json',{
        'driver':Path(__file__).name,'sha256':pilot.digest(__file__),
        'parallelism':'Three persistent isolated encoding processes, Aer max_parallel_threads=1 per detector',
        'scheduling':'Frozen task shuffle filtered within each method; completed smoke result reused with matching protocol',
        'timing_limit':'Concurrent host execution; no runtime or hardware speed ranking permitted'})
    children,logs=[],[]
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    try:
        for method in ('QPIE','FRQI','NEQR'):
            log=(pilot.OUTPUT/f'{method.lower()}_execution.log').open('w',encoding='utf-8')
            logs.append(log)
            children.append(subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'--method',method],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,**options))
        previous=-1
        while any(p.poll() is None for p in children):
            if any(p.poll() is not None and p.returncode!=0 for p in children):
                raise RuntimeError('Encoding worker failed; inspect *_execution.log')
            done=len(list((pilot.OUTPUT/'runs').glob('*/result.json')))
            if done!=previous:
                print(f'Completed{done}/240quantumruns',flush=True);previous=done
            time.sleep(5)
        if any(p.returncode!=0 for p in children):raise RuntimeError('Encoding worker failed')
        records=pilot.load_records(manifest)
        pilot.write_report(records,manifest)
        print('Fullmatrixcomplete; independentreplayandcurveverificationstarting',flush=True)
        pilot.verify(records,manifest)
        print('Completed and verified:'+str(pilot.OUTPUT/'report.md'),flush=True)
    finally:
        for p in children:
            if p.poll() is None:p.terminate()
        for p in children:p.wait()
        for log in logs:log.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method',choices=('QPIE','FRQI','NEQR'))
    args=parser.parse_args()
    if args.method:method_run(args.method)
    else:run()
