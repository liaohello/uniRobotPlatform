"""Map and route slice acceptance, run in two clearly separated modes.

  --mode live     against the 18953 candidate, which really serves the map catalog,
                  PGM raster, route drafts and immutable versions. Writes are limited to
                  route-draft resources for a dedicated test route; the delivered sample
                  route is only read back and compared.
  --mode offline  against 18949, which has no map/route endpoints: the catalog read must
                  fail explicitly, the labelled offline fixture stays usable for editing,
                  backend writes stay blocked, and the Simulation navigation mini view
                  keeps working next to the real 3D workbench.

Both modes assert that no motion, STOP, RESET, recording, navigation execution, session
or native command request is ever issued.
"""
import argparse, asyncio, json, re, time, traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

p = argparse.ArgumentParser()
p.add_argument('url'); p.add_argument('output', type=Path)
p.add_argument('--mode', choices=('live', 'offline'), default='live')
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
report = {'scope': f'{a.mode} map/route acceptance against {a.url}', 'mode': a.mode,
          'checks': [], 'errors': [], 'requests': [], 'real': {}, 'status': 'failed'}
SAMPLE_ROUTE = 'route-9e55257fc5d24a03a54986d9fcaa8a80'
SAMPLE_DIGESTS = {'v1': 'a9ee5895be83db986da5ea830fb12beff74f657feeba80d9e3ef5844dd484e62',
                  'v2': '370d246234a251d7adc8b8f1205c745a2ca37ebf4ea50b1d7f64f5aabaa7871c'}
ROOM = 'map_room_a_g3b_release_v1/v1'


def check(name, condition, detail=None):
    if not condition: raise AssertionError(name if detail is None else f'{name} :: {detail}')
    report['checks'].append(name)


async def open_scene(page):
    await page.goto(a.url + '/?inspect=1', wait_until='domcontentloaded')
    if a.mode == 'offline':
        await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0', timeout=90000)
    else:
        await page.wait_for_selector('.side-nav button', timeout=60000)
    await page.get_by_role('button', name='场景布置', exact=True).click()
    await page.wait_for_selector('.scene-setup [data-map-editor]', timeout=20000)


async def place_two_points(page):
    box = await page.locator('.scene-setup .map-canvas').bounding_box()
    for fraction in (0.35, 0.62):
        await page.mouse.click(box['x'] + box['width'] * fraction, box['y'] + box['height'] * 0.5)
        await page.wait_for_timeout(250)
    await page.wait_for_function("()=>document.querySelectorAll('.scene-setup [data-waypoint-id]').length===2", timeout=15000)
    return await page.locator('.scene-setup [data-waypoint-id]').evaluate_all('els=>els.map(e=>e.getAttribute("data-waypoint-id"))')


async def set_pose(page, point_id, x_m, y_m, yaw_deg):
    await page.locator(f'.scene-setup [data-route-point="{point_id}"] button.route-point-main').click()
    if x_m is not None:
        await page.get_by_role('spinbutton', name='Waypoint X', exact=True).fill(str(x_m))
        await page.get_by_role('spinbutton', name='Waypoint Y', exact=True).fill(str(y_m))
    await page.get_by_role('spinbutton', name='Waypoint yaw deg', exact=True).fill(str(yaw_deg))
    await page.get_by_role('spinbutton', name='Waypoint yaw deg', exact=True).press('Tab')
    await page.wait_for_timeout(200)


async def yaw_of(page, point_id):
    return await page.locator(f'.scene-setup [data-waypoint-id="{point_id}"]').get_attribute('data-yaw-rad')


