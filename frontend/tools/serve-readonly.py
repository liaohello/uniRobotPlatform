"""Frontend-owned static preview + allowlisted same-origin API proxy.

GET is exposed for the existing read surface plus execution-recipe, kinematics,
config snapshots and Sessions. Platform Draft create/save/validate POST/PUT is
allowed. Session create/start, motion, RESET, recording and native command
endpoints stay unproxied. Method, path, status, error body and query string are
preserved; no request body is invented by the proxy.
"""
import argparse,functools,http.server,json,re,time,urllib.request,urllib.error
from pathlib import Path

ID=r'[A-Za-z0-9_.-]{1,128}'
ROUTES=[
 (re.compile(r'^/api/v1/mobilecar/(scene|capabilities|snapshot|kinematics|execution-recipe)$'),{'GET'}),
 (re.compile(r'^/api/v1/mobilecar/scene/assets/'+ID+r'$'),{'GET'}),
 (re.compile(r'^/api/v1/experiment-drafts$'),{'GET','POST'}),
 (re.compile(r'^/api/v1/experiment-drafts/'+ID+r'$'),{'GET','PUT'}),
 (re.compile(r'^/api/v1/experiment-drafts/'+ID+r'/validate$'),{'POST'}),
 (re.compile(r'^/api/v1/config-snapshots$'),{'GET'}),
 (re.compile(r'^/api/v1/config-snapshots/'+ID+r'$'),{'GET'}),
 (re.compile(r'^/api/v1/sessions$'),{'GET'}),
 (re.compile(r'^/api/v1/sessions/'+ID+r'$'),{'GET'}),
]
MAX_BODY=65536
class Preview(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith('/api/'):return super().do_GET()
        self.forward('GET')
    def do_POST(self):self.forward('POST')
    def do_PUT(self):self.forward('PUT')
    def do_PATCH(self):self.forward('PATCH')
    def do_DELETE(self):self.forward('DELETE')
    def do_OPTIONS(self):self.forward('OPTIONS')
    def forward(self,method):
        path=self.path.split('?',1)[0]
        if not path.startswith('/api/'):
            self.send_error(405,'Only API paths may use this method');return
        matches=[allowed for pattern,allowed in ROUTES if pattern.fullmatch(path)]
        if not matches:
            self.send_error(404,'Only allowlisted platform endpoints are exposed');return
        if method not in matches[0]:
            self.send_error(405,'Method not allowed for this platform endpoint');return
        length=int(self.headers.get('Content-Length') or 0)
        if length>MAX_BODY:
            self.reply(413,json.dumps({'detail':{'code':'request_too_large','message':f'Request body exceeds {MAX_BODY} bytes'}}).encode(),'application/json');return
        body=self.rfile.read(length) if length else None
        headers={}
        if body is not None:headers['Content-Type']=self.headers.get('Content-Type','application/json')
        started=time.monotonic()
        request=urllib.request.Request(self.server.upstream+self.path,data=body,headers=headers,method=method)
        try:
            response=urllib.request.urlopen(request,timeout=20)
        except urllib.error.HTTPError as exc:
            response=exc
        except (OSError,TimeoutError) as exc:
            payload=json.dumps({'detail':{'code':'gateway_unavailable','message':str(exc),'read_only':True,'session_ready':False}}).encode()
            self.reply(503,payload,'application/json');self.record(method,503,started,len(payload));return
        with response:
            data=response.read();status=response.code
            passthrough={key:response.headers[key] for key in ('ETag','X-Content-Type-Options','Location') if key in response.headers}
            self.reply(status,data,response.headers.get('Content-Type','application/octet-stream'),passthrough)
        self.record(method,status,started,len(data))
    def reply(self,status,body,content_type,headers=None):
        self.send_response(status);self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        for key,value in (headers or {}).items():self.send_header(key,value)
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass  # browser source-switch cancellation
    def record(self,method,status,started,size):
        print(json.dumps({'method':method,'path':self.path,'status':status,'elapsed_ms':round((time.monotonic()-started)*1000,2),'bytes':size}),flush=True)
    def do_HEAD(self):
        if self.path.startswith('/api/'):self.send_error(405,'GET only')
        else:super().do_HEAD()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--port',type=int,required=True)
    p.add_argument('--upstream',default='http://127.0.0.1:18941');a=p.parse_args()
    server=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),functools.partial(Preview,directory=str(a.directory.resolve())))
    server.upstream=a.upstream.rstrip('/');server.serve_forever()
