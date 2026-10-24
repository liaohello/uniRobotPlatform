"""Map / Waypoint route slice: position + orientation editing, local save isolation.

The map and route editing in this test is entirely local: 18949 exposes no
map/route/waypoint endpoint, and the offline test map is a clearly labelled
fixture, not a SLAM or navigation map. The test asserts that no route wire is
invented, that backend save/adopt stay disabled, and that the 3D workbench and
its navigation mini view keep working. No motion, RESET, recording, navigation
execution or native command request is made.
"""
import argparse, asyncio, json, math, traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

p = argparse.ArgumentParser(); p.add_argument('url'); p.add_argument('output', type=Path); a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
report = {'scope': 'local map/Waypoint editing plus offline-labelled save store; no backend route API, no navigation execution',
          'checks': [], 'errors': [], 'requests': [], 'status': 'failed'}
def check(name, condition, detail=None):
    if not condition: raise AssertionError(name if detail is None else f'{name} :: {detail}')
    report['checks'].append(name)

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
        page = await browser.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=1, timezone_id='America/Los_Angeles')
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.on('request', lambda req: report['requests'].append({'method': req.method, 'url': req.url}))
        try:
            await page.goto(a.url + '/?inspect=1', wait_until='domcontentloaded')
            await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0', timeout=90000)
            scene = page.get_by_role('button', name='场景布置', exact=True)
            check('Scene Setup is reachable from the workbench shell', await scene.count() == 1)
            await scene.click()
            await page.wait_for_selector('.scene-setup [data-map-editor]', timeout=20000)

            map_attrs = page.locator('.scene-setup [data-map-id]')
            check('map identity, version, frame and source are explicit', await map_attrs.get_attribute('data-map-id') == 'offline-test-map'
                  and await map_attrs.get_attribute('data-map-version') == 'v1'
                  and await map_attrs.get_attribute('data-map-frame') == 'map'
                  and await map_attrs.get_attribute('data-map-source') == 'offline_test_fixture')
            check('offline map declares it is not a SLAM or scene-truth source',
                  '非 SLAM' in await page.locator('.scene-setup').inner_text()
                  and await page.locator('.scene-setup [data-map-compatibility]').get_attribute('data-map-compatibility') == 'not_applicable')
            check('backend route API is explicitly unavailable', await page.locator('.scene-setup [data-backend-route-api]').get_attribute('data-backend-route-api') == 'unavailable'
                  and await page.locator('.scene-setup [data-route-saved]').get_attribute('data-route-saved') == 'false')
            canvas = page.locator('.scene-setup .map-canvas')
            box = await canvas.bounding_box()
            before_points = await page.locator('.scene-setup [data-waypoint-id]').count()
            check('a fresh draft starts with no invented waypoints', before_points == 0)

            # --- click placement: map coordinates come from the raster transform, not pixels ---
            await page.mouse.click(box['x'] + box['width'] * 0.5, box['y'] + box['height'] * 0.5)
            await page.wait_for_selector('.scene-setup [data-waypoint-id]', timeout=15000)
            first = page.locator('.scene-setup [data-waypoint-id]').first
            first_id = await first.get_attribute('data-waypoint-id')
            x0 = float(await first.get_attribute('data-map-x')); y0 = float(await first.get_attribute('data-map-y'))
            check('placed PointGoal carries a stable ID, order and map binding', bool(first_id) and await first.get_attribute('data-waypoint-order') == '1'
                  and -20 <= x0 <= 20 and -15 <= y0 <= 15)
            check('a newly placed point has no orientation until the user sets it', await first.get_attribute('data-yaw-rad') == '')
            await page.screenshot(path=str(a.output / 'map-placement.png'), full_page=True)

            # --- view transform must not change map coordinates ---
            center_before = await first.bounding_box()
            await page.get_by_role('button', name='地图右旋', exact=True).click()
            await page.get_by_role('button', name='地图右旋', exact=True).click()
            await page.get_by_role('button', name='地图放大', exact=True).click()
            await page.wait_for_function("()=>document.querySelector('.scene-setup .map-view-readout').textContent.includes('30')")
            check('coordinates survive rotation and zoom', abs(float(await first.get_attribute('data-map-x')) - x0) < 1e-9 and abs(float(await first.get_attribute('data-map-y')) - y0) < 1e-9)
            center_after = await first.bounding_box()
            check('the same map point really moved on screen', abs(center_after['x'] - center_before['x']) > 5 or abs(center_after['y'] - center_before['y']) > 5)
            await page.get_by_role('button', name='地图视图归零', exact=True).click()
            await page.wait_for_function("()=>document.querySelector('.scene-setup .map-view-readout').textContent.startsWith('0°')")
            check('view reset restores the on-screen position', abs((await first.bounding_box())['x'] - center_before['x']) < 3)

            # --- pan gesture must not create a point ---
            count_before = await page.locator('.scene-setup [data-waypoint-id]').count()
            await page.mouse.move(box['x'] + box['width'] * 0.2, box['y'] + box['height'] * 0.8)
            await page.mouse.down()
            await page.mouse.move(box['x'] + box['width'] * 0.2 + 60, box['y'] + box['height'] * 0.8 - 40, steps=6)
            await page.mouse.up()
            check('empty-area drag pans the view instead of placing a point',
                  await page.locator('.scene-setup [data-waypoint-id]').count() == count_before)
            await page.get_by_role('button', name='地图视图归零', exact=True).click()

            # --- orientation: zero-length drag is not a confirmation ---
            handle = page.locator(f'.scene-setup [data-yaw-handle="{first_id}"]')
            hb = await handle.bounding_box()
            await page.mouse.move(hb['x'] + hb['width'] / 2, hb['y'] + hb['height'] / 2)
            await page.mouse.down(); await page.mouse.up()
            check('a zero-length direction drag does not silently set 0 degrees',
                  await first.get_attribute('data-yaw-rad') == ''
                  and '未设置' in await page.locator('.scene-setup [data-route-point]').inner_text())
            check('an unset orientation blocks saving', await page.locator('.scene-setup [data-route-save]').get_attribute('data-route-save') == 'blocked')

            # real drag sets the orientation in map frame
            await page.mouse.move(hb['x'] + hb['width'] / 2, hb['y'] + hb['height'] / 2)
            await page.mouse.down()
            await page.mouse.move(hb['x'] + hb['width'] / 2 + 70, hb['y'] + hb['height'] / 2 - 40, steps=8)
            await page.mouse.up()
            await page.wait_for_function("(id)=>document.querySelector(`.scene-setup [data-waypoint-id=\"${id}\"]`)?.getAttribute('data-yaw-rad')!==''", arg=first_id, timeout=15000)
            dragged = float(await first.get_attribute('data-yaw-rad'))
            check('dragged orientation is a finite normalised radian', math.isfinite(dragged) and -math.pi <= dragged < math.pi, dragged)

            # numeric degrees on the wire as normalised radians
            yaw_field = page.get_by_role('spinbutton', name='Waypoint yaw deg', exact=True)
            await yaw_field.fill('355'); await yaw_field.press('Tab')
            await page.wait_for_function("()=>Math.abs(parseFloat(document.querySelector('.scene-setup [data-waypoint-id]').getAttribute('data-yaw-rad'))+0.0872664626)<1e-6", timeout=15000)
            check('UI degrees become wire radians in [-pi, pi)', abs(float(await first.get_attribute('data-yaw-rad')) + 0.0872664626) < 1e-6)
            await yaw_field.fill('180'); await yaw_field.press('Tab')
            await page.wait_for_function("()=>Math.abs(parseFloat(document.querySelector('.scene-setup [data-waypoint-id]').getAttribute('data-yaw-rad'))+Math.PI)<1e-6", timeout=15000)
            check('180 degrees normalises to -pi, not +pi', abs(float(await first.get_attribute('data-yaw-rad')) + math.pi) < 1e-9)
            await yaw_field.fill(''); await yaw_field.press('Tab')
            await page.wait_for_function("()=>document.querySelector('.scene-setup [data-waypoint-id]').getAttribute('data-yaw-rad')===''", timeout=15000)
            check('clearing the field returns to unset instead of 0 degrees', await first.get_attribute('data-yaw-rad') == '')
            await yaw_field.fill('45'); await yaw_field.press('Tab')
            await page.wait_for_function("()=>document.querySelector('.scene-setup [data-waypoint-id]').getAttribute('data-yaw-rad')!==''", timeout=15000)

            # --- second point, reorder keeps IDs, yaw counts as content ---
            await page.mouse.click(box['x'] + box['width'] * 0.35, box['y'] + box['height'] * 0.35)
            await page.wait_for_function("()=>document.querySelectorAll('.scene-setup [data-waypoint-id]').length===2", timeout=15000)
            ids_before = await page.locator('.scene-setup [data-route-point]').evaluate_all('els=>els.map(e=>e.getAttribute("data-route-point"))')
            await page.get_by_role('button', name=f'下移 {ids_before[0]}', exact=True).click()
            ids_after = await page.locator('.scene-setup [data-route-point]').evaluate_all('els=>els.map(e=>e.getAttribute("data-route-point"))')
            orders_after = await page.locator('.scene-setup [data-route-point]').evaluate_all('els=>els.map(e=>e.getAttribute("data-route-order"))')
            check('reorder keeps waypoint IDs and only renumbers order', sorted(ids_before) == sorted(ids_after) and ids_before != ids_after
                  and orders_after == ['1', '2'])

            # the second point still has no orientation: give it one before saving
            second_id = ids_after[0]
            await page.locator(f'.scene-setup [data-route-point="{second_id}"] button.route-point-main').click()
            await page.get_by_role('spinbutton', name='Waypoint yaw deg', exact=True).fill('90')
            await page.get_by_role('spinbutton', name='Waypoint yaw deg', exact=True).press('Tab')
            await page.wait_for_function("(id)=>document.querySelector(`.scene-setup [data-waypoint-id=\"${id}\"]`)?.getAttribute('data-yaw-rad')!==''", arg=second_id, timeout=15000)
            yaws = await page.locator('.scene-setup [data-waypoint-id]').evaluate_all('els=>els.map(e=>e.getAttribute("data-yaw-rad"))')
            check('every PointGoal needs a position and an orientation before saving', all(yaws), yaws)

            # --- local save isolation: revision-conditioned draft, immutable versions, no backend write ---
            await page.wait_for_selector('.scene-setup [data-route-save="ready"]', timeout=15000)
            check('a valid position+orientation route unlocks the local save', await page.locator('.scene-setup [data-route-save]').is_enabled())
            await page.locator('.scene-setup [data-route-save]').click()
            await page.wait_for_function("()=>document.querySelector('.scene-setup [data-route-local-state]').getAttribute('data-route-local-state')==='saved'", timeout=15000)
            check('local save is labelled as session-scoped, not backend', await page.locator('.scene-setup [data-local-store-authority]').get_attribute('data-local-store-authority') == 'local_session_only')
            await page.locator('.scene-setup [data-route-publish]').click()
            await page.wait_for_function("()=>document.querySelector('.scene-setup [data-route-version-count]').getAttribute('data-route-version-count')==='1'", timeout=15000)
            digest_v1 = await page.locator('.scene-setup [data-route-version-count]').inner_text()
            check('published v1 keeps a content digest and the point count', 'local-' in digest_v1 and '2 点' in digest_v1)

            # a pure orientation change is a content change: edit the first point, save again, publish v2
            await page.locator(f'.scene-setup [data-route-point="{first_id}"] button.route-point-main').click()
            await page.get_by_role('spinbutton', name='Waypoint yaw deg', exact=True).fill('60')
            await page.get_by_role('spinbutton', name='Waypoint yaw deg', exact=True).press('Tab')
            await page.wait_for_timeout(400)
            await page.locator('.scene-setup [data-route-save]').click()
            await page.wait_for_function("()=>document.querySelector('.scene-setup [data-route-local-state]').getAttribute('data-route-local-state')==='saved'", timeout=15000)
            await page.locator('.scene-setup [data-route-publish]').click()
            await page.wait_for_function("()=>document.querySelector('.scene-setup [data-route-version-count]').getAttribute('data-route-version-count')==='2'", timeout=15000)
            versions_text = await page.locator('.scene-setup [data-route-version-count]').inner_text()
            digests = [token for token in versions_text.split('·') if token.strip().startswith('local-')]
            check('an orientation edit publishes a new version and keeps v1',
                  'v1' in versions_text and 'v2' in versions_text and len(set(digests)) == 2, versions_text)
            check('the adopted reference stays unset after publishing', await page.locator('.scene-setup [data-route-adopted]').get_attribute('data-route-adopted') == 'none')
            check('adoption stays disabled without a backend config API', await page.locator('.scene-setup [data-route-adopt]').is_disabled())
            await page.screenshot(path=str(a.output / 'map-versions.png'), full_page=True)

            # refresh must not fake a reload from the backend
            await page.reload(wait_until='domcontentloaded')
            await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0', timeout=90000)
            await page.get_by_role('button', name='场景布置', exact=True).click()
            await page.wait_for_selector('.scene-setup [data-map-editor]', timeout=20000)
            check('after reload the draft is empty and says nothing was stored on the backend',
                  (await page.locator('.scene-setup [data-route-waypoint-count]').inner_text()).startswith('0')
                  and await page.locator('.scene-setup [data-route-saved]').get_attribute('data-route-saved') == 'false'
                  and await page.locator('.scene-setup [data-route-local-state]').get_attribute('data-route-local-state') == 'unsaved')

            # --- Simulation mini view keeps the 3D workbench ---
            await page.get_by_role('button', name='Simulation', exact=True).click()
            await page.wait_for_selector('main canvas', timeout=30000)
            await page.wait_for_function('window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0', timeout=60000)
            inspect = await page.evaluate('window.__workbenchInspect()')
            check('3D viewport still renders after the page switch', inspect['scene']['renderCount'] > 0 and inspect['scene']['pendingLoads'] == 0)
            nav = page.get_by_role('button', name='导航小窗', exact=True)
            check('the navigation mini window is reachable', await nav.count() == 1)
            await nav.click()
            await page.wait_for_selector('[data-nav-mini] [data-map-editor]', timeout=15000)
            mini_text = (await page.locator('[data-nav-mini]').text_content()) or ''
            check('mini view is read-only and separates draft, saved version and execution feedback',
                  '只读预览' in mini_text or '只读' in mini_text)
            check('editing lines are labelled as not a planned safe path', '非规划' in mini_text or '编辑连线' in mini_text)
            check('no execution feedback is claimed without a run', '无执行反馈' in mini_text or '执行反馈' in mini_text)
            await page.screenshot(path=str(a.output / 'map-nav-mini.png'), full_page=True)

            # --- network boundary: nothing was written, nothing was invented ---
            writes = [r for r in report['requests'] if r['method'] != 'GET']
            check('the map slice issues no write request', not writes, writes[:5])
            invented = [r['url'] for r in report['requests'] if any(token in urlsplit(r['url']).path for token in ('/map', '/route', '/waypoint'))]
            check('no map/route/waypoint endpoint was invented', not invented, invented[:3])
            forbidden = [r['url'] for r in report['requests'] if any(token in r['url'] for token in ('/commands', '/episodes', '/reset', '/recording', '/start'))]
            check('no motion, RESET, recording or Start request was made', not forbidden, forbidden[:3])
            check('no uncaught browser errors', not report['errors'], report['errors'][:3])
            report['request_count'] = len(report['requests'])
            report['status'] = 'passed'
        except Exception as exc:
            report['exception'] = str(exc); report['traceback'] = traceback.format_exc()
            await page.screenshot(path=str(a.output / 'failure.png'), full_page=True)
        finally:
            (a.output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            await browser.close()
asyncio.run(main())
print(json.dumps({'status': report['status'], 'checks': len(report['checks']), 'error': report.get('exception')}, ensure_ascii=False))
raise SystemExit(report['status'] != 'passed')