async def editing_rules(page):
    ids = await place_two_points(page)
    unset = await page.locator('.scene-setup [data-waypoint-id]').evaluate_all('els=>els.map(e=>e.getAttribute("data-yaw-rad"))')
    check('freshly placed points have no orientation instead of a silent 0', all(value == '' for value in unset), unset)
    box = await page.locator(f'.scene-setup [data-yaw-handle="{ids[0]}"]').bounding_box()
    await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    await page.mouse.down(); await page.mouse.up()
    check('a zero-length direction drag does not write 0 degrees', await yaw_of(page, ids[0]) == '')
    await page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    await page.mouse.down()
    await page.mouse.move(box['x'] + box['width'] / 2 + 40, box['y'] + box['height'] / 2 - 24, steps=6)
    await page.mouse.up()
    await page.wait_for_function("(id)=>document.querySelector(`.scene-setup [data-waypoint-id=\"${id}\"]`)?.getAttribute('data-yaw-rad')!==''", arg=ids[0], timeout=15000)
    dragged = float(await yaw_of(page, ids[0]))
    check('a real direction drag sets a normalised radian orientation', -3.14159 <= dragged < 3.14159, dragged)
    await set_pose(page, ids[0], None, None, 355)
    check('UI degrees become wire radians in [-pi, pi)', abs(float(await yaw_of(page, ids[0])) + 0.0872664626) < 1e-6)
    await set_pose(page, ids[0], None, None, 180)
    check('180 degrees normalises to -pi', abs(float(await yaw_of(page, ids[0])) + 3.14159265) < 1e-6)
    await set_pose(page, ids[0], None, None, 0)
    check('an explicit 0 degrees is a valid orientation', await yaw_of(page, ids[0]) == '0')
    return ids


