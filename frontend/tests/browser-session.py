"""Stateful synthetic 18949 Session protocol fixtures for the frontend.

All platform configuration/session responses in this test are synthetic and live
in this process only. Mobilecar scene/snapshot/actual reads still come from the
live preview, so the real 3D workspace stays in the loop. The fixture exercises
the M1.2d contract: the Session list envelope, the single-Session read-only
`current` observation, offline / expired / identity-changed currents, prepared
TTL versus started lifecycle, and archive-versus-current separation.

No native motion, RESET, recording or command request is made. This test does
not certify a real prepared Session.
"""
import argparse, asyncio, copy, json, time, traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

p = argparse.ArgumentParser(); p.add_argument('url'); p.add_argument('output', type=Path); a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
report = {'scope': 'synthetic stateful 18949 Session envelope/current fixture; no native prepared/Start acceptance', 'synthetic': True,
          'checks': [], 'errors': [], 'requests': [], 'fixture_writes': [], 'status': 'failed'}
CHECK = lambda key: {'key': key, 'status': 'passed', 'phase': 'configuration', 'scope': 'synthetic fixture', 'detail': 'synthetic fixture value; not native evidence'}
def checks(): return [CHECK('fixture_configuration'), {**CHECK('fixture_readiness'), 'phase': 'readiness'}]
def check(name, condition, detail=None):
    if not condition: raise AssertionError(name if detail is None else f'{name} :: {detail}')
    report['checks'].append(name)

def validation(snapshot_id, execution_revision, fingerprint):
    return {'validation_id': 'val-' + snapshot_id, 'execution_revision': execution_revision, 'fingerprint': fingerprint,
            'recipe_fingerprint': 'c' * 64, 'checked_at': '2026-10-24T09:00:00+00:00', 'snapshot_id': snapshot_id,
            'snapshot_sha256': 'e' * 64, 'status': 'passed', 'checks': checks(), 'execution_eligible': True,
            'blocking_reasons': [], 'validated_snapshot_id': snapshot_id, 'reused': False}
def snapshot_record(draft_id, snapshot_id, execution_revision, fingerprint):
    return {'schema_version': 'unirobot-config-snapshot-1', 'snapshot_id': snapshot_id, 'snapshot_sha256': 'e' * 64,
            'created_at': '2026-10-24T09:00:00+00:00', 'draft_id': draft_id, 'draft_revision': 1,
            'execution_revision': execution_revision, 'fingerprint': fingerprint, 'recipe_fingerprint': 'c' * 64,
            'recipe': {'recipe_id': 'synthetic.fixture', 'recipe_revision': 3, 'sources': [{'role': 'fixture', 'path': 'synthetic', 'sha256': 'f' * 64}]},
            'observation': {'interface_profile': 'synthetic-fixture'}, 'kinematics': {'profile_id': 'landerpi.kinematics.v1', 'digest': 'f' * 64,
            'authority': 'synthetic_fixture', 'joint_order_consistent': True, 'user_limits_consistent': True,
            'tcp_mount_consistent': True, 'camera_mount_consistent': True, 'gripper_limits_consistent': True,
            'max_user_limit_error_rad': 0.0, 'limitations': ['synthetic fixture']},
            'checks': checks(), 'validation_status': 'passed', 'validation_scope': 'synthetic_fixture_only',
            'execution_eligible': True, 'validated_snapshot_id': snapshot_id, 'blocking_reasons': []}
