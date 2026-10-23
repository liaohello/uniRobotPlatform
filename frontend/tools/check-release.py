"""Run only on the authorized server, inside an already hash-frozen frontend release."""
from pathlib import Path
import argparse,datetime,functools,hashlib,http.server,json,os,subprocess,sys,urllib.request
p=argparse.ArgumentParser();p.add_argument('release',type=Path);p.add_argument('--environment',type=Path,required=True);p.add_argument('--node-bin',type=Path,required=True);p.add_argument('--browser-python',type=Path,required=True);p.add_argument('--reports',type=Path,required=True);p.add_argument('--port',type=int,required=True);a=p.parse_args()
r=a.release.resolve();front=r/'frontend';a.reports.mkdir(parents=True,exist_ok=False)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((r/'source-manifest.json').read_text())
for f in manifest['files']:
 if digest(front/f['path'])!=f['sha256']:raise RuntimeError('Source digest mismatch: '+f['path'])
for name in ('package.json','package-lock.json'):
 if digest(front/name)!=digest(a.environment/name):raise RuntimeError('Environment lock differs: '+name)
os.symlink(a.environment/'node_modules',front/'node_modules',target_is_directory=True)
env=dict(os.environ,PATH=str(a.node_bin)+os.pathsep+os.environ['PATH'])
def run(name,cmd):
 with (a.reports/name).open('w') as out:
  subprocess.run(cmd,cwd=front,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
def native():
 with urllib.request.urlopen('http://127.0.0.1:8792/api/v1/health',timeout=10) as response:return json.load(response)
before=native()
run('build.log',['npm','run','build'])
run('unit.log',['npm','test','--','--maxWorkers=2','--reporter=default','--reporter=json','--outputFile='+str(a.reports/'unit.json')])
with (a.reports/'preview.log').open('w') as log:
 preview=subprocess.Popen([sys.executable,'-m','http.server',str(a.port),'--bind','127.0.0.1','--directory',str(front/'dist')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
server={'pid':preview.pid,'port':a.port,'release_id':manifest['release_id'],'directory':str(front/'dist'),'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(a.reports/'preview.json').write_text(json.dumps(server,indent=2)+'\n')
try:
 run('browser.log',[str(a.browser_python),str(front/'tests/browser-workbench.py'),'http://127.0.0.1:'+str(a.port),str(a.reports/'browser')])
finally:
 after=native();keys=('run_id','backend_generation','episode_id','recording_status')
 (a.reports/'native-read-only.json').write_text(json.dumps({'before':{k:before[k] for k in keys},'after':{k:after[k] for k in keys},'native_mutations_sent':False,'new_physics_process_started':False},indent=2)+'\n')
 environment={'node':subprocess.check_output(['node','--version'],env=env,text=True).strip(),'npm':subprocess.check_output(['npm','--version'],env=env,text=True).strip(),'browser_python':str(a.browser_python),'hostname':os.uname().nodename,'lock_sha256':digest(front/'package-lock.json')}
 (a.reports/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
print(json.dumps({'status':'passed','release':manifest['release_id'],'reports':str(a.reports),'preview':server}))
