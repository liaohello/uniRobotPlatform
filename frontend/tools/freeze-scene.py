"""Server-only, read-only capture of the existing native viewer data. Never sends commands."""
from pathlib import Path
import argparse,datetime,hashlib,json,urllib.request
p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--origin',default='http://127.0.0.1:8792');a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
def get(route):
 with urllib.request.urlopen(a.origin+route,timeout=20) as r:return r.read()
def read(name):return json.loads(get('/api/v1/'+name))
def save(name,obj):
 (a.output/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
before=read('health');scene=read('scene');caps=read('capabilities');snap=read('snapshot');after=read('health')
for k in ('run_id','backend_generation','episode_id'):
 if not (before[k]==after[k]==snap[k]):raise RuntimeError('Native identity changed during read-only capture: '+k)
assets=[];(a.output/'meshes').mkdir()
for asset in scene['mesh_assets']:
 data=get(asset['uri']);sha=hashlib.sha256(data).hexdigest()
 if sha!=asset['sha256']:raise RuntimeError('Asset digest mismatch: '+asset['asset_id'])
 name=asset['asset_id']+'.stl';(a.output/'meshes'/name).write_bytes(data)
 assets.append({'asset_id':asset['asset_id'],'sha256':sha,'size_bytes':len(data),'source_uri':asset['uri']})
 asset['uri']='./sample/meshes/'+name
save('scene.json',scene);save('snapshot.json',snap);save('capabilities.json',caps)
save('provenance.json',{'kind':'frozen-native-sample','captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'identity':{k:snap[k] for k in ('run_id','backend_generation','episode_id')},'interface_profile':before['interface_profile'],'model_id':scene['model_id'],'model_sha256':scene['model_sha256'],'scene_id':scene['scene_id'],'capture_method':'GET health/scene/capabilities/snapshot and mesh assets from existing native process; no POST, RESET, stepping or new physics process','is_live':False,'is_platform_session':False,'is_episode_replay':False,'assets':assets})
print(json.dumps({'output':str(a.output),'links':len(scene['links']),'world_links':len(scene['world_links']),'assets':len(assets),'asset_bytes':sum(i['size_bytes'] for i in assets),'snapshot_keys':list(snap),'capability_keys':list(caps)}))