async def live_flow(page):
    await page.wait_for_selector('.scene-setup [data-map-catalog="ready"]', timeout=25000)
    fields = page.locator('.scene-setup [data-map-catalog-source]')
    check('map catalog is the declared local package source and is not live',
          await fields.get_attribute('data-map-catalog-source') == 'local_map_packages'
          and await fields.get_attribute('data-map-catalog-live') == 'false'
          and await fields.get_attribute('data-map-catalog-supported') == 'true')
    check('catalog lists the fixed G3B map versions', await page.locator('.scene-setup [data-map-option]').count() >= 2)
    await page.locator(f'.scene-setup [data-map-option="{ROOM}"]').click()
    await page.wait_for_function("()=>document.querySelector('.scene-setup [data-image-verified]')?.getAttribute('data-image-verified')==='true'", timeout=25000)
    authority = page.locator('.scene-setup [data-map-authority-source]')
    check('real map provenance is explicit: historical offline, not live SLAM',
          await authority.get_attribute('data-map-authority-source') == 'g3b_historical_offline'
          and await authority.get_attribute('data-map-live') == 'false'
          and await authority.get_attribute('data-map-test-only') == 'false')
    declared = await page.locator('.scene-setup [data-map-image-sha]').get_attribute('data-map-image-sha')
    image = page.locator('.scene-setup [data-image-verified]')
    actual = await image.get_attribute('data-image-sha')
    check('served raster bytes match the declared image digest', declared == actual and re.fullmatch(r'[0-9a-f]{64}', actual or '') is not None, (declared, actual))
    evidence = await image.inner_text()
    check('decoded PGM geometry matches the declared grid', '59×47' in evidence and 'P5' in evidence and '2786 B' in evidence, evidence)
    check('the verified bytes are what gets painted',
          (await page.locator('.scene-setup .map-canvas image').get_attribute('href') or '').startswith('data:image/png;base64,'))
    check('grid geometry, frame and origin come from the backend',
          await page.locator('.scene-setup [data-map-dims]').get_attribute('data-map-dims') == '59x47'
          and await page.locator('.scene-setup [data-map-frame]').get_attribute('data-map-frame') == 'map'
          and await page.locator('.scene-setup [data-map-id]').get_attribute('data-map-id') == 'map_room_a_g3b_release_v1')
    convention = page.locator('.scene-setup [data-map-convention]')
    check('declared coordinate convention is shown, including the cell centre rule',
          'image_lower_left_corner_in_map_frame' in await convention.inner_text()
          and await convention.get_attribute('data-map-convention') == 'col+0.5,row+0.5')
    compat = page.locator('.scene-setup [data-map-compatibility]')
    check('G1 incompatibility and navigation inelegance are stated, not smoothed',
          await compat.get_attribute('data-map-compatibility') == 'incompatible'
          and await compat.get_attribute('data-map-g1-status') == 'failed'
          and await compat.get_attribute('data-map-navigation-eligible') == 'false')
    verified = page.locator('.scene-setup [data-map-assets-verified]')
    check('assets_verified is scoped to declared asset digests, not whole-package truth',
          '不等于 live SLAM' in await verified.inner_text()
          and await verified.get_attribute('data-map-assets-verified') == 'true'
          and 'not_checked' in await page.locator('.scene-setup [data-map-current-runtime]').inner_text())
    report['real']['map'] = {'room': ROOM, 'image_sha256': actual, 'evidence': evidence}

    await page.locator('.scene-setup [data-map-offline-switch]').click()
    check('the offline fixture stays a labelled, write-blocked source',
          await page.locator('.scene-setup [data-scene-map-mode]').get_attribute('data-scene-map-mode') == 'offline-test'
          and await page.locator('.scene-setup [data-route-create]').get_attribute('data-route-create') == 'blocked'
          and '离线测试地图' in (await page.locator('.scene-setup [data-route-create]').get_attribute('title') or ''))
    await page.locator(f'.scene-setup [data-map-option="{ROOM}"]').click()
    await page.wait_for_function("()=>document.querySelector('.scene-setup [data-image-verified]')?.getAttribute('data-image-verified')==='true'", timeout=25000)

    ids = await editing_rules(page)
    sample = await (await page.request.get(f'{a.url}/api/v1/routes/{SAMPLE_ROUTE}/versions/v2')).json()
    poses = [(item['x_m'], item['y_m']) for item in sample['waypoints']]
    check('known-free poses come from the read-only sample route', len(poses) == 2, poses)
    await set_pose(page, ids[0], poses[0][0], poses[0][1], 28.6438)
    await set_pose(page, ids[1], poses[1][0], poses[1][1], 0)
    written = await page.locator('.scene-setup [data-waypoint-id]').evaluate_all('els=>els.map(e=>[e.getAttribute("data-map-x"),e.getAttribute("data-map-y"),e.getAttribute("data-yaw-rad")])')
    check('points carry real map coordinates and an explicit 0 degree yaw is kept',
          float(written[0][0]) == poses[0][0] and float(written[1][0]) == poses[1][0]
          and abs(float(written[0][2]) - 0.5) < 1e-4 and float(written[1][2]) == 0.0, written)
    stamp = f'front-m1.3-{int(time.time())}'
    await page.get_by_label('路线名称', exact=True).fill(f'{stamp} 初始草案')
    await page.wait_for_selector('.scene-setup [data-route-create="ready"]', timeout=15000)
    await page.locator('.scene-setup [data-route-create]').click()
    await page.wait_for_selector('.scene-setup [data-draft-bound="true"]', timeout=25000)
    route_id = await page.locator('.scene-setup [data-route-id]').get_attribute('data-route-id')
    digest_first = await page.locator('.scene-setup [data-content-digest]').get_attribute('data-content-digest')
    check('POST route-drafts returned a real route id, revision 1 and a server digest',
          bool(route_id) and route_id.startswith('route-') and route_id != SAMPLE_ROUTE
          and await page.locator('.scene-setup [data-draft-revision]').get_attribute('data-draft-revision') == '1'
          and re.fullmatch(r'[0-9a-f]{64}', digest_first or '') is not None, route_id)
    check('the server draft keeps the map binding and states the real validation scope',
          await page.locator('.scene-setup [data-map-ref]').get_attribute('data-map-ref') == 'map_room_a_g3b_release_v1/v1/map'
          and await page.locator('.scene-setup [data-pose-checks]').get_attribute('data-pose-checks') == 'true'
          and await page.locator('.scene-setup [data-arrival]').get_attribute('data-arrival') == 'not_checked')
    check('a freshly created draft matches the server', await page.locator('.scene-setup [data-route-dirty]').get_attribute('data-route-dirty') == 'false')
    report['real']['route_id'] = route_id
    await page.screenshot(path=str(a.output / 'live-draft.png'), full_page=True)

    await set_pose(page, ids[1], None, None, 90)
    check('an orientation-only edit is a local change until the server accepts it',
          await page.locator('.scene-setup [data-route-dirty]').get_attribute('data-route-dirty') == 'true')
    await page.locator('.scene-setup [data-route-save]').click()
    await page.wait_for_function("(before)=>document.querySelector('.scene-setup [data-draft-revision]').getAttribute('data-draft-revision')==='2' && document.querySelector('.scene-setup [data-content-digest]').getAttribute('data-content-digest')!==before", arg=digest_first, timeout=25000)
    digest_saved = await page.locator('.scene-setup [data-content-digest]').get_attribute('data-content-digest')
    check('PUT with base_revision advanced the server revision and digest', digest_saved != digest_first)
    check('a route without published versions reads as empty, not as a failure',
          await page.locator('.scene-setup [data-route-version-count]').get_attribute('data-route-version-count') == '0'
          and await page.locator('.scene-setup [data-versions-error]').count() == 0)
    await page.locator('.scene-setup [data-route-publish]').click()
    await page.wait_for_function("()=>document.querySelector('.scene-setup [data-route-version-count]').getAttribute('data-route-version-count')==='1'", timeout=25000)
    check('the backend reports a newly created version, not a reused one',
          await page.locator('.scene-setup [data-publish-note]').get_attribute('data-publish-note') == 'published')
    v1_digest = await page.locator('.scene-setup [data-version-option="v1"]').get_attribute('data-version-digest')
    check('publish produced a fixed v1 whose digest is the server digest', v1_digest == digest_saved, (v1_digest, digest_saved))
    check('adoption and execution stay disabled because the backend says so',
          await page.locator('.scene-setup [data-route-adopt]').is_disabled()
          and await page.locator('.scene-setup [data-route-execute]').is_disabled()
          and 'adoption_supported=false' in await page.locator('.scene-setup').inner_text())

    await page.locator(f'.scene-setup [data-route-point="{ids[0]}"] [aria-label="下移 {ids[0]}"]').click()
    moved_ids = await page.locator('.scene-setup [data-route-point]').evaluate_all('els=>els.map(e=>e.getAttribute("data-route-point"))')
    check('reorder keeps stable waypoint IDs', sorted(moved_ids) == sorted(ids) and moved_ids != ids)
    await page.locator('.scene-setup [data-route-save]').click()
    await page.wait_for_function("()=>document.querySelector('.scene-setup [data-draft-revision]').getAttribute('data-draft-revision')==='3'", timeout=25000)
    await page.locator('.scene-setup [data-route-publish]').click()
    await page.wait_for_function("()=>document.querySelector('.scene-setup [data-route-version-count]').getAttribute('data-route-version-count')==='2'", timeout=25000)
    options = await page.locator('.scene-setup [data-version-option]').evaluate_all('els=>els.map(e=>[e.getAttribute("data-version-option"),e.getAttribute("data-version-digest")])')
    check('versions list newest first and v1 keeps its original digest',
          [item[0] for item in options] == ['v2', 'v1'] and options[0][1] != options[1][1] and options[1][1] == v1_digest, options)
    await page.locator('.scene-setup [data-version-option="v1"]').click()
    await page.wait_for_selector('.scene-setup [data-version-view="v1"]', timeout=25000)
    fixed = page.locator('.scene-setup [data-version-view="v1"]')
    check('the opened fixed version is the immutable document, not the live draft',
          await fixed.get_attribute('data-version-digest') == v1_digest
          and await fixed.get_attribute('data-nav-eligible') == 'false'
          and await fixed.get_attribute('data-adoption-supported') == 'false'
          and await fixed.get_attribute('data-execution-supported') == 'false')
    v1_doc = await (await page.request.get(f'{a.url}/api/v1/routes/{route_id}/versions/v1')).json()
    check('the stored v1 kept the original waypoint IDs', [item['id'] for item in v1_doc['waypoints']] == ids, v1_doc['waypoints'])
    report['real']['versions'] = {'v1': v1_digest, 'v2': options[0][1]}

    external = await page.request.put(f'{a.url}/api/v1/route-drafts/{route_id}', data=json.dumps({
        'name': f'{stamp} 外部宿主改名', 'map_ref': {'map_id': 'map_room_a_g3b_release_v1', 'version': 'v1', 'frame': 'map'},
        'waypoints': v1_doc['waypoints'], 'base_revision': 3}), headers={'Content-Type': 'application/json'})
    check('an external host save advances the same draft revision', external.status == 200 and (await external.json())['draft_revision'] == 4, external.status)
    await set_pose(page, ids[1], None, None, 120)
    await page.locator('.scene-setup [data-route-save]').click()
    await page.wait_for_selector('.scene-setup [data-route-conflict]', timeout=25000)
    clash = page.locator('.scene-setup [data-route-conflict]')
    clash_text = await clash.inner_text()
    check('stale base_revision yields the real 409 code and current_revision',
          await clash.get_attribute('data-route-conflict') == 'route_draft_revision_conflict'
          and 'current_revision=4' in clash_text, clash_text)
    check('the conflict names the server revision instead of a local guess',
          '服务端为' not in clash_text and '服务器内容未被覆盖' in clash_text, clash_text)
    local_yaw = await yaw_of(page, ids[1])
    check('local edits survive the conflict', abs(float(local_yaw) - 2.0943951) < 1e-4, local_yaw)
    await page.screenshot(path=str(a.output / 'live-conflict.png'), full_page=True)
    await page.locator('.scene-setup [data-reload-server]').click()
    await page.wait_for_function("()=>document.querySelector('.scene-setup [data-draft-revision]').getAttribute('data-draft-revision')==='4'", timeout=25000)
    check('explicit reload adopts the server draft and clears the conflict',
          await page.locator('.scene-setup [data-route-conflict]').count() == 0
          and await page.locator('.scene-setup [data-route-dirty]').get_attribute('data-route-dirty') == 'false')

    await page.reload(wait_until='domcontentloaded')
    await page.wait_for_selector('.side-nav button', timeout=60000)
    await page.get_by_role('button', name='场景布置', exact=True).click()
    await page.wait_for_function(f"()=>document.querySelector('.scene-setup [data-route-id]')?.getAttribute('data-route-id')==='{route_id}'", timeout=40000)
    check('after a reload the draft and versions reopen by route_id from the URL',
          await page.locator('.scene-setup [data-route-version-count]').get_attribute('data-route-version-count') == '2'
          and await page.locator('.scene-setup [data-image-verified]').get_attribute('data-image-verified') == 'true')
    await page.get_by_label('按 route_id 打开', exact=True).fill(SAMPLE_ROUTE)
    await page.locator('.scene-setup [data-route-open]').click()
    await page.wait_for_function(f"()=>document.querySelector('.scene-setup [data-route-id]').getAttribute('data-route-id')==='{SAMPLE_ROUTE}'", timeout=25000)
    check('a route_id opens explicitly because no route collection API exists',
          await page.locator('.scene-setup [data-route-version-count]').get_attribute('data-route-version-count') == '2')
    await page.get_by_label('按 route_id 打开', exact=True).fill(route_id)
    await page.locator('.scene-setup [data-route-open]').click()
    await page.wait_for_function(f"()=>document.querySelector('.scene-setup [data-route-id]').getAttribute('data-route-id')==='{route_id}'", timeout=25000)

    # Deterministic async transaction behaviour: one selection is one transaction.
    non_get_before = len([r for r in report['requests'] if r['method'] != 'GET'])
    options_list = await page.locator('.scene-setup [data-map-option]').evaluate_all('els=>els.map(e=>e.getAttribute("data-map-option"))')
    other = next(item for item in options_list if item != ROOM)

    async def slow_version(route):
        response = await route.fetch()
        await asyncio.sleep(3.0)
        await route.fulfill(response=response)
    await page.route('**/api/v1/maps/**', slow_version)
    await page.locator(f'.scene-setup [data-map-option="{other}"]').click()
    await page.locator('.scene-setup [data-map-offline-switch]').click()
    await asyncio.sleep(5.5)
    check('a switch to the offline fixture wins against the still-pending map read',
          await page.locator('.scene-setup [data-scene-map-mode]').get_attribute('data-scene-map-mode') == 'offline-test')
    check('the late success cannot resurrect a backend map nor clear the offline state',
          await page.locator('.scene-setup dl[data-map-source]').get_attribute('data-map-source') == 'offline_test_fixture'
          and await page.locator('.scene-setup [data-map-offline="true"]').count() == 1
          and await page.locator('.scene-setup [data-map-error]').count() == 0)

    await page.unroute('**/api/v1/maps/**', slow_version)

    async def corrupt_raster(route):
        if urlsplit(route.request.url).path.endswith('/image'):
            await route.fulfill(status=200, content_type='application/octet-stream', body='P5\n59 47\n255\n' + '0' * 40)
        else: await route.continue_()
    await page.route('**/api/v1/maps/**', corrupt_raster)
    await page.locator(f'.scene-setup [data-map-option="{ROOM}"]').click()
    await page.wait_for_selector('.scene-setup [data-map-error]', timeout=25000)
    error_text = await page.locator('.scene-setup [data-map-error]').inner_text()
    check('a raster failing digest validation reports the real pgm code', 'digest_mismatch' in error_text, error_text)
    create_state = await page.locator('.scene-setup [data-route-create]').get_attribute('data-route-create')
    save_reason = await page.locator('.scene-setup [data-route-save]').get_attribute('data-route-save-reason')
    offline_shown = await page.locator('.scene-setup [data-map-offline="true"]').count()
    check('write eligibility follows the failed validation of the map bound to this route',
          create_state == 'blocked' and '校验失败' in save_reason, f'{create_state} · {save_reason}')
    check('a failed backend map read stays visible instead of silently showing the offline fixture as usable',
          bool(error_text) and offline_shown <= 1, error_text[:120])
    check('no route write is issued after the validation failure',
          len([r for r in report['requests'] if r['method'] != 'GET']) == non_get_before,
          [f"{r['method']} {urlsplit(r['url']).path}" for r in report['requests'] if r['method'] != 'GET'][non_get_before:][:4])
    await page.unroute('**/api/v1/maps/**', corrupt_raster)
    await page.locator(f'.scene-setup [data-map-option="{ROOM}"]').click()
    await page.wait_for_function("()=>document.querySelector('.scene-setup [data-image-verified]')?.getAttribute('data-image-verified')==='true'", timeout=25000)
    check('a superseded failed validation does not stick after a clean re-read',
          await page.locator('.scene-setup [data-map-error]').count() == 0
          and await page.locator('.scene-setup [data-route-save]').get_attribute('data-route-save') == 'ready'
          and await page.locator('.scene-setup [data-image-verified]').get_attribute('data-image-verified') == 'true')

    # Publish semantics: the result names the server revision it came from.
    await set_pose(page, ids[0], None, None, 45)
    revision_before = await page.locator('.scene-setup [data-draft-revision]').get_attribute('data-draft-revision')
    server_digest = await page.locator('.scene-setup [data-content-digest]').get_attribute('data-content-digest')
    await page.locator('.scene-setup [data-route-publish]').click()
    await page.wait_for_selector('.scene-setup [data-publish-note]', timeout=25000)
    published = page.locator('.scene-setup [data-publish-note]')
    publish_text = await published.inner_text()
    check('publish names the exact server draft revision it published',
          await published.get_attribute('data-publish-revision') == revision_before
          and await published.get_attribute('data-publish-version') in ('v1', 'v2', 'v3'), f'{revision_before} · {publish_text[:80]}')
    check('unsaved local edits are warned about instead of pretending to be published',
          await published.get_attribute('data-publish-dirty') == 'true' and '没有被包含在本次发布' in publish_text, publish_text)
    check('the published digest is the server draft digest, not the dirty local content',
          await published.get_attribute('data-publish-digest') == server_digest, (await published.get_attribute('data-publish-digest'), server_digest))

    await page.get_by_role('button', name='Simulation', exact=True).click()
    text = await page.locator('main').inner_text()
    check('the 3D workbench states this candidate read contract is unusable instead of pretending to render',
          '3D 数据源不可用' in text and ('envelope' in text or 'geometry' in text), text[:220])

    after = await (await page.request.get(f'{a.url}/api/v1/routes/{SAMPLE_ROUTE}/versions')).json()
    digests = {item['version']: item['content_digest'] for item in after['versions']}
    check('the delivered sample route v1/v2 are untouched', digests == SAMPLE_DIGESTS, digests)


