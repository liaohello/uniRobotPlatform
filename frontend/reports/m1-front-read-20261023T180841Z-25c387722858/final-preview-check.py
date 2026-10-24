"""Supplemental server-only check against an unchanged, hash-frozen production build."""
import argparse,asyncio,hashlib,json,traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('report',type=Path);a=p.parse_args()
result={'checks':[],'requests':[],'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
def check(name,value):
 if not value:raise AssertionError(name)
 result['checks'].append(name)
async def s(page):return await page.evaluate('window.__workbenchInspect()')
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1600,'height':1000},device_scale_factor=1)
  page.on('request',lambda r:result['requests'].append({'method':r.method,'url':r.url}))
  try:
   await page.goto(a.url+'/?inspect=1',wait_until='domcontentloaded')
   await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().monitor.snapshots>=2')
   await page.wait_for_timeout(1000);initial=await s(page)
   canvas=page.get_by_role('application',name='机器人三维视口');rect=await canvas.bounding_box()
   check('settled initial fit contains all robot link centers',all(rect['x']<=pt['x']<=rect['x']+rect['width'] and rect['y']<=pt['y']<=rect['y']+rect['height'] for pt in initial['scene']['linkPoints'].values()))
   await page.get_by_role('button',name='TCP',exact=True).click()
   p0=initial['actual']['tcp']['position_m'];field=page.get_by_role('spinbutton',name='TCP X',exact=True);await field.fill(str(p0[0]+.01));await field.press('Tab')
   await page.wait_for_function('window.__workbenchInspect().target?.mode==="tcp"');before=await s(page);h=before['scene']['handles']['x']
   await page.mouse.move(h['x'],h['y']);await page.mouse.down();await page.mouse.move(h['x']+24,h['y'],steps=12)
   dragging=await s(page);check('TCP pointer drag starts on real-source local target',dragging['scene']['dragging'])
   await page.wait_for_function('(n)=>window.__workbenchInspect().monitor.snapshots>=n',arg=dragging['monitor']['snapshots']+2,timeout=10000)
   during=await s(page)
   check('Actual polling keeps active drag and camera stable',during['scene']['dragging'] and during['scene']['camera']==before['scene']['camera'] and during['actual']['control_tick_id']!=dragging['actual']['control_tick_id'])
   await page.mouse.up();after=await s(page)
   check('dragged local target survives two Actual snapshots',after['target']['revision']>=dragging['target']['revision'] and after['target']['tcpWorldM']==dragging['target']['tcpWorldM'] and after['target']['tcpWorldM']!=before['target']['tcpWorldM'])
   result['drag']={'before':before['target'],'after':after['target'],'snapshot_count_before':dragging['monitor']['snapshots'],'snapshot_count_after':during['monitor']['snapshots'],'camera_before':before['scene']['camera'],'camera_after':during['scene']['camera']}
   await page.get_by_role('button',name='取消目标',exact=False).click();await page.get_by_role('button',name='恢复全景',exact=True).click();await page.wait_for_timeout(500)
   check('cancel leaves real Actual and no local Ghost',(await s(page))['target'] is None and not (await s(page))['scene']['ghost'])
   await page.screenshot(path=str(a.report/'browser/settled-real-readonly.png'),full_page=True)
   check('supplemental browser requests remain GET-only',all(r['method']=='GET' and ('/api/' not in r['url'] or '/api/v1/mobilecar/' in r['url']) for r in result['requests']))
   result['status']='passed';result['final_source']=(await s(page))['source'];result['final_scene']=(await s(page))['scene']
  except Exception as e:
   result.update(status='failed',exception=str(e),traceback=traceback.format_exc());await page.screenshot(path=str(a.report/'browser/supplemental-failure.png'),full_page=True)
  finally:
   (a.report/'final-preview-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');await browser.close()
asyncio.run(main());print(json.dumps({'status':result['status'],'checks':result['checks'],'exception':result.get('exception')}));raise SystemExit(result['status']!='passed')
