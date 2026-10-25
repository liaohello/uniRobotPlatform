"""Run only on the authorized server, inside an already hash-frozen frontend release."""
from pathlib import Path
import argparse,datetime,functools,hashlib,http.server,json,os,socket,subprocess,sys,urllib.request
p=argparse.ArgumentParser();p.add_argument('release',type=Path);p.add_argument('--environment',type=Path,required=True);p.add_argument('--node-bin',type=Path,required=True);p.add_argument('--browser-python',type=Path,required=True);p.add_argument('--reports',type=Path,required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--read-only',action='store_true');p.add_argument('--upstream',default='http://127.0.0.1:18941');p.add_argument('--geometry',action='store_true');p.add_argument('--usability',action='store_true');p.add_argument('--config',action='store_true');p.add_argument('--session',action='store_true');p.add_argument('--map',action='store_true');p.add_argument('--lifecycle',action='store_true');p.add_argument('--lifecycle-live',action='store_true');p.add_argument('--map-mode',default='live',choices=('live','offline'));p.add_argument('--history',action='store_true');p.add_argument('--history-mode',default='real',choices=('real','synthetic'));p.add_argument('--skip-readonly',action='store_true');a=p.parse_args()
r=a.release.resolve();front=r/'frontend';a.reports.mkdir(parents=True,exist_ok=False)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((r/'source-manifest.json').read_text())
for f in manifest['files']:
 if digest(front/f['path'])!=f['sha256']:raise RuntimeError('Source digest mismatch: '+f['path'])
for name in ('package.json','package-lock.json'):
 if digest(front/name)!=digest(a.environment/name):raise RuntimeError('Environment lock differs: '+name)
link=front/'node_modules'
if link.is_symlink() or link.exists():link.unlink()
os.symlink(a.environment/'node_modules',link,target_is_directory=True)
env=dict(os.environ,PATH=str(a.node_bin)+os.pathsep+os.environ['PATH'],VITE_WORKBENCH_RELEASE=manifest['release_id'])
def run(name,cmd):
 with (a.reports/name).open('w') as out:
  subprocess.run(cmd,cwd=front,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
def native():
 with urllib.request.urlopen('http://127.0.0.1:8792/api/v1/health',timeout=10) as response:return json.load(response)
port_probe=socket.socket();port_probe.bind(('127.0.0.1',a.port));port_probe.close()
before=native()
process_before=subprocess.check_output(['ss','-ltnp'],text=True)
(a.reports/'listeners-before.txt').write_text(process_before)

run('build.log',['npm','run','build'])
run('unit.log',['npm','test','--','--maxWorkers=2','--reporter=default','--reporter=json','--outputFile='+str(a.reports/'unit.json')])
with (a.reports/'preview.log').open('w') as log:
 preview_command=([sys.executable,str(front/'tools/serve-readonly.py'),'--port',str(a.port),'--directory',str(front/'dist'),'--upstream',a.upstream] if a.read_only else [sys.executable,'-m','http.server',str(a.port),'--bind','127.0.0.1','--directory',str(front/'dist')])
 preview=subprocess.Popen(preview_command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
server={'pid':preview.pid,'port':a.port,'upstream':a.upstream,'release_id':manifest['release_id'],'directory':str(front/'dist'),'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(a.reports/'preview.json').write_text(json.dumps(server,indent=2)+'\n')
try:
 if not a.skip_readonly: run('browser.log',[str(a.browser_python),str(front/('tests/browser-readonly.py' if a.read_only else 'tests/browser-workbench.py')),'http://127.0.0.1:'+str(a.port),str(a.reports/'browser')])
 if a.read_only and not a.skip_readonly:run('frozen-browser.log',[str(a.browser_python),str(front/'tests/browser-workbench.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'frozen-browser')])
 if a.geometry:run('geometry-browser.log',[str(a.browser_python),str(front/'tests/browser-geometry.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'geometry'),manifest['release_id']])
 if a.usability:run('usability-browser.log',[str(a.browser_python),str(front/'tests/browser-usability.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'usability'),'--release',manifest['release_id']])
 if a.config:run('config-browser.log',[str(a.browser_python),str(front/'tests/browser-config.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'config')])
 if a.map:run('map-browser.log',[str(a.browser_python),str(front/'tests/browser-map.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'map'),'--mode',a.map_mode])
 if a.lifecycle:run('lifecycle-browser.log',[str(a.browser_python),str(front/'tests/browser-lifecycle.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'lifecycle'),'--mode','synthetic'])
 if a.lifecycle_live:run('lifecycle-live-browser.log',[str(a.browser_python),str(front/'tests/browser-lifecycle.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'lifecycle-live'),'--mode','live'])
 if a.session:run('session-browser.log',[str(a.browser_python),str(front/'tests/browser-session.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'session')])
 if a.history:run('history-browser.log',[str(a.browser_python),str(front/'tests/browser-history.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'history'),'--mode',a.history_mode])
finally:
 after=native();(a.reports/'listeners-after.txt').write_text(subprocess.check_output(['ss','-ltnp'],text=True));keys=('run_id','backend_generation','episode_id','recording_status')
 (a.reports/'native-read-only.json').write_text(json.dumps({'before':{k:before[k] for k in keys},'after':{k:after[k] for k in keys},'native_mutations_sent':False,'new_physics_process_started':False},indent=2)+'\n')
 environment={'node':subprocess.check_output(['node','--version'],env=env,text=True).strip(),'npm':subprocess.check_output(['npm','--version'],env=env,text=True).strip(),'browser_python':str(a.browser_python),'hostname':os.uname().nodename,'lock_sha256':digest(front/'package-lock.json')}
 (a.reports/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
print(json.dumps({'status':'passed','release':manifest['release_id'],'reports':str(a.reports),'preview':server}))