async def offline_flow(page):
    await page.wait_for_selector('.scene-setup [data-map-catalog="failed"]', timeout=25000)
    check('a backend without map endpoints fails the catalog read explicitly',
          bool(await page.locator('.scene-setup [data-map-catalog-error]').inner_text()))
    check('the labelled offline fixture remains the active, write-blocked source',
          await page.locator('.scene-setup [data-scene-map-mode]').get_attribute('data-scene-map-mode') == 'offline-test'
          and await page.locator('.scene-setup [data-route-create]').get_attribute('data-route-create') == 'blocked'
          and await page.locator('.scene-setup dl[data-map-source]').get_attribute('data-map-source') == 'offline_test_fixture')
    ids = await editing_rules(page)
    await set_pose(page, ids[1], None, None, 30)
    check('an unset orientation still blocks route writes',
          await page.locator('.scene-setup [data-route-create]').get_attribute('data-route-create') == 'blocked')
    await page.get_by_role('button', name='Simulation', exact=True).click()
    await page.wait_for_function('window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0', timeout=60000)
    await page.get_by_role('button', name='导航小窗', exact=True).click()
    await page.wait_for_selector('[data-nav-mini] [data-map-editor]', timeout=15000)
    mini = page.locator('[data-nav-mini]')
    mini_text = await mini.text_content()
    check('mini view follows the unbound local draft and stays read-only',
          await mini.get_attribute('data-nav-source') == 'local-unbound'
          and await mini.get_attribute('data-nav-map-mode') == 'offline-test'
          and '本地草案' in mini_text and '非规划安全路径' in mini_text and '执行反馈：无' in mini_text, (mini_text or '')[:200])
    await page.screenshot(path=str(a.output / 'offline-mini.png'), full_page=True)


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
        page = await browser.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=1, timezone_id='America/Los_Angeles')
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.on('request', lambda req: report['requests'].append({'method': req.method, 'url': req.url}))
        try:
            await open_scene(page)
            if a.mode == 'live': await live_flow(page)
            else: await offline_flow(page)
            writes = [r for r in report['requests'] if r['method'] != 'GET']
            check('every write is a route-draft resource call and never touches the sample route',
                  all(urlsplit(r['url']).path.startswith('/api/v1/route-drafts') and SAMPLE_ROUTE not in r['url'] for r in writes),
                  [f"{r['method']} {urlsplit(r['url']).path}" for r in writes][:6])
            forbidden = [r['url'] for r in report['requests'] if any(token in urlsplit(r['url']).path for token in
                       ('/commands', '/episodes', '/reset', '/recording', '/start', '/stop', '/sessions', '/runs'))]
            check('no session, motion, STOP, RESET, recording or navigation endpoint was called', not forbidden, forbidden[:3])
            mobilecar = [r for r in report['requests'] if '/api/v1/mobilecar/' in r['url']]
            check('mobilecar reads stay GET-only', all(r['method'] == 'GET' for r in mobilecar))
            invented = [r['url'] for r in report['requests'] if r['url'].endswith('/api/v1/routes') or '/api/v1/route-drafts?' in r['url']]
            check('no route collection listing was invented', not invented, invented[:3])
            check('no uncaught browser errors', not report['errors'], report['errors'][:3])
            report['real']['request_count'] = len(report['requests'])
            report['real']['write_requests'] = [f"{r['method']} {urlsplit(r['url']).path}" for r in writes]
            report['status'] = 'passed'
        except Exception as exc:
            report['exception'] = str(exc); report['traceback'] = traceback.format_exc()
            await page.screenshot(path=str(a.output / 'failure.png'), full_page=True)
        finally:
            (a.output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            await browser.close()

asyncio.run(main())
print(json.dumps({'status': report['status'], 'mode': a.mode, 'checks': len(report['checks']), 'error': report.get('exception')}, ensure_ascii=False))
raise SystemExit(report['status'] != 'passed')
