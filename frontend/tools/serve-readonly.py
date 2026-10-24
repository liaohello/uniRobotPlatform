"""Frontend-owned static preview + allowlisted GET proxy. No native imports/control."""
import argparse,functools,http.server,json,re,time,urllib.request,urllib.error
from pathlib import Path

API=re.compile(r'^/api/v1/mobilecar/(scene|capabilities|snapshot|scene/assets/[A-Za-z0-9_.-]{1,128})$')
class Preview(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path=self.path.split('?',1)[0]
        if not path.startswith('/api/'):
            return super().do_GET()
        if not API.fullmatch(path):
            self.send_error(404,'Only mobileCar read endpoints are exposed');return
        started=time.monotonic()
        try:
            response=urllib.request.urlopen(self.server.upstream+self.path,timeout=15)
        except urllib.error.HTTPError as exc:
            response=exc
        except (OSError,TimeoutError) as exc:
            body=json.dumps({'detail':{'code':'gateway_unavailable','message':str(exc),'read_only':True,'session_ready':False}}).encode()
            self.reply(503,body,'application/json');self.record(503,started,len(body));return
        with response:
            body=response.read();status=response.code
            headers={key:response.headers[key] for key in ('ETag','X-Content-Type-Options') if key in response.headers}
            self.reply(status,body,response.headers.get('Content-Type','application/octet-stream'),headers)
        self.record(status,started,len(body))
    def reply(self,status,body,content_type,headers=None):
        self.send_response(status);self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        for key,value in (headers or {}).items():self.send_header(key,value)
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass  # browser source-switch cancellation
    def record(self,status,started,size):
        print(json.dumps({'method':'GET','path':self.path,'status':status,'elapsed_ms':round((time.monotonic()-started)*1000,2),'bytes':size}),flush=True)
    def do_HEAD(self):
        if self.path.startswith('/api/'):self.send_error(405,'GET only')
        else:super().do_HEAD()
    def readonly(self):self.send_error(405,'Read-only preview: GET only; no request forwarded')
    do_POST=do_PUT=do_PATCH=do_DELETE=do_OPTIONS=readonly

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--port',type=int,required=True)
    p.add_argument('--upstream',default='http://127.0.0.1:18941');a=p.parse_args()
    server=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),functools.partial(Preview,directory=str(a.directory.resolve())))
    server.upstream=a.upstream.rstrip('/');server.serve_forever()
