"""Server-only UI verification. Offline sample checks do NOT certify robot control or M1 integration."""
import argparse,json,time,hashlib,math,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];requests=[];report={'scope':'M1.2a frozen-sample frontend interaction; no physical control/session/recording acceptance','checks':checks,'errors':errors}
def check(name,condition):
 if not condition:raise AssertionError(name)
 checks.append(name)
def state(page):return page.evaluate('window.__workbenchInspect()')
def loaded(page):page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0',timeout=60000)
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1600,'height':1000},device_scale_factor=1,timezone_id='America/Los_Angeles')
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.on('request',lambda req:requests.append({'method':req.method,'url':req.url}))
 try:
  start=time.perf_counter();page.goto(a.url+'/?inspect=1&source=frozen',wait_until='networkidle');loaded(page)
  report['initial_load_s']=time.perf_counter()-start;initial=state(page);before=json.dumps(initial['actual'],sort_keys=True)
  check('23 real STL assets loaded without failure',initial['scene']['pendingLoads']==0 and initial['scene']['failedAssets']==[])
  check('offline source does not grant platform Session',initial['source']['kind']=='frozen' and not initial['source']['is_platform_session'])
  check('single active renderer after React lifecycle',initial['scene']['lifecycle']['active']==1)
  check('execution and recording controls stay disabled',page.get_by_role('button',name='Start',exact=True).is_disabled() and page.get_by_role('button',name='录制',exact=True).is_disabled())
  page.screenshot(path=str(a.output/'workbench-overview.png'),full_page=True)
  # Hierarchy -> viewport selection and Inspector.
  page.locator('[data-object="link2"]').click();check('tree and Inspector share stable link selection',state(page)['selected']=='link2' and page.locator('.inspector-object b').inner_text()=='link2')
  page.get_by_role('button',name='Joint',exact=True).first.click()
  joint1=page.get_by_role('spinbutton',name='joint2 Target deg',exact=True);joint1.fill('12');joint1.press('Tab');page.wait_for_function('window.__workbenchInspect().target?.mode==="joint"')
  target1=state(page)['target'];check('Joint edit shows local Ghost without changing Actual',state(page)['scene']['ghost'] and json.dumps(state(page)['actual'],sort_keys=True)==before)
  page.locator('[data-object="link1"]').click();j2=page.get_by_role('spinbutton',name='joint1 Target deg',exact=True);j2.fill('8');j2.press('Tab')
  check('editing another Joint preserves existing target',abs(state(page)['target']['jointModelRad']['joint2']-target1['jointModelRad']['joint2'])<1e-9)
  # Drag a visible Joint ring using its projected geometry and actual hit testing.
  s=state(page);ring_hit=None
  # Camera-dependent: pick the widest projected diameter so the drag is a real
  # arc from every view direction, then verify the pointer really hits that ring.
  for axis,points in s['scene']['rings'].items():
   pairs=[(math.hypot(points[i]['x']-points[(i+len(points)//2)%len(points)]['x'],points[i]['y']-points[(i+len(points)//2)%len(points)]['y']),i) for i in range(len(points))]
   span,index=max(pairs);point=points[index]
   page.mouse.move(point['x'],point['y']);page.wait_for_timeout(30)
   if state(page)['scene']['gizmoAxis']==axis:
    ring_hit=(axis,point,points[(index+len(points)//2)%len(points)]);break
  check('visible single-joint ring is pickable',ring_hit is not None)
  axis,first,last=ring_hit;q_before=state(page)['target']['jointModelRad'].copy();cam=state(page)['scene']['camera']
  page.mouse.move(first['x'],first['y']);page.mouse.down();page.mouse.move(last['x'],last['y'],steps=12);page.mouse.up();page.wait_for_timeout(100)
  q_after=state(page)['target']['jointModelRad'];check('Joint ring changes only the selected target',abs(q_after['joint1']-q_before['joint1'])>0.0001 and abs(q_after['joint2']-q_before['joint2'])<1e-9)
  check('Joint ring drag leaves Orbit camera unchanged',max(abs(v-state(page)['scene']['camera'][i]) for i,v in enumerate(cam))<1e-6)
  # Unit switch is display conversion, not another target command.
  revision=state(page)['target']['revision'];page.get_by_role('button',name='rad',exact=True).click();check('unit switch preserves target revision',state(page)['target']['revision']==revision)
  page.get_by_role('button',name='°',exact=True).click()
  # Text focus blocks viewport shortcuts and ESC.
  search=page.get_by_role('textbox',name='搜索对象');search.fill('f');search.press('Escape');check('text focus does not cancel target',state(page)['target'] is not None);search.fill('')
  page.get_by_role('button',name='取消目标',exact=False).click();check('cancel clears Ghost and Target only',state(page)['target'] is None and not state(page)['scene']['ghost'] and json.dumps(state(page)['actual'],sort_keys=True)==before)
  # TCP fields and renderer share the same Target in world_sim metres.
  page.get_by_role('button',name='TCP',exact=True).click();position=state(page)['actual']['tcp']['position_m'];x=page.get_by_role('spinbutton',name='TCP X',exact=True);x.fill(str(round(position[0]+0.015,5)));x.press('Tab');page.wait_for_function('window.__workbenchInspect().target?.mode==="tcp"')
  check('TCP numeric target uses explicit frame and preserves Actual',state(page)['target']['frame']=='world_sim' and json.dumps(state(page)['actual'],sort_keys=True)==before)
  page.screenshot(path=str(a.output/'workbench-tcp-target.png'),full_page=True)
  # Exercise the actual TransformControls handle via screen coordinates, not state injection.
  s=state(page);h=s['scene']['handles']['x'];initial_x=s['target']['tcpWorldM'][0];cam=s['scene']['camera']
  page.mouse.move(h['x'],h['y']);page.mouse.down();page.mouse.move(h['x']+32,h['y'],steps=12);page.mouse.up();page.wait_for_timeout(150)
  moved=state(page);report['tcp_pointer_drag']={'before_x':initial_x,'after_x':moved['target']['tcpWorldM'][0],'handle':h,'camera_before':cam,'camera_after':moved['scene']['camera']}
  check('TCP handle pointer drag updates target',abs(moved['target']['tcpWorldM'][0]-initial_x)>0.0001)
  check('TCP handle drag does not Orbit camera',max(abs(v-moved['scene']['camera'][i]) for i,v in enumerate(cam))<1e-6)
  # A blur event ends an active local drag; it does not cancel the stored target.
  h=state(page)['scene']['handles']['z'];page.mouse.move(h['x'],h['y']);page.mouse.down();page.mouse.move(h['x'],h['y']-8,steps=3)
  check('TCP drag enters active gesture',state(page)['scene']['dragging'])
  page.evaluate("window.dispatchEvent(new Event('blur'))")
  check('blur event clears active gesture and enables Orbit',not state(page)['scene']['dragging'] and state(page)['scene']['orbitEnabled'])
  page.mouse.up()
  # Resize + preserved target, then layout save/reset/restore exercises teardown/recreation.
  revision=state(page)['target']['revision'];instance=state(page)['scene']['instanceId'];page.get_by_role('button',name='保存',exact=True).click();page.set_viewport_size({'width':1280,'height':900});page.wait_for_timeout(250)
  check('resize keeps one usable renderer and target',state(page)['scene']['viewport']['width']>200 and state(page)['target']['revision']==revision)
  page.get_by_role('button',name='重置',exact=True).click();loaded(page)
  check('layout reset keeps the same renderer and target',state(page)['scene']['lifecycle']['active']==1 and state(page)['scene']['instanceId']==instance and state(page)['target']['revision']==revision)
  page.get_by_role('button',name='恢复',exact=True).click();loaded(page);check('layout restore retains target and source identity',state(page)['target']['revision']==revision and state(page)['actual']['run_id']==initial['actual']['run_id'])
  canvas=page.get_by_role('application',name='机器人三维视口');canvas.focus();canvas.press('Escape');check('viewport ESC cancels local target',state(page)['target'] is None and not state(page)['scene']['ghost'])
  # Real viewport mesh picking using projected source geometry.
  page.get_by_role('button',name='选择',exact=True).click();page.get_by_role('button',name='恢复全景',exact=True).click();page.wait_for_timeout(250);point=state(page)['scene']['linkPoints']['link4'];page.mouse.click(point['x'],point['y']);page.wait_for_timeout(100)
  check('mesh click updates shared selection',state(page)['selected'] is not None and page.locator('.inspector-object b').inner_text()==state(page)['selected'])
  # Orbit on genuinely empty viewport space; no selection motion command.
  rect=canvas.bounding_box();cam=state(page)['scene']['camera'];page.mouse.move(rect['x']+rect['width']-25,rect['y']+70);page.mouse.down();page.mouse.move(rect['x']+rect['width']-90,rect['y']+100,steps=10);page.mouse.up();page.wait_for_timeout(200)
  check('blank-space Orbit remains usable',state(page)['scene']['camera']!=cam)
  page.set_viewport_size({'width':1600,'height':1000});page.get_by_role('button',name='恢复全景',exact=True).click();page.wait_for_timeout(300)
  report['final_scene']=state(page)['scene'];page.screenshot(path=str(a.output/'workbench-final.png'),full_page=True)
  # No silent simulated fallback when a real source is unavailable.
  page.route('**/api/v1/mobilecar/**',lambda route:route.fulfill(status=503,json={'detail':{'code':'fixture_offline','message':'synthetic offline source'}}));page.get_by_label('数据源',exact=True).select_option('platform');page.get_by_role('heading',name='数据源不可用').wait_for();check('unavailable platform source clears old view without silent fallback',page.locator('canvas').count()==0 and 'fixture_offline' in page.get_by_role('alert').inner_text())
  page.get_by_role('button',name='使用冻结原生样本',exact=True).click();loaded(page);check('explicit source switch recreates a single renderer',state(page)['scene']['lifecycle']['active']==1 and state(page)['target'] is None)
  check('browser issued GET requests only',all(r['method']=='GET' for r in requests))
  check('browser made no native command/runtime calls',all('/api/v1/' not in r['url'] or r['url'].split('?')[0].endswith(('/mobilecar/scene','/mobilecar/capabilities','/mobilecar/snapshot')) for r in requests))
  check('no uncaught browser errors',not errors)
  report['status']='passed';report['request_count']=len(requests);report['actual_sha256']=hashlib.sha256(before.encode()).hexdigest()
 except Exception as exc:
  report['status']='failed';report['exception']=str(exc);report['traceback']=traceback.format_exc();page.screenshot(path=str(a.output/'failure.png'),full_page=True)
 finally:
  (a.output/'browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');browser.close()
print(json.dumps({'status':report['status'],'checks':len(checks),'error':report.get('exception')},ensure_ascii=False))
raise SystemExit(report['status']!='passed')
