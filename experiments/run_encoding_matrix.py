"""Execute the frozen benchmark using persistent, isolated encoding workers.

Tasks run serially in the same randomized order as benchmark_encodings.py;
only interpreter/import startup is amortized. Each method owns one subprocess.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments import benchmark_encodings as benchmark


def serve(method):
    for line in sys.stdin:
        task = json.loads(line)
        try:
            benchmark.worker(Path(task['output']), method, task['stem'], task['shots'], task['seed'])
            print(json.dumps({'ok': True}), flush=True)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            print(json.dumps({'ok': False}), flush=True)


def run(output):
    import numpy as np
    manifest = benchmark.prepare(output)
    records = []
    for case in manifest['cases']:
        records.extend(benchmark.classical(output, case))
    tasks = [(c['stem'], method, shots, seed) for c in manifest['cases']
             for method in benchmark.METHODS for shots in benchmark.BUDGETS for seed in benchmark.SEEDS]
    np.random.default_rng(20261019).shuffle(tasks)
    workers = {}
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    benchmark.write_json(output / 'execution_driver.json', {
        'driver': Path(__file__).name, 'sha256': benchmark.digest(__file__),
        'execution': 'One persistent isolated subprocess per encoding; serial tasks in frozen random order',
        'resume': 'Earlier completed runs retained with exact same protocol hash',
        'timing_limit': 'First use includes cold in-call library behavior; later calls warm. No hardware speedup claim.',
    })
    try:
        for number, (stem, method, shots, seed) in enumerate(tasks, 1):
            path = output / 'runs' / f'{stem}_{method}_s{shots}_seed{seed}' / 'result.json'
            if not path.exists():
                if method not in workers:
                    workers[method] = subprocess.Popen(
                        [sys.executable, '-u', str(Path(__file__).resolve()), '--serve', method],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=ROOT, **options)
                process = workers[method]
                process.stdin.write(json.dumps({'output': str(output), 'stem': stem, 'shots': shots, 'seed': seed}) + '\n')
                process.stdin.flush()
                reply = process.stdout.readline()
                if not reply or not json.loads(reply)['ok']:
                    raise RuntimeError('Encoding worker failed: ' + method)
            result = json.loads(path.read_text())
            if result['protocol_sha256'] != benchmark.digest(output / 'protocol.json'):
                raise ValueError('Stale result protocol')
            records.append(result['metrics'])
            print(f"{number}/144 {method} shots={shots} seed={seed} {stem}: "
                  f"AP={result['metrics']['pr_auc']:.4f} time={result['metrics']['elapsed_seconds']:.2f}s", flush=True)
        benchmark.verify(output, records, manifest)
        benchmark.report(output, records, manifest)
        print('Completed and verified: ' + str(output / 'report.md'), flush=True)
    finally:
        for process in workers.values():
            process.stdin.close()
        for process in workers.values():
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=benchmark.DEFAULT_OUTPUT)
    parser.add_argument('--serve', choices=benchmark.METHODS)
    args = parser.parse_args()
    if args.serve:
        serve(args.serve)
    else:
        run(args.output.resolve())


if __name__ == '__main__':
    main()
