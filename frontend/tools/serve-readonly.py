"""Frontend-owned static preview + allowlisted same-origin API proxy.

GET is exposed for the existing read surface plus preflight, execution-recipe,
kinematics, config snapshots, Sessions, the map catalog with fixed map versions and
map raster images, and route drafts with immutable route versions. Platform Draft
create/save/validate, Session prepare/start, route-draft create/save/publish and the
three Session lifecycle actions (recording begin, robot STOP, recording end) are the
only writes; each is an exact path, so no wildcard control path is reachable.
The history reader is exposed as eight exact GET paths only: the five of episode-read-1 (list, detail,
stream catalogue, per-stream records, episode assets), the frame-link-2 path
(/api/v1/episodes/{id}/frames) and the two history-pose paths (/api/v1/episodes/{id}/robot-state and
/api/v1/episodes/{id}/model/assets/{asset_id}). No wildcard episode route is added: each of these is
its own exact pattern, so no other sub-path of an episode becomes reachable through this gateway.
Native episode validate/assessment,
replay execution, motion/teleop, RESET, /runs/{id}/stop and native command endpoints stay
unproxied: they are refused by this gateway itself, never forwarded. There is no route
collection GET upstream, so
none is exposed here. Method, path, status,
error body and query string are preserved; no request body is invented.
"""
import argparse,functools,http.server,json,re,time,urllib.request,urllib.error
from pathlib import Path

ID=r'[A-Za-z0-9_.-]{1,128}'
# At most eight nested segments and no dot-segments: the reader enforces its own asset
# boundary, this gateway simply refuses to carry anything outside the declared shape.
ASSET=r'[A-Za-z0-9_-][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_-][A-Za-z0-9_.-]*){0,7}'
ROUTES=[
 (re.compile(r'^/api/v1/mobilecar/(scene|capabilities|snapshot|kinematics|execution-recipe|preflight)$'),{'GET'}),
 (re.compile(r'^/api/v1/mobilecar/scene/assets/'+ID+r'$'),{'GET'}),
 (re.compile(r'^/api/v1/experiment-drafts$'),{'GET','POST'}),
 (re.compile(r'^/api/v1/experiment-drafts/'+ID+r'$'),{'GET','PUT'}),
 (re.compile(r'^/api/v1/experiment-drafts/'+ID+r'/validate$'),{'POST'}),
 (re.compile(r'^/api/v1/config-snapshots$'),{'GET'}),
 (re.compile(r'^/api/v1/config-snapshots/'+ID+r'$'),{'GET'}),
 (re.compile(r'^/api/v1/sessions$'),{'GET','POST'}),
 (re.compile(r'^/api/v1/sessions/'+ID+r'$'),{'GET'}),
 (re.compile(r'^/api/v1/maps$'),{'GET'}),
 (re.compile(r'^/api/v1/maps/'+ID+r'/versions/'+ID+r'$'),{'GET'}),
 (re.compile(r'^/api/v1/maps/'+ID+r'/versions/'+ID+r'/image$'),{'GET'}),
 (re.compile(r'^/api/v1/route-drafts$'),{'POST'}),
 (re.compile(r'^/api/v1/route-drafts/'+ID+r'$'),{'GET','PUT'}),
 (re.compile(r'^/api/v1/route-drafts/'+ID+r'/publish$'),{'POST'}),
 (re.compile(r'^/api/v1/sessions/'+ID+r'/start$'),{'POST'}),
 (re.compile(r'^/api/v1/sessions/'+ID+r'/recording/begin$'),{'POST'}),
 (re.compile(r'^/api/v1/sessions/'+ID+r'/stop$'),{'POST'}),
 (re.compile(r'^/api/v1/sessions/'+ID+r'/recording/end$'),{'POST'}),
 (re.compile(r'^/api/v1/routes/'+ID+r'/versions$'),{'GET'}),
 (re.compile(r'^/api/v1/routes/'+ID+r'/versions/'+ID+r'$'),{'GET'}),
 (re.compile(r'^/api/v1/episodes$'),{'GET'}),
 (re.compile(r'^/api/v1/episodes/'+ID+r'$'),{'GET'}),
 (re.compile(r'^/api/v1/episodes/'+ID+r'/streams$'),{'GET'}),
 (re.compile(r'^/api/v1/episodes/'+ID+r'/streams/'+ID+r'/records$'),{'GET'}),
 (re.compile(r'^/api/v1/episodes/'+ID+r'/assets/'+ASSET+r'$'),{'GET'}),
 # frame-link-2 adds exactly this one GET. It is deliberately not a wildcard under /episodes/{id}/:
 # any other episode sub-path still falls through to the local refusal below.
 (re.compile(r'^/api/v1/episodes/'+ID+r'/frames$'),{'GET'}),
 # history-pose-1 adds exactly these two GETs, one for the selected frame's state and mapping and one
 # for the frozen bundle's mesh bytes. Neither widens the episode namespace: the model asset id stays
 # a single flat token, so no other sub-path under /episodes/{id}/ becomes reachable.
 (re.compile(r'^/api/v1/episodes/'+ID+r'/robot-state$'),{'GET'}),
 (re.compile(r'^/api/v1/episodes/'+ID+r'/model/assets/'+ID+r'$'),{'GET'}),
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
            passthrough={key:response.headers[key] for key in ('ETag','X-Content-Type-Options','Location','X-Episode-Asset-Sha256','X-Episode-Run-Id') if key in response.headers}
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