def draft_record(draft_id, snapshot_id, execution_revision, fingerprint, name):
    return {'draft_id': draft_id, 'draft_revision': 1, 'execution_revision': execution_revision, 'fingerprint': fingerprint,
            'recipe_fingerprint': 'c' * 64, 'preset': {'preset_id': 'mobilecar.g1.teleop', 'native_commit': 'fixture', 'manifest_sha256': 'f' * 64,
            'recipe': {'editable_initial_state_fields': []}, 'expected': {}}, 'name': name, 'description': 'synthetic stateful fixture',
            'validation': {'status': 'passed', 'result': validation(snapshot_id, execution_revision, fingerprint)},
            'created_at': '2026-10-24T09:00:00+00:00', 'updated_at': '2026-10-24T09:00:00+00:00'}

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
        page = await browser.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=1, timezone_id='America/Los_Angeles')
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.on('request', lambda req: report['requests'].append({'method': req.method, 'url': req.url}))
        try:
            snap = await (await page.request.get(a.url + '/api/v1/mobilecar/snapshot')).json()
            caps = await (await page.request.get(a.url + '/api/v1/mobilecar/capabilities')).json()
            identity = copy.deepcopy(snap['runtime_identity'])
            fixture = {'identity': identity, 'session_identity': copy.deepcopy(identity), 'observed_at': '2026-10-24T09:00:00+00:00',
                       'preflight_count': 0, 'sessions_gets': 0, 'current_gets': 0, 'preflights': 0, 'create_mode': 'normal',
                       'start_mode': 'success', 'current_mode': 'valid', 'current_delay': 0.0, 'current_abort': False,
                       'create_calls': [], 'create_keys': [], 'start_calls': [], 'sessions': {}, 'created_by_key': {}, 'writes': []}
            fixture['drafts'] = [draft_record('draft-fixture-a', 'cs-fixture-a', 3, 'a' * 64, 'Synthetic Draft A'),
                                 draft_record('draft-fixture-b', 'cs-fixture-b', 4, 'b' * 64, 'Synthetic Draft B')]
            fixture['snapshots'] = {'cs-fixture-a': snapshot_record('draft-fixture-a', 'cs-fixture-a', 3, 'a' * 64),
                                    'cs-fixture-b': snapshot_record('draft-fixture-b', 'cs-fixture-b', 4, 'b' * 64)}

            def session_id_for(snapshot_id): return 'ps-fixture-' + snapshot_id.rsplit('-', 1)[-1]
            def new_session(body):
                sid = session_id_for(body['validated_snapshot_id'])
                now = '2026-10-24T09:00:00+00:00'
                return {'schema_version': 'unirobot-prepared-session-1', 'session_id': sid, 'state': 'prepared',
                        'created_at': now, 'updated_at': now, 'snapshot_id': body['validated_snapshot_id'],
                        'recipe_fingerprint': 'c' * 64, 'execution_revision': body['execution_revision'], 'fingerprint': body['fingerprint'],
                        'native_identity': copy.deepcopy(fixture['session_identity']),
                        'native_binding': {'status': 'verified', 'protocol': 'm1-binding-1', 'binding_id': 'bind-' + sid,
                                           'native_session_id': sid, 'config_fingerprint': body['validated_snapshot_id'],
                                           'expires_scope': 'prepared', 'expires_at_backend_monotonic_s': 4000.5,
                                           'verified_at': now, 'readback_sha256': 'd' * 64, 'reason': None},
                        'execution_eligible': True, 'start_available': True,
                        'execution': {'control_scope_granted': [], 'owner': {'state': 'not_acquired', 'session_id': None, 'lease_expires_at_backend_monotonic_s': None},
                                      'recording_required_for_motion': True, 'recording_begin_required': True, 'recording_ready': False,
                                      'motion_ready': False, 'motion_blockers': ['recording_not_ready'], 'observed_at': fixture['observed_at'], 'source': 'prepared'},
                        'blocking_reasons': [], 'start_attempts': [], 'started_at': None, 'start_receipt': None,
                        'recording_begin_attempts': [], 'recording_begin_receipt': None}
            def stored_session(session):
                value = copy.deepcopy(session); value['native_identity'] = copy.deepcopy(fixture['session_identity']); return value
            def live_session(session):
                value = stored_session(session); value['current'] = current_for(session); return value
            def current_for(session):
                mode = fixture['current_mode']
                prepared = session['state'] == 'prepared'
                status = ('prepared' if prepared else 'started') if mode == 'valid' else mode
                matches = mode != 'identity_changed'
                runtime = copy.deepcopy(fixture['session_identity'])
                if mode == 'identity_changed': runtime['episode_id'] = 'fixture-episode-after-reset'
                offline = mode == 'offline'
                eligible = not offline
                binding_state = 'verified' if mode == 'valid' else ('expired' if mode == 'expired' else 'invalidated' if mode == 'identity_changed' else 'unavailable')
                return {'source': 'live_native_read_only', 'observed_at': f'2026-10-24T09:00:{fixture["current_gets"]:02d}+00:00',
                        'valid': mode != 'offline',
                        'status': status, 'error': 'native_offline: synthetic fixture read failure' if offline else None,
                        'runtime_identity': runtime, 'runtime_identity_matches': matches,
                        'binding': {'binding_id': session['native_binding']['binding_id'] if not offline else None,
                                    'state': binding_state, 'matches': matches and not offline,
                                    'readback_sha256': None if offline else 'd' * 64, 'error': 'native_offline' if offline else None},
                        'snapshot_id': session['snapshot_id'], 'snapshot_eligible': eligible,
                        'recipe_fingerprint_matches': not offline,
                        'control_scope_granted': [] if prepared else ['base', 'arm', 'gripper'],
                        'recording_required_for_motion': True, 'recording_begin_required': True,
                        'recording': {'status': 'IDLE' if not offline else 'unknown', 'episode_id': None, 'segment_id': None,
                                      'command_capture_ready': False, 'error': 'native_offline' if offline else None, 'ready': False},
                        'owner': {'state': 'not_acquired', 'session_id': None, 'lease_expires_at_backend_monotonic_s': None, 'lease_exposed': False},
                        'safety_latched': False, 'recording_ready': False, 'motion_ready': False,
                        'start_available': bool(prepared and mode == 'valid'), 'recording_begin_available': False,
                        'blockers': [] if mode == 'valid' else ([{'key': 'native_offline', 'scope': 'native', 'message': 'synthetic fixture: native read failed'}] if offline else
                                 [{'key': 'prepared_binding_expired', 'scope': 'platform', 'message': 'synthetic fixture: prepared TTL expired'}] if mode == 'expired' else
                                 [{'key': 'native_identity_changed', 'scope': 'native', 'message': 'synthetic fixture: episode identity changed'}])}
            def error(route, status, code, message, **extra):
                return route.fulfill(status=status, body=json.dumps({'detail': {'code': code, 'message': message, **extra}}, ensure_ascii=False), headers={'Content-Type': 'application/json'})
            async def json_reply(route, status, value):
                await route.fulfill(status=status, body=json.dumps(value, ensure_ascii=False), headers={'Content-Type': 'application/json', 'Cache-Control': 'no-store'})
            async def handle(route):
                request = route.request; path = urlsplit(request.url).path; method = request.method
                body = json.loads(request.post_data or '{}') if request.post_data else {}
                if method != 'GET': fixture['writes'].append({'method': method, 'path': path, 'body': body})
                if path == '/api/v1/experiment-drafts':
                    if method == 'GET': return await json_reply(route, 200, fixture['drafts'])
                    return await json_reply(route, 201, fixture['drafts'][0])
                if path.startswith('/api/v1/experiment-drafts/'):
                    rest = path[len('/api/v1/experiment-drafts/'):]
                    draft_id = rest.split('/', 1)[0]
                    found = next((d for d in fixture['drafts'] if d['draft_id'] == draft_id), None)
                    if not found: return await error(route, 404, 'draft_not_found', 'synthetic missing draft')
                    if rest.endswith('/validate') and method == 'POST': return await json_reply(route, 200, found)
                    if method == 'GET': return await json_reply(route, 200, found)
                    if method == 'PUT':
                        found.update({'name': body.get('name', found['name']), 'description': body.get('description', found['description']), 'draft_revision': found['draft_revision'] + 1})
                        return await json_reply(route, 200, found)
                if path == '/api/v1/config-snapshots': return await json_reply(route, 200, list(fixture['snapshots'].values()))
                if path.startswith('/api/v1/config-snapshots/'):
                    sid = path.rsplit('/', 1)[-1]
                    return await json_reply(route, 200, fixture['snapshots'][sid]) if sid in fixture['snapshots'] else await error(route, 404, 'snapshot_not_found', 'synthetic missing snapshot')
                if path == '/api/v1/sessions':
                    if method == 'GET':
                        fixture['sessions_gets'] += 1
                        return await json_reply(route, 200, {'source': 'stored', 'live': False,
                                     'retrieved_at': f'2026-10-24T09:01:{fixture["sessions_gets"]:02d}+00:00',
                                     'sessions': [stored_session(s) for s in fixture['sessions'].values()]})
                    fixture['create_calls'].append(body); fixture['create_keys'].append(body.get('idempotency_key'))
                    mode = fixture['create_mode']
                    if mode == 'offline':
                        fixture['create_mode'] = 'normal'; return await error(route, 503, 'native_offline', 'synthetic offline fixture; no native call')
                    existing = next((s for s in fixture['sessions'].values() if s['state'] in ('prepared', 'active')), None)
                    if mode == 'conflict' and existing:
                        fixture['create_mode'] = 'normal'
                        return await error(route, 409, 'session_conflict', 'synthetic existing runtime Session', session_id=existing['session_id'])
                    key = body.get('idempotency_key')
                    if key in fixture['created_by_key']:
                        sid = fixture['created_by_key'][key]; return await json_reply(route, 200, {'session': live_session(fixture['sessions'][sid]), 'replayed': True})
                    if existing and key not in fixture['created_by_key'] and mode != 'delay':
                        return await error(route, 409, 'session_conflict', 'synthetic existing runtime Session', session_id=existing['session_id'])
                    session = new_session(body); fixture['sessions'][session['session_id']] = session; fixture['created_by_key'][key] = session['session_id']
                    if mode == 'delay':
                        fixture['create_mode'] = 'normal'
                        await asyncio.sleep(9.0)
                        try: return await json_reply(route, 201, {'session': live_session(session), 'replayed': False})
                        except Exception: return
                    return await json_reply(route, 201, {'session': live_session(session), 'replayed': False})
                if path.startswith('/api/v1/sessions/'):
                    rest = path[len('/api/v1/sessions/'):]
                    sid = rest.split('/', 1)[0]
                    session = fixture['sessions'].get(sid)
                    if not session: return await error(route, 404, 'session_not_found', 'synthetic missing session')
                    if rest.endswith('/start') and method == 'POST':
                        fixture['start_calls'].append({'session_id': sid, 'mode': fixture['start_mode']})
                        if session['state'] == 'active': return await json_reply(route, 200, live_session(session))
                        if fixture['start_mode'] == 'refuse':
                            attempt = {'at': '2026-10-24T09:00:01+00:00', 'result': 'refused', 'blocking': [{'key': 'native_safety_stop_latched', 'scope': 'native', 'message': 'synthetic fixture refusal'}], 'detail': ''}
                            session['start_attempts'].append(attempt)
                            return await error(route, 409, 'start_preconditions_unmet', 'synthetic Start refusal', blocking_reasons=attempt['blocking'])
                        receipt = {'binding_id': session['native_binding']['binding_id'], 'native_session_id': sid,
                                   'run_id': session['native_identity']['run_id'], 'backend_generation': session['native_identity']['backend_generation'],
                                   'episode_id': session['native_identity']['episode_id'], 'config_fingerprint': session['snapshot_id'],
                                   'started_at_backend_monotonic_s': 42.5, 'control_scope_granted': ['base', 'arm', 'gripper'],
                                   'recording_required_for_motion': True, 'recording_begin_required': True, 'owner_state': 'not_acquired',
                                   'owner_session_id': None, 'lease_expires_at_backend_monotonic_s': None, 'recording_ready': False,
                                   'motion_ready': False, 'motion_blockers': ['recording_not_ready']}
                        session.update({'state': 'active', 'start_available': False, 'started_at': '2026-10-24T09:00:02+00:00', 'start_receipt': receipt,
                                        'start_attempts': session.get('start_attempts', []) + [{'at': '2026-10-24T09:00:02+00:00', 'result': 'started', 'blocking': [], 'detail': ''}],
                                        'execution': {'control_scope_granted': ['base', 'arm', 'gripper'], 'owner': {'state': 'not_acquired', 'session_id': None, 'lease_expires_at_backend_monotonic_s': None},
                                                      'recording_required_for_motion': True, 'recording_begin_required': True, 'recording_ready': False,
                                                      'motion_ready': False, 'motion_blockers': ['recording_not_ready'], 'observed_at': '2026-10-24T09:00:02+00:00', 'source': 'native_start'}})
                        return await json_reply(route, 200, live_session(session))
                    if method == 'GET':
                        fixture['current_gets'] += 1
                        if fixture['current_abort']:
                            fixture['current_abort'] = False; return await route.abort()
                        if fixture['current_delay']:
                            await asyncio.sleep(fixture['current_delay']); fixture['current_delay'] = 0.0
                        return await json_reply(route, 200, live_session(session))
                if path == '/api/v1/mobilecar/preflight':
                    fixture['preflight_count'] += 1; fixture['preflights'] += 1
                    value = {'schema_version': 'mobilecar-integration-1', 'task_id': 'synthetic.fixture',
                             'checked_at': f'2026-10-24T09:00:{fixture["preflight_count"]:02d}+00:00', 'read_only': True,
                             'session_ready': True, 'read_contract_compatible': True,
                             'verification_scope': 'synthetic stateful fixture; not a live native observation', 'transport': 'synthetic_fixture',
                             'runtime_identity': copy.deepcopy(fixture['identity']),
                             'native_resource_identity': {'model_id': caps['data']['model_id'], 'model_sha256': caps['data']['model_sha256'], 'scene_id': caps['data']['scene_id'], 'backend_kind': caps['data']['backend_kind'], 'interface_profile': 'synthetic-fixture'},
                             'recording': {'status': 'IDLE', 'command_capture_ready': False, 'recording_segment_id': None},
                             'checks': [{'key': 'fixture_read_contract', 'status': 'passed', 'detail': 'synthetic fixture only'}, {'key': 'fixture_only', 'status': 'not_checked', 'detail': 'no native evidence'}]}
                    return await json_reply(route, 200, value)
                return await error(route, 404, 'synthetic_unhandled', f'no fixture for {method} {path}')
            for pattern in ('**/api/v1/experiment-drafts**', '**/api/v1/config-snapshots**', '**/api/v1/sessions**', '**/api/v1/mobilecar/preflight'):
                await page.route(pattern, handle)

            await page.goto(a.url + '/?inspect=1', wait_until='domcontentloaded')
            await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0', timeout=90000)
            await page.get_by_role('button', name='Session 准备', exact=True).click()
            await page.wait_for_selector('.session-drawer [data-snapshot-id="cs-fixture-a"]', timeout=20000)
            await page.wait_for_function("()=>{const e=document.querySelector('.session-drawer [data-preflight-checked-at]');return !!(e&&e.getAttribute('data-preflight-checked-at'))}", timeout=20000)
            drawer = page.locator('.session-drawer')
            text = await drawer.inner_text()
            check('synthetic preflight is visibly labelled and current', 'synthetic stateful fixture' in text and await page.locator('[data-preflight-compatible]').get_attribute('data-preflight-compatible') == 'true')
            check('preflight is only a global diagnostic for Start', '只以下方单 Session current 为准' in text or '不是 Session current 的刷新' in text)
            check('list envelope is unpacked and labelled stored/non-live',
                  await page.locator('.session-drawer [data-sessions-source]').get_attribute('data-sessions-source') == 'stored'
                  and await page.locator('.session-drawer [data-sessions-live]').get_attribute('data-sessions-live') == 'false')
            create = page.locator('.session-drawer [data-session-create]')
            check('eligible synthetic snapshot enables explicit create', await create.get_attribute('data-session-create') == 'ready' and await create.is_enabled())

            # Create: first attempt offline, retry must reuse the idempotency key.
            fixture['create_mode'] = 'offline'
            await create.click()
            await page.wait_for_selector('.session-drawer [data-session-error]', timeout=15000)
            check('offline create is shown without a fabricated Session', 'native_offline' in await page.locator('.session-drawer [data-session-error]').inner_text())
            await create.click()
            await page.wait_for_selector('.session-drawer article[data-session-state="prepared"]', timeout=15000)
            check('retry after offline reuses one idempotency key', len(fixture['create_keys']) == 2 and fixture['create_keys'][0] == fixture['create_keys'][1], fixture['create_keys'])
            check('prepare creation never auto-starts', fixture['start_calls'] == [])
            card = page.locator('.session-drawer article[data-session-state="prepared"]')
            await page.wait_for_function("()=>document.querySelector('.session-drawer article[data-session-current-status=\"prepared\"]')!==null", timeout=15000)
            check('prepared current observation drives the card', await card.get_attribute('data-session-current-valid') == 'true'
                  and await card.get_attribute('data-session-current-status') == 'prepared'
                  and await card.get_attribute('data-session-execution-source') == 'live_native_read_only'
                  and bool(await card.get_attribute('data-session-observed-at')))
            check('current is read by a separate single-Session GET', fixture['current_gets'] >= 1 and any('/api/v1/sessions/ps-fixture-a' in r['url'] for r in report['requests']))
            check('prepared session separates owner/recording/motion', await card.get_attribute('data-session-owner') == 'not_acquired'
                  and await card.get_attribute('data-session-recording-ready') == 'false'
                  and await card.get_attribute('data-session-motion-ready') == 'false')
            check('lifecycle comes from current.status, not a browser clock', '前端不按本地时钟计算' in await drawer.inner_text())
            await page.screenshot(path=str(a.output / 'session-prepared.png'), full_page=True)

            # HTTP 200 but current offline: archive start_available must not be reused as ready.
            fixture['current_mode'] = 'offline'
            await page.get_by_role('button', name='刷新 current（只读）', exact=True).click()
            await page.wait_for_function("()=>document.querySelector('.session-drawer article')?.getAttribute('data-session-current-status')==='offline'", timeout=15000)
            check('offline current is displayed with its error and no archive fallback', await card.get_attribute('data-session-current-valid') == 'false'
                  and 'native_offline' in await card.get_attribute('data-session-current-error')
                  and await card.get_attribute('data-session-startable') == 'false'
                  and await page.locator('.session-drawer [data-session-start]').is_disabled()
                  and int(await card.get_attribute('data-session-current-blockers')) >= 1)
            check('offline current still shows archived start_available separately', 'start_available' in await drawer.inner_text())
            await page.screenshot(path=str(a.output / 'session-current-offline.png'), full_page=True)
            fixture['current_mode'] = 'valid'
            await page.get_by_role('button', name='刷新 current（只读）', exact=True).click()
            await page.wait_for_function("()=>document.querySelector('.session-drawer article')?.getAttribute('data-session-current-status')==='prepared'", timeout=15000)
            check('explicit current refresh recovers Start eligibility', await card.get_attribute('data-session-startable') == 'true'
                  and await page.locator('.session-drawer [data-session-start]').is_enabled())

            # Disconnected current read is an error, not a silent archive fallback.
            fixture['current_abort'] = True
            await page.get_by_role('button', name='刷新 current（只读）', exact=True).click()
            await page.wait_for_function("()=>document.querySelector('.session-drawer .session-current')?.getAttribute('data-current-error')!==''", timeout=15000)
            check('a failed current read disables Start and stays visible', await card.get_attribute('data-session-startable') == 'false'
                  and '读取失败' in await drawer.inner_text())
            fixture['current_mode'] = 'valid'
            await page.get_by_role('button', name='刷新 current（只读）', exact=True).click()
            await page.wait_for_function("()=>document.querySelector('.session-drawer article')?.getAttribute('data-session-startable')==='true'", timeout=15000)
            check('current read recovers after an explicit retry', await page.locator('.session-drawer .session-current').get_attribute('data-current-error') == '')

            # Explicit Start: refusal first, then success.
            fixture['start_mode'] = 'refuse'
            await page.locator('.session-drawer [data-session-start]').click()
            await page.wait_for_selector('.session-drawer [data-session-error]', timeout=15000)
            await page.wait_for_function("()=>document.querySelectorAll('.session-drawer [data-start-attempt=\"refused\"]').length>0", timeout=15000)
            check('Start refusal is explicit and leaves the Session prepared', 'start_preconditions_unmet' in await page.locator('.session-drawer [data-session-error]').inner_text()
                  and await page.locator('.session-drawer article[data-session-state="prepared"]').count() == 1)
            fixture['start_mode'] = 'success'
            await page.locator('.session-drawer [data-session-start]').click()
            await page.wait_for_selector('.session-drawer article[data-session-state="active"]', timeout=15000)
            await page.wait_for_function("()=>document.querySelector('.session-drawer article')?.getAttribute('data-session-current-status')==='started'", timeout=15000)
            active = page.locator('.session-drawer article[data-session-state="active"]')
            check('explicit Start produces active only after the click', fixture['start_calls'][-1]['mode'] == 'success' and await active.get_attribute('data-session-id') == 'ps-fixture-a')
            check('active keeps owner/recording/motion separate and is not startable', await active.get_attribute('data-session-owner') == 'not_acquired'
                  and await active.get_attribute('data-session-recording-ready') == 'false'
                  and await active.get_attribute('data-session-motion-ready') == 'false'
                  and await active.get_attribute('data-session-startable') == 'false'
                  and await active.get_attribute('data-session-current-status') == 'started')
            check('started lifecycle is read from current, not a prepared TTL', await active.get_attribute('data-session-current-valid') == 'true')
            check('historical receipts stay in a separate archive section', await drawer.locator('.session-current').count() == 1
                  and await drawer.locator('summary', has_text='历史 / 存档字段').count() == 1)
            check('top Start remains disabled', await page.get_by_role('button', name='Start', exact=True).is_disabled())
            await page.screenshot(path=str(a.output / 'session-active.png'), full_page=True)

            # Second draft: conflict, delayed create + archive recovery, freshness.
            await page.get_by_label('选择草案', exact=True).select_option('draft-fixture-b')
            await page.wait_for_selector('.session-drawer [data-draft-id="draft-fixture-b"]', timeout=15000)
            await page.wait_for_selector('.session-drawer [data-snapshot-id="cs-fixture-b"]', timeout=15000)
            fixture['create_mode'] = 'conflict'
            await create.click()
            await page.wait_for_function("()=>document.querySelector('.session-drawer .session-notice')?.textContent?.includes('已有 Session')", timeout=15000)
            check('409 existing Session is read back instead of hidden', 'session_conflict' in await page.locator('.session-drawer [data-session-error]').inner_text())
            fixture['create_mode'] = 'delay'
            await create.click()
            await page.wait_for_selector('.session-drawer article[data-session-id="ps-fixture-b"][data-session-state="prepared"]', timeout=20000)
            timeout_text = await drawer.inner_text()
            check('timeout is recovered by reading the Session archive, not reported as a false success', ('超时' in timeout_text or '回读' in timeout_text)
                  and await page.locator('.session-drawer [data-session-unknown]').count() == 0
                  and len(fixture['create_keys']) >= 4 and fixture['create_keys'][2] == fixture['create_keys'][3], fixture['create_keys'])
            check('recovered prepared Session did not auto-start', fixture['start_calls'][-1]['session_id'] == 'ps-fixture-a')
            await page.screenshot(path=str(a.output / 'session-recovered.png'), full_page=True)

            observed = await page.locator('.session-drawer article[data-session-id="ps-fixture-b"]').get_attribute('data-session-observed-at')
            sessions_before = fixture['sessions_gets']; preflights_before = fixture['preflights']; currents_before = fixture['current_gets']
            await page.get_by_role('button', name='刷新存档（不调用 native）', exact=True).click()
            await page.wait_for_timeout(700)
            check('archive refresh reads the envelope without touching native or current',
                  await page.locator('.session-drawer article[data-session-id="ps-fixture-b"]').get_attribute('data-session-observed-at') == observed
                  and fixture['preflights'] == preflights_before and fixture['current_gets'] == currents_before
                  and fixture['sessions_gets'] == sessions_before + 1)
            checked_before = await page.locator('.session-drawer [data-preflight-checked-at]').get_attribute('data-preflight-checked-at')
            await page.get_by_role('button', name='刷新 native 观测（只读）', exact=True).click()
            await page.wait_for_function("(old)=>document.querySelector('.session-drawer [data-preflight-checked-at]')?.getAttribute('data-preflight-checked-at')!==old", arg=checked_before, timeout=10000)
            check('preflight refresh updates checked_at without changing Session current',
                  await page.locator('.session-drawer article[data-session-id="ps-fixture-b"]').get_attribute('data-session-observed-at') == observed
                  and fixture['preflights'] == preflights_before + 1 and fixture['current_gets'] == currents_before)

            # Late current for a switched Session must not overwrite the new selection.
            fixture['current_delay'] = 3.0
            await page.get_by_role('button', name='刷新 current（只读）', exact=True).click()
            await page.wait_for_timeout(300)
            await page.get_by_label('选择 Session', exact=True).select_option('ps-fixture-a')
            await page.wait_for_function("()=>document.querySelector('.session-drawer article[data-session-id=\"ps-fixture-a\"]')!==null", timeout=15000)
            await page.wait_for_timeout(4200)
            current_id = await page.locator('.session-drawer article').get_attribute('data-session-id')
            check('a late current response cannot overwrite the switched Session', current_id == 'ps-fixture-a', current_id)

            # Local target must be cancelled when the current identity is invalidated.
            await page.get_by_role('button', name='关闭 Session 准备', exact=True).click()
            await page.locator('[data-object="link2"]').click()
            await page.get_by_role('button', name='Joint', exact=True).first.click()
            field = page.get_by_role('spinbutton', name='joint2 Target deg', exact=True)
            await field.fill('10'); await field.press('Tab')
            await page.wait_for_function('window.__workbenchInspect().target!==null', timeout=15000)
            before = await page.evaluate('window.__workbenchInspect()')
            fixture['current_mode'] = 'identity_changed'
            await page.get_by_role('button', name='Session 准备', exact=True).click()
            await page.wait_for_function("()=>document.querySelector('.session-drawer [data-session-count]')!==null", timeout=15000)
            await page.get_by_label('选择 Session', exact=True).select_option('ps-fixture-a')
            await page.wait_for_selector('.session-drawer article[data-session-id="ps-fixture-a"][data-session-invalidated="true"]', timeout=15000)
            await page.wait_for_function('window.__workbenchInspect().target===null', timeout=5000)
            after = await page.evaluate('window.__workbenchInspect()')
            check('current identity change disables Start and reports invalidation', await page.locator('.session-drawer article').get_attribute('data-session-startable') == 'false'
                  and await page.locator('.session-drawer [data-session-start]').is_disabled()
                  and await page.locator('.session-drawer article').get_attribute('data-session-current-status') == 'identity_changed')
            check('invalidation cancels the local target but keeps renderer, camera and layout', after['target'] is None and after['scene']['instanceId'] == before['scene']['instanceId'] and after['scene']['camera'] == before['scene']['camera'])
            check('invalidation does not auto-resend Start', fixture['start_calls'][-1]['session_id'] == 'ps-fixture-a')
            await page.screenshot(path=str(a.output / 'session-invalidated.png'), full_page=True)

            # Prepared binding expiry is reported by current, never inferred from the browser clock.
            fixture['current_mode'] = 'expired'
            await page.get_by_role('button', name='刷新 current（只读）', exact=True).click()
            await page.wait_for_function("()=>document.querySelector('.session-drawer article')?.getAttribute('data-session-current-status')==='expired'", timeout=15000)
            check('expired prepared binding disables Start without a clock guess', await page.locator('.session-drawer article').get_attribute('data-session-startable') == 'false'
                  and await page.locator('.session-drawer article').get_attribute('data-session-invalidated') == 'true')

            # Network boundary: fixture sessions are synthetic; live mobilecar remains GET-only.
            mobilecar = [r for r in report['requests'] if '/api/v1/mobilecar/' in r['url'] and '/preflight' not in r['url']]
            native_paths = [r for r in report['requests'] if any(token in r['url'] for token in ('/api/v1/session/', '/api/v1/recording/', '/api/v1/commands', '/api/v1/episodes', '/api/v1/reset'))]
            check('all live mobilecar requests remain GET', all(r['method'] == 'GET' for r in mobilecar))
            check('no native session/commands/recording/RESET path was requested', not native_paths, native_paths[:3])
            check('fixture writes are only Session create/start', all(w['path'] == '/api/v1/sessions' or w['path'].endswith('/start') for w in fixture['writes']), fixture['writes'][:5])
            check('no production mock switch was used', not any('mock=' in r['url'] for r in report['requests']))
            check('no map/route request was invented', not any(token in request['url'] for request in report['requests'] for token in ('/map', '/route', '/waypoint')), [r['url'] for r in report['requests'] if 'map' in r['url'] or 'route' in r['url']][:3])
            check('no uncaught browser errors', not report['errors'], report['errors'][:3])
            report['fixture_state'] = {'identity': identity, 'session_identity_after': fixture['session_identity'], 'create_keys': fixture['create_keys'],
                                       'create_calls': len(fixture['create_calls']), 'start_calls': fixture['start_calls'],
                                       'sessions_gets': fixture['sessions_gets'], 'current_gets': fixture['current_gets'],
                                       'preflights': fixture['preflights'], 'stored_sessions': list(fixture['sessions'])}
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
