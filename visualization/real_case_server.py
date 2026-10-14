"""Local automatic detector and live results; image upload with automatic whole-image processing."""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
import shutil
import uuid
from urllib.parse import unquote
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from visualization.trace_store import write_json_atomic
from preprocessing.upload_image import preprocess_upload,MAX_BYTES

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'results/real_case/row0'


class DetectionJob:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.last_status = {'status':'idle'}
        self.output=OUTPUT
        self.context={'kind':'sombench','name':'SomBench metadata row 0','image_shape':[512,512],
                      'metrics_available':True,'preprocessing':None}

    def upload(self,body,name):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError('Please wait for the current detection run to finish')
            output=ROOT/'results/user_images'/uuid.uuid4().hex
            output.mkdir(parents=True)
            source=output/'source.bin'
            source.write_bytes(body)
            info=preprocess_upload(source,output)
            for asset in ('index.html','gate_trace_view.js','live_pipeline_view.js'):
                shutil.copyfile(OUTPUT/asset,output/asset)
            self.process=None
            self.output=output
            self.context={'kind':'upload','name':Path(name.replace('\\','/')).name[:200],
                'image_shape':info['image_shape'],'metrics_available':False,'preprocessing':info}
            write_json_atomic(output/'context.json',self.context)
            write_json_atomic(output/'progress.json',{'status':'preprocessed','circuits_executed':0,'measurement_shots':0,'elapsed_seconds':0})
            write_json_atomic(output/'gate_trace_latest.json',{'waiting':True})
            self.last_status={'status':'preprocessed'}
            return self.context

    def status(self):
        path = self.output/'progress.json'
        try:
            info = json.loads(path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError):
            info = dict(self.last_status)
        if self.process is not None:
            code = self.process.poll()
            if code is not None and code != 0:
                return {'status':'failed','exit_code':code,'log':'run.log'}
            if code is None and info.get('status') == 'complete':
                info['status'] = 'finishing'
        self.last_status = dict(info)
        return info

    def start(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return False
            self.output.mkdir(parents=True,exist_ok=True)
            write_json_atomic(self.output/'progress.json',{'status':'queued','circuits_executed':0,
                'measurement_shots':0,'elapsed_seconds':0})
            write_json_atomic(self.output/'gate_trace_latest.json',{'waiting':True})
            command=[sys.executable,str(ROOT/'experiments/real_case.py')]
            if self.context['kind']=='upload':
                command+=['--image',str(self.output/'preprocessed.png'),'--output',str(self.output)]
            with (self.output/'run.log').open('w',encoding='utf-8') as log:
                options = {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                self.process = subprocess.Popen(command,
                    cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,**options)
            return True


JOB = DetectionJob()


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        relative=Path(super().translate_path(path)).relative_to(OUTPUT)
        return str(JOB.output/relative)
    def reply(self,value,status=200):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)

    def do_GET(self):
        if self.path.split('?',1)[0] == '/api/status':
            self.reply(JOB.status())
        elif self.path.split('?',1)[0] == '/api/trace':
            try:
                packet = json.loads((JOB.output/'gate_trace_latest.json').read_text(encoding='utf-8'))
            except (OSError,json.JSONDecodeError):
                packet = {'waiting':True}
            self.reply(packet)
        elif self.path.split('?',1)[0]=='/api/context':
            self.reply(JOB.context)
        else:
            super().do_GET()

    def do_POST(self):
        host = self.headers.get('Host','')
        origin = self.headers.get('Origin','')
        allowed = {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        expected_type='application/octet-stream' if self.path=='/api/upload' else 'application/json'
        if host not in allowed or origin not in ('','http://'+host) or self.headers.get('Content-Type') != expected_type:
            self.reply({'error':'Local same-origin requests required'},403);return
        if self.path=='/api/upload':
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=MAX_BYTES:
                    self.reply({'error':'Upload an image smaller than 20 MB'},413);return
                context=JOB.upload(self.rfile.read(length),unquote(self.headers.get('X-File-Name','Uploaded image')))
                self.reply(context,201)
            except RuntimeError as error:
                self.reply({'error':str(error)},409)
            except (ValueError,OSError) as error:
                self.reply({'error':str(error)},400)
            return
        if self.path != '/api/run':
            self.reply({'error':'Unknown endpoint'},404);return
        length = int(self.headers.get('Content-Length','0'))
        if length > 1024:
            self.reply({'error':'Request too large'},413);return
        self.rfile.read(length)
        self.reply({'started':True},202) if JOB.start() else self.reply({'error':'Already running'},409)

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8766)
    args = parser.parse_args()
    handler = partial(Handler,directory=str(OUTPUT))
    server = ThreadingHTTPServer(('127.0.0.1',args.port),handler)
    print(f'Automatic quantum detector: http://127.0.0.1:{args.port}/',flush=True)
    server.serve_forever()
