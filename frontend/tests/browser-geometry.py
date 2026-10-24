"""Server-only LanderPi assembly evidence and unchanged TCP interaction checks."""
import argparse,asyncio,json,math,traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('output',type=Path);p.add_argument('release');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
report={'release_id':a.release,'scope':'compiled visual mesh assembly, actual TCP and local-only target interaction','checks':[],'requests':[],'errors':[],'views':{}}
def check(name,value):
 if not value:raise AssertionError(name)
 report['checks'].append(name)
async def state(page):return await page.evaluate('window.__workbenchInspect()')
def center(g):return [(lo+hi)/2 for lo,hi in zip(g['worldSimBounds']['min'],g['worldSimBounds']['max'])]
def span(g):return [hi-lo for lo,hi in zip(g['worldSimBounds']['min'],g['worldSimBounds']['max'])]
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1920,'height':1200},device_scale_factor=1)
  page.on('request',lambda r:report['requests'].append({'method':r.method,'url':r.url}));page.on('pageerror',lambda e:report['errors'].append(str(e)))
  try:
   response=await page.request.get(a.url+'/api/v1/mobilecar/scene');wire=await response.json();report['geometry_provenance']=wire.get('geometry_provenance')
   check('scene explicitly declares verified compiled geometry',response.status==200 and wire['schema_version']=='unirobot-mobilecar-geometry-1' and all(x['coordinate_space']=='mujoco_compiled_mesh' and x['mesh_preprocessing_applied'] and x['units']=='m' for x in wire['data']['mesh_assets']))
   await page.goto(a.url+'/?inspect=1',wait_until='domcontentloaded')
   await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().monitor.snapshots>=2',timeout=60000);await page.wait_for_timeout(400)
   check('preview title identifies this exact release',await page.locator('.build-label').get_attribute('title')==a.release)
   # Use existing visibility controls: no target, no Ghost, no world object occlusion.
   await page.get_by_role('button',name='图层选项',exact=True).click();await page.get_by_label('显示 Ghost 候选',exact=True).uncheck();await page.get_by_label('显示场景对象',exact=True).uncheck();await page.get_by_role('button',name='图层选项',exact=True).click()
   initial=await state(page);check('assembly inspection has Ghost off and no local Target',not initial['scene']['ghost'] and initial['target'] is None)
   geoms=initial['scene']['geoms'];report['actual_geometry']=geoms
   visible_expected={l['name']+'/'+g['name'] for l in wire['data']['links'] for g in l['geoms'] if g['rgba'][3]>0}
   check('all authored visible robot geometry is retained',set(geoms)==visible_expected and all(g['visible'] and g['vertices']>0 for g in geoms.values()))
   hidden_expected={l['name']+'/'+g['name'] for l in wire['data']['links'] for g in l['geoms'] if g['rgba'][3]==0}
   check('invisible chassis and contact geometry is not built',not hidden_expected.intersection(geoms) and 'base_link/chassis_collision' in hidden_expected)
   wheels={name:next(g for g in geoms.values() if g['asset']==asset) for name,asset in [('fl','wheel_left_front_link'),('rl','wheel_left_back_link'),('fr','wheel_right_front_link'),('rr','wheel_right_back_link')]}
   wc={k:center(g) for k,g in wheels.items()};ws={k:span(g) for k,g in wheels.items()};report['wheel_centers_world_sim_m']=wc;report['wheel_aabb_spans_m']=ws
   check('four wheel meshes lie at separate front/rear and left/right positions',wc['fl'][0]>wc['rl'][0] and wc['fr'][0]>wc['rr'][0] and wc['fl'][1]>wc['fr'][1] and wc['rl'][1]>wc['rr'][1])
   check('wheel thickness follows lateral axle and radial extent remains upright',all(v[1]<.65*min(v[0],v[2]) for v in ws.values()))
   check('four wheels share the same support height',max(g['worldSimBounds']['min'][2] for g in wheels.values())-min(g['worldSimBounds']['min'][2] for g in wheels.values())<.01)
   plate=next(g for g in geoms.values() if g['asset']=='base_link');plate_span=span(plate);report['base_visual_aabb_span_m']=plate_span
   check('visible chassis plate is horizontal',plate_span[2]<.6*min(plate_span[0],plate_span[1]))
   shells=[g for g in geoms.values() if g['asset'] in ('back_shell_black_link','back_shell_middle_link')]
   arm=next(g for g in geoms.values() if g['asset']=='link1');jaws=[g for g in geoms.values() if g['asset'] in ('left_jaw_link','right_jaw_link')]
   check('shells, arm base and two jaws remain assembled and visible',len(shells)==2 and len(jaws)==2 and center(arm)[2]>min(center(g)[2] for g in shells))
   check('rendered joint-chain TCP matches the true Actual marker',initial['scene']['tcp']['errorM'] is not None and initial['scene']['tcp']['errorM']<1e-5)
   check('both jaw meshes stay near the real TCP',all(math.dist(center(g),initial['actual']['tcp']['position_m'])<.08 for g in jaws))
   # Same zoom/target for front and side; oblique uses the existing fit camera.
   for name in ('front','side','oblique'):
    if name=='oblique':await page.get_by_role('button',name='恢复全景',exact=True).click()
    else:await page.get_by_role('button',name={'front':'车头','side':'车侧'}[name],exact=True).click()
    await page.wait_for_timeout(350);s=await state(page)
    check(name+' view has Ghost off and no asset errors',not s['scene']['ghost'] and not s['scene']['failedAssets'])
    report['views'][name]={'camera':s['scene']['camera'],'camera_target':s['scene']['cameraTarget'],'source':s['source'],'tick':s['actual']['control_tick_id'],'ghost':s['scene']['ghost'],'world_objects':False}
    await page.screenshot(path=str(a.output/(name+'.png')),full_page=True);await page.locator('.viewport-panel').screenshot(path=str(a.output/(name+'-viewport.png')))
   # No change to the established Joint4 mapping or local target behavior.
   await page.locator('[data-object="link4"]').click();await page.get_by_role('button',name='Joint',exact=True).first.click()
   field=page.get_by_role('spinbutton',name='joint4 Target deg',exact=True);await field.fill('1');await field.press('Tab');await page.wait_for_function('window.__workbenchInspect().target!==null');await field.fill('0');await field.press('Tab');await page.wait_for_function('Math.abs(window.__workbenchInspect().target.jointModelRad.joint4+Math.PI/2)<1e-8');s=await state(page)
   check('Joint4 user zero still maps to model minus pi/2',abs(s['target']['jointModelRad']['joint4']+math.pi/2)<1e-8)
   await page.get_by_role('button',name='图层选项',exact=True).click();await page.get_by_label('显示 Ghost 候选',exact=True).check();await page.get_by_role('button',name='图层选项',exact=True).click()
   await page.get_by_role('button',name='TCP',exact=True).click();s=await state(page);x=page.get_by_role('spinbutton',name='TCP X',exact=True);await x.fill(str(s['target']['tcpWorldM'][0]+.01));await x.press('Tab');s=await state(page)
   check('numeric TCP edit keeps a local preview and separate Actual',s['target']['mode']=='tcp' and s['source']['kind']=='live' and s['actual']['diagnostics']=={})
   before=s;h=s['scene']['handles']['x'];await page.mouse.move(h['x'],h['y']);await page.mouse.down();await page.mouse.move(h['x']+30,h['y'],steps=12);drag=await state(page)
   check('TCP pointer handle retains its existing dragging behavior',drag['scene']['dragging'] and drag['target']['tcpWorldM']!=before['target']['tcpWorldM'])
   await page.wait_for_function('(n)=>window.__workbenchInspect().monitor.snapshots>=n',arg=drag['monitor']['snapshots']+2);during=await state(page)
   check('Actual refresh preserves ongoing TCP drag, target and camera',during['scene']['dragging'] and during['target']==drag['target'] and during['scene']['camera']==before['scene']['camera'] and during['actual']['control_tick_id']!=drag['actual']['control_tick_id'])
   await page.mouse.up();await page.screenshot(path=str(a.output/'tcp-local-preview.png'),full_page=True)
   await page.get_by_role('button',name='取消目标',exact=False).click();s=await state(page)
   check('cancel only clears local Target and Ghost',s['target'] is None and not s['scene']['ghost'] and s['source']['identity']==initial['source']['identity'])
   check('Actual TCP and model chain remain aligned after all interactions',s['scene']['tcp']['errorM']<1e-5)
   allowed={'/api/v1/mobilecar/scene','/api/v1/mobilecar/capabilities','/api/v1/mobilecar/snapshot'}
   check('all browser requests are GET and no robot mutation endpoint is used',all(r['method']=='GET' and (not urlsplit(r['url']).path.startswith('/api/') or urlsplit(r['url']).path in allowed or urlsplit(r['url']).path.startswith('/api/v1/mobilecar/scene/assets/')) for r in report['requests']))
   check('no uncaught browser errors',not report['errors']);report['status']='passed';report['final_tcp']=s['scene']['tcp'];report['renderer']=s['scene']['renderer']
  except Exception as exc:
   report.update(status='failed',exception=str(exc),traceback=traceback.format_exc());await page.screenshot(path=str(a.output/'failure.png'),full_page=True)
  finally:
   (a.output/'geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');await browser.close()
asyncio.run(main());print(json.dumps({'status':report['status'],'checks':len(report['checks']),'exception':report.get('exception')}));raise SystemExit(report['status']!='passed')
