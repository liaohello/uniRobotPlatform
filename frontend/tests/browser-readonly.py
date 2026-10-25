"""Server-only read integration. Synthetic fault checks never alter native state."""
import argparse,asyncio,copy,hashlib,json,time,traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
from view_settle import camera_trace, settle_view
p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
report={'scope':'real read-only GET integration + explicitly synthetic fault fixtures; NOT M1 control acceptance','checks':[],'errors':[],'requests':[],'assets':[],'snapshot_timings':[]}
def check(name,condition):
 if not condition:raise AssertionError(name)
 report['checks'].append(name)
async def state(page):return await page.evaluate('window.__workbenchInspect()')
async def loaded(page):await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0',timeout=60000)
async def reload_source(page):
 before=(await state(page))['scene']['lifecycle']['created'] if await page.evaluate('typeof window.__workbenchInspect==="function"') else 0
 await page.get_by_role('button',name='重新加载来源',exact=True).click()
 await page.wait_for_function('(n)=>window.__workbenchInspect && window.__workbenchInspect().scene.lifecycle.created>n',arg=before)
 await loaded(page)
async def edit(page,value='12'):
 await page.locator('[data-object="link2"]').click();await page.get_by_role('button',name='Joint',exact=True).first.click()
 field=page.get_by_role('spinbutton',name='joint2 Target deg',exact=True);await field.fill(value);await field.press('Tab')
 await page.wait_for_function('window.__workbenchInspect().target?.mode==="joint"')
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
  context=await browser.new_context(viewport={'width':1600,'height':1000},device_scale_factor=1,timezone_id='America/Los_Angeles')
  page=await context.new_page();page.on('pageerror',lambda e:report['errors'].append(str(e)))
  context.on('request',lambda r:report['requests'].append({'method':r.method,'url':r.url}))
  try:
   # Actual gateway responses fetched through the same frontend origin. Never call native.
   wires={}
   for endpoint in ('scene','capabilities','snapshot'):
    started=time.perf_counter();r=await context.request.get(a.url+'/api/v1/mobilecar/'+endpoint)
    check('proxy '+endpoint+' HTTP 200',r.status==200);wires[endpoint]=await r.json()
    report.setdefault('initial_http',[]).append({'endpoint':endpoint,'elapsed_ms':round((time.perf_counter()-started)*1000,2)})
   for asset in wires['scene']['data']['mesh_assets']:
    r=await context.request.get(a.url+asset['uri']);body=await r.body();sha=hashlib.sha256(body).hexdigest()
    report['assets'].append({'id':asset['asset_id'],'status':r.status,'bytes':len(body),'sha256':sha,'matches':sha==asset['sha256'],'etag':r.headers.get('etag')})
   check('23 meshes traverse frontend proxy and match all SHA256 digests',len(report['assets'])==23 and all(x['matches'] and x['status']==200 for x in report['assets']))
   asset=wires['scene']['data']['mesh_assets'][0];wrong=asset['uri'].split('?')[0]+'?sha256='+'0'*64
   r=await context.request.get(a.url+wrong);bad=await r.json();check('proxy preserves asset digest query and backend 409',r.status==409 and bad['detail']['code']=='asset_revision_changed')
   await page.goto(a.url+'/?inspect=1',wait_until='domcontentloaded');await loaded(page)
   await page.wait_for_function('window.__workbenchInspect().monitor.snapshots>=3')
   first=await state(page);report['real_identity']=first['source'];report['real_resource']=first['live']['resource'];report['renderer']=first['scene']['renderer']
   check('real source is read-only and does not create platform Session',first['source']['kind']=='live' and not first['source']['is_platform_session'] and await page.get_by_role('button',name='Start',exact=True).is_disabled())
   check('real scene meshes are rendered without failures',first['scene']['failedAssets']==[])
   check('real snapshot excludes GT diagnostics',first['actual']['diagnostics']=={})
   check('user and named model angles retain joint4 zero difference',abs(first['actual']['arm']['user_joint_positions_rad'][3]-first['actual']['model_joint_positions_rad']['joint4'])>1.5)
   check('backend target is separate and has no command acknowledgement',first['live']['target']['command_id'] is None and first['live']['target']['tcp'] is None and first['target'] is None and await page.locator('[data-backend-target="joint2"]').count()==1)
   await edit(page);await page.get_by_role('button',name='车侧',exact=True).click();await page.wait_for_timeout(300)
   await page.get_by_role('button',name='保存',exact=True).click();before=await state(page);layout=await page.evaluate('localStorage.getItem("unirobot:m12a:layout:v2")')
   await page.wait_for_function('(n)=>window.__workbenchInspect().monitor.snapshots>=n',arg=before['monitor']['snapshots']+4)
   after=await state(page)
   check('real Actual tick/time keep updating',after['actual']['control_tick_id']!=before['actual']['control_tick_id'] and after['actual']['sim_time_s']>before['actual']['sim_time_s'])
   check('polling preserves one renderer, selection and camera',after['scene']['lifecycle']['created']==before['scene']['lifecycle']['created'] and after['scene']['camera']==before['scene']['camera'] and after['selected']==before['selected'])
   check('polling preserves local target and saved layout',after['target']==before['target'] and layout==await page.evaluate('localStorage.getItem("unirobot:m12a:layout:v2")'))
   await page.get_by_role('button',name='TCP',exact=True).click();x=await page.get_by_role('spinbutton',name='TCP X',exact=True).input_value();await page.get_by_role('spinbutton',name='TCP X',exact=True).fill(str(float(x)+.01));await page.get_by_role('spinbutton',name='TCP X',exact=True).press('Tab')
   check('live source supports explicit local TCP candidate only',(await state(page))['target']['mode']=='tcp' and await page.get_by_role('button',name='提交执行',exact=False).is_disabled())
   await page.get_by_label('轮询间隔',exact=True).select_option('2000');check('poll interval is configurable without replacing the renderer',(await state(page))['monitor']['intervalMs']==2000 and (await state(page))['scene']['lifecycle']['created']==before['scene']['lifecycle']['created']);await page.get_by_label('轮询间隔',exact=True).select_option('1000')
   await page.screenshot(path=str(a.output/'real-readonly.png'),full_page=True)
   real_final=await state(page);report['real_final']=real_final
   check('takeover, execution, recording remain disabled',await page.get_by_role('button',name='申请接管',exact=True).is_disabled() and await page.get_by_role('button',name='录制',exact=True).is_disabled())
   # Snapshot fixtures use wire data copies and explicitly synthetic identities/time.
   fixture={'offline':False,'runtime':0,'resource':0,'mismatch_init':False,'asset_bad':False,'asset_http_error':False,'delay':0,'seq':0,'inflight':0,'max_inflight':0,'starts':[],'ends':[],'entered':asyncio.Event()}
   def fixture_scene_id():return 'mobile_pick' if fixture['resource']==0 else 'fixture-scene-'+str(fixture['resource'])
   async def intercept(route):
    path=urlsplit(route.request.url).path
    if '/scene/assets/' in path:
     if fixture['asset_bad'] and path.endswith('/base_link'):
      await route.fulfill(status=200,body=b'fixture corrupted mesh bytes',content_type='model/stl');return
     if fixture['asset_http_error'] and path.endswith('/base_link'):
      await route.fulfill(status=502,json={'detail':{'code':'asset_integrity_failed','message':'synthetic upstream integrity error'}});return
     await route.continue_();return
    endpoint=path.rsplit('/',1)[-1]
    if endpoint in ('kinematics','execution-recipe'):
     await route.continue_();return
    d=copy.deepcopy(wires[endpoint]);new_runtime={'run_id':'fixture-run-'+str(fixture['runtime']),'backend_generation':1,'episode_id':'fixture-episode-'+str(fixture['runtime'])}
    d['runtime_identity']=copy.deepcopy(new_runtime)
    if endpoint in ('scene','capabilities'):
     d['resource_identity']['scene_id']=fixture_scene_id();d['data']['scene_id']=d['resource_identity']['scene_id']
    if endpoint=='snapshot':d['resource_identity']['scene_id']=fixture_scene_id()
    if endpoint=='scene':
     d['geometry_binding']['observed_runtime_identity']=copy.deepcopy(new_runtime)
     d['geometry_binding']['runtime_identity_matches']=False
     d['geometry_binding']['association']='content_reverified_after_runtime_identity_change'
     if fixture['resource']>0:d['geometry_binding']['content_identity_sha256']=('d' if fixture['resource']==1 else 'e')*64
     if fixture['mismatch_init']:
      d['resource_identity']['scene_id']='fixture-inconsistent-scene';d['data']['scene_id']='fixture-inconsistent-scene'
    if endpoint=='snapshot':
     fixture['seq']+=1;fixture['inflight']+=1;fixture['max_inflight']=max(fixture['max_inflight'],fixture['inflight']);fixture['starts'].append(time.monotonic());fixture['entered'].set()
     try:
      await asyncio.sleep(fixture['delay'])
      if fixture['offline']:
       await route.fulfill(status=503,json={'detail':{'code':'native_offline','message':'synthetic disconnected source'}});return
      d['data']['time']['sim_time_s']=100+fixture['seq'];d['data']['time']['control_tick_id']='fixture-tick-'+str(fixture['seq'])
      d['data']['actual']['arm']['user_joint_positions_rad'][0]=.001*fixture['seq'];d['data']['actual']['model_joint_positions_rad']['joint1']=.001*fixture['seq'];d['data']['actual']['arm']['model_joint_positions_rad'][0]=.001*fixture['seq']
      d['data']['actual']['diagnostics']={'mode':'GT_DEBUG','object_pose_world_sim':{'position_m':[99,99,99]}}
      await route.fulfill(status=200,json=d)
     finally:fixture['inflight']-=1;fixture['ends'].append(time.monotonic())
    else:await route.fulfill(status=200,json=d)
   await page.route('**/api/v1/mobilecar/**',intercept)
   await reload_source(page);await edit(page)
   synthetic=await state(page);fixture['delay']=1.5;fixture['starts'].clear();fixture['ends'].clear()
   await page.wait_for_function('(n)=>window.__workbenchInspect().monitor.snapshots>=n',arg=synthetic['monitor']['snapshots']+3,timeout=30000)
   current=await state(page)
   # The counter and the proxy log settle a few milliseconds apart; wait for the
   # measured condition instead of assuming the third completion already landed.
   for _ in range(40):
    if len(fixture['ends'])>=3:break
    await asyncio.sleep(.1)
   check('synthetic continuous Actual update preserves local target',current['actual']['model_joint_positions_rad']['joint1']!=synthetic['actual']['model_joint_positions_rad']['joint1'] and current['target']==synthetic['target'])
   check('slow snapshot requests never overlap',fixture['max_inflight']==1 and len(fixture['ends'])>=3 and all(s-e>.85 for s,e in zip(fixture['starts'][1:],fixture['ends'])))
   report['snapshot_timings']={'fixture':'1.5 s synthetic responses','starts':fixture['starts'][:],'ends':fixture['ends'][:],'max_inflight':fixture['max_inflight']}
   check('synthetic diagnostics are not merged into live Actual',current['actual']['diagnostics']=={})
   # Disconnect using HTTP fixture; keep the last good value clearly stale.
   fixture['delay']=0;fixture['offline']=True
   await page.wait_for_function('window.__workbenchInspect().monitor.state==="stale"')
   stale=await state(page);await page.screenshot(path=str(a.output/'fixture-disconnected.png'),full_page=True)
   check('disconnect marks retained Actual stale without sample fallback',stale['source']['kind']=='live' and stale['actual']['control_tick_id'].startswith('fixture-') and '陈旧' in await page.locator('.monitor-chip').inner_text())
   fixture['offline']=False;await page.wait_for_function('window.__workbenchInspect().monitor.state==="current"')
   check('read polling recovers explicitly on successful same-identity response',(await state(page))['source']['kind']=='live')
   # geometry-2: runtime-only changes keep content; resource changes replace it.
   for field in ('runtime','resource'):
    await edit(page)
    # Both samples come from the shared quiescence gate: a pending 120 ms auto-fit debounce or a
    # damped OrbitControls residual would otherwise be measured as an unsolicited camera change.
    before_identity=await settle_view(page)
    fixture[field]+=1
    await page.wait_for_function('(r)=>window.__workbenchInspect && window.__workbenchInspect().live.resource.scene_id===r.scene && window.__workbenchInspect().actual.run_id===r.run && window.__workbenchInspect().target===null',arg={'scene':fixture_scene_id(),'run':'fixture-run-'+str(fixture['runtime'])},timeout=15000)
    at_flip=await state(page)
    await loaded(page);after_identity=await settle_view(page)
    camera_trace(report,'identity transition keeps camera ('+field+')',before_identity,at_flip,after_identity)
    report.setdefault('identity_transitions',[]).append({'field':field,
     'before':{'instanceId':before_identity['scene']['instanceId'],'contentKey':before_identity['live']['contentKey'],'runtimeKey':before_identity['live']['runtimeKey'],'camera':before_identity['scene']['camera'],'cameraTarget':before_identity['scene']['cameraTarget'],'target':before_identity['target'] is not None},
     'after':{'instanceId':after_identity['scene']['instanceId'],'contentKey':after_identity['live']['contentKey'],'runtimeKey':after_identity['live']['runtimeKey'],'camera':after_identity['scene']['camera'],'cameraTarget':after_identity['scene']['cameraTarget'],'target':after_identity['target'] is not None,'sourceIdentity':after_identity['source']['identity']}})
    check(field+' identity change clears the old local Target',after_identity['target'] is None)
    if field=='runtime':
     check('runtime-only change keeps verified content, renderer, camera and layout',after_identity['scene']['instanceId']==before_identity['scene']['instanceId'] and after_identity['live']['contentKey']==before_identity['live']['contentKey'] and after_identity['scene']['camera']==before_identity['scene']['camera'] and after_identity['scene']['viewport']==before_identity['scene']['viewport'])
    else:
     check('content change replaces the scene instead of reusing old meshes',after_identity['scene']['instanceId']!=before_identity['scene']['instanceId'] or after_identity['live']['contentKey']!=before_identity['live']['contentKey'])
   # Explicit initialization mismatch is rejected rather than mixed across requests.
   fixture['mismatch_init']=True;await page.get_by_role('button',name='重新加载来源',exact=True).click();await page.get_by_role('heading',name='数据源不可用').wait_for()
   check('cross-request initialization mismatch displays no mixed renderer',await page.locator('canvas').count()==0)
   fixture['mismatch_init']=False;await reload_source(page)
   # A delayed old request is canceled when switching to frozen. Its result cannot overwrite it.
   fixture['delay']=1.8;fixture['entered'].clear();await asyncio.wait_for(fixture['entered'].wait(),8)
   await page.get_by_label('数据源',exact=True).select_option('frozen');await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().source.kind==="frozen"');await loaded(page);await asyncio.sleep(2)
   check('source switch cancels delayed live result and clears local Target',(await state(page))['source']['kind']=='frozen' and (await state(page))['target'] is None)
   fixture['delay']=0;fixture['asset_bad']=True
   await page.get_by_label('数据源',exact=True).select_option('platform');await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().source.kind==="live"');await loaded(page)
   bad_state=await state(page);check('wrong mesh bytes are rejected before STL parsing','base_link' in bad_state['scene']['failedAssets'] and 'asset_integrity_failed' in bad_state['assetError'])
   await page.screenshot(path=str(a.output/'fixture-asset-integrity.png'),full_page=True)
   fixture['asset_bad']=False;fixture['asset_http_error']=True;await reload_source(page)
   check('backend integrity error remains visible without frozen asset fallback','asset_integrity_failed' in (await state(page))['assetError'])
   fixture['asset_http_error']=False;await page.unroute('**/api/v1/mobilecar/**',intercept)
   await reload_source(page)
   await page.wait_for_function('window.__workbenchInspect().monitor.snapshots>=2');await page.screenshot(path=str(a.output/'final-real-readonly.png'),full_page=True)
   check('real source restores with one renderer after fault fixtures',(await state(page))['scene']['lifecycle']['active']==1 and (await state(page))['assetError']=='')
   allowed={'/api/v1/mobilecar/scene','/api/v1/mobilecar/capabilities','/api/v1/mobilecar/snapshot','/api/v1/mobilecar/kinematics','/api/v1/mobilecar/execution-recipe','/api/v1/mobilecar/preflight'}
   check('browser network contains only GET and allowlisted read endpoints',all(r['method']=='GET' and (not urlsplit(r['url']).path.startswith('/api/') or urlsplit(r['url']).path in allowed or urlsplit(r['url']).path.startswith('/api/v1/mobilecar/scene/assets/')) for r in report['requests']))
   check('no uncaught browser errors',not report['errors']);report['status']='passed'
  except Exception as exc:
   report.update(status='failed',exception=str(exc),traceback=traceback.format_exc());await page.screenshot(path=str(a.output/'failure.png'),full_page=True)
  finally:
   (a.output/'browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');await browser.close()
asyncio.run(main());print(json.dumps({'status':report['status'],'checks':len(report['checks']),'error':report.get('exception')}));raise SystemExit(report['status']!='passed')
