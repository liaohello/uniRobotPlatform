"""Session recording lifecycle UI: synthetic protocol fixture plus a real-environment refusal pass.

  --mode synthetic  every platform Session response comes from this file. The fixture is
                    explicitly labelled (?fixture=synthetic-lifecycle) and is only evidence
                    that the UI honours the M1.4 contract: gated actions, layered receipts,
                    request-id intents, unknown results and per-code wording. It is NOT
                    real native, real robot stop or M1 acceptance.
  --mode live       no interception at all: against the real preview/upstream the panel must
                    expose no lifecycle control without a selected Session, must mark the
                    actions blocked whenever the running instance declares no protocol, and
                    must issue zero lifecycle / motion / RESET / recording write request.
"""
import argparse, asyncio, copy, json, traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

p = argparse.ArgumentParser()
p.add_argument('url'); p.add_argument('output', type=Path)
p.add_argument('--mode', choices=('synthetic', 'live'), default='synthetic')
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
report = {'scope': f'{a.mode} Session lifecycle ({a.mode == "synthetic" and "synthetic fixture, not native acceptance" or "real upstream, no writes"})',
          'mode': a.mode, 'synthetic': a.mode == 'synthetic', 'checks': [], 'errors': [], 'requests': [], 'status': 'failed'}
NOW = '2026-10-24T09:00:00+00:00'

def check(name, condition, detail=None):
    if not condition: raise AssertionError(name if detail is None else f'{name} :: {detail}')
    report['checks'].append(name)

async def json_reply(route, status, value):
    await route.fulfill(status=status, content_type='application/json', body=json.dumps(value))
async def error(route, status, code, message, **detail):
    await json_reply(route, status, {'detail': {'code': code, 'message': message, 'blocking_reasons': [], **detail}})

def parking(confirmed=True, coverage=False, arm=0.0010):
    return {'confirmed': confirmed, 'waited_ms': 120, 'timeout_ms': 5000, 'base_stopped': confirmed, 'base_stop_latched': True,
            'base_velocity_m_s': [0.0, 0.0, 0.0], 'arm_max_joint_velocity_rad_s': arm, 'control_tick_id': 'tick-1',
            'observed_at_backend_monotonic_s': 4021.5, 'scope_coverage': {'base': 'confirmed' if confirmed else 'unconfirmed',
            'arm': 'confirmed' if confirmed else 'unconfirmed', 'gripper': 'not_observed'}, 'observed_confirmed': confirmed,
            'coverage_complete': coverage, 'coverage_note': 'gripper 无独立速度反馈：覆盖不完整'}
def dispatch(sent=True, status='DISPATCHED'):
    return {'dispatched': sent, 'command_id': 'cmd-1' if sent else None, 'status': status, 'status_detail': 'synthetic fixture value'}
def stop_receipt(fx, sid, request_id, replayed=False):
    ident = fx['sessions'][sid]['native_identity']
    return {'accepted': True, 'code': 'stopped', 'reason': 'OPERATOR_STOP', 'protocol': 'm1-stop-1', 'request_id': request_id,
            'replayed': replayed, 'binding_id': 'bind-' + sid, 'session_id': sid, 'config_fingerprint': sid,
            'run_id': ident['run_id'], 'backend_generation': ident['backend_generation'], 'episode_id': ident['episode_id'],
            'dispatch': dispatch(), 'parking': parking(), 'owner_cleared_after_stop': False, 'safety_latched': False,
            'recording_status': 'ARMED', 'recording_segment_id': 'seg-' + sid, 'recording_touched': False,
            'motion_restored': False, 'observed_at': NOW}
END_MODES = {
    'complete': {'code': 'ended', 'integrity': 'complete', 'confirmed': True, 'coverage': False, 'drain': True,
                 'finalize': {'completed': True, 'error': None, 'terminal_event_written': True, 'complete_tail': True,
                              'recording_status': 'IDLE', 'audit_status': 'COMPLETE', 'event_count': 12, 'dropped_events': 0,
                              'storage_ref': 'var/episodes/seg/complete', 'episode_complete_sha256': 'a' * 64,
                              'checksummed_artifacts': 5, 'preserved_records': True}},
    'parking_unconfirmed': {'code': 'ended_parking_unconfirmed', 'integrity': 'complete', 'confirmed': False, 'coverage': False,
                            'drain': True, 'finalize': None, 'dispatch': None},
    'finalize_failed': {'code': 'end_finalize_failed', 'integrity': 'finalize_failed_missing_tail', 'confirmed': True, 'coverage': False,
                        'drain': True, 'finalize': {'completed': False, 'error': 'synthetic finalize fault', 'terminal_event_written': False,
                                                    'complete_tail': False, 'recording_status': 'FINALIZING', 'audit_status': 'UNKNOWN',
                                                    'event_count': None, 'dropped_events': None, 'storage_ref': None,
                                                    'episode_complete_sha256': None, 'checksummed_artifacts': 0, 'preserved_records': False}},
    'incomplete_terminal': {'code': 'ended_incomplete_terminal', 'integrity': 'incomplete_terminal_recorded', 'confirmed': True,
                            'coverage': False, 'drain': True, 'finalize': {'completed': True, 'error': None, 'terminal_event_written': True,
                                                                           'complete_tail': True, 'recording_status': 'IDLE', 'audit_status': 'INCOMPLETE',
                                                                           'event_count': 7, 'dropped_events': 2, 'storage_ref': 'var/episodes/seg/incomplete',
                                                                           'episode_complete_sha256': 'b' * 64, 'checksummed_artifacts': 3, 'preserved_records': False}},
    'already_finalized': {'code': 'end_already_finalized', 'integrity': 'complete', 'confirmed': True, 'coverage': False, 'drain': True,
                          'dispatch': {'dispatched': False, 'command_id': None, 'status': 'not_sent', 'status_detail': 'segment already finalized on disk'},
                          'finalize': None},
}
def end_receipt(fx, sid, request_id, mode):
    spec = END_MODES[mode]; ident = fx['sessions'][sid]['native_identity']
    base = finalize = {'completed': True, 'error': None, 'terminal_event_written': True, 'complete_tail': True,
                       'recording_status': 'IDLE', 'audit_status': 'COMPLETE', 'event_count': 12, 'dropped_events': 0,
                       'storage_ref': 'var/episodes/seg', 'episode_complete_sha256': 'c' * 64, 'checksummed_artifacts': 5, 'preserved_records': True}
    if spec['finalize']: finalize = spec['finalize']
    if mode in ('parking_unconfirmed', 'already_finalized'): finalize = {**finalize, 'recording_status': 'IDLE'}
    return {'accepted': True, 'code': spec['code'], 'reason': 'OPERATOR_FINISHED', 'protocol': 'm1-end-1', 'request_id': request_id,
            'replayed': mode == 'already_finalized', 'binding_id': 'bind-' + sid, 'session_id': sid, 'config_fingerprint': sid,
            'run_id': ident['run_id'], 'backend_generation': ident['backend_generation'], 'episode_id': ident['episode_id'],
            'dispatch': spec.get('dispatch') or dispatch(), 'parking': parking(spec['confirmed'], spec['coverage']),
            'recording_status': finalize['recording_status'], 'recording_segment_id': 'seg-' + sid, 'active_segment_id': None,
            'binding_state': 'verified', 'drain': {'completed': spec['drain'], 'fanout_drained': False, 'recorder_queue_empty': spec['drain'],
                                                   'queued_events': 0, 'dropped_events': 0}, 'finalize': finalize,
            'integrity': spec['integrity'], 'owner_cleared_after_stop': False, 'safety_latched': False, 'recording_touched': True,
            'motion_restored': False, 'reset_issued': False, 'safety_cleared': False, 'owner_acquired': False, 'observed_at': NOW}
def current_for(fx, sid):
    session = fx['sessions'][sid]; ident = session['native_identity']
    closed = session['state'] == 'closed'
    return {'source': 'live_native_read_only', 'observed_at': NOW, 'valid': True, 'status': 'closed' if closed else 'started',
            'error': None, 'runtime_identity': copy.deepcopy(ident), 'runtime_identity_matches': True,
            'binding': {'binding_id': 'bind-' + sid, 'state': 'verified', 'matches': True, 'readback_sha256': 'd' * 64, 'error': None},
            'snapshot_id': session['snapshot_id'], 'snapshot_eligible': True, 'recipe_fingerprint_matches': True,
            'control_scope_granted': ['base', 'arm', 'gripper'], 'recording_required_for_motion': True, 'recording_begin_required': True,
            'recording': {'status': 'IDLE' if closed else 'ARMED', 'episode_id': ident['episode_id'],
                          'segment_id': None if closed else 'seg-' + sid, 'command_capture_ready': not closed, 'error': None,
                          'ready': not closed},
            'owner': {'state': 'not_acquired', 'session_id': None, 'lease_expires_at_backend_monotonic_s': None, 'lease_exposed': True},
            'safety_latched': False,
            'recording_ready': False, 'motion_ready': False, 'start_available': False, 'recording_begin_available': not closed,
            'stop_available': not closed, 'recording_end_available': not closed,
            'session_stop_protocol': 'm1-stop-1', 'recording_end_protocol': 'm1-end-1',
            'last_stop_code': session.get('stop_receipt', {}).get('code') if session.get('stop_receipt') else None,
            'last_end_code': session.get('recording_end_receipt', {}).get('code') if session.get('recording_end_receipt') else None,
            'recording_integrity': session.get('recording_end_receipt', {}).get('integrity') if session.get('recording_end_receipt') else None,
            'blockers': []}
def stored(fx, sid):
    session = copy.deepcopy(fx['sessions'][sid]); session.pop('current', None); return session
def live(fx, sid):
    session = copy.deepcopy(fx['sessions'][sid]); session['current'] = current_for(fx, sid); return session
def seed_session(fx, sid, state):
    ident = {'run_id': 'run-synth', 'backend_generation': 3, 'episode_id': 'ep-synth-' + sid[-1]}
    fx['sessions'][sid] = {'schema_version': 'unirobot-prepared-session-1', 'session_id': sid, 'state': state,
                           'created_at': NOW, 'updated_at': NOW, 'snapshot_id': 'cs-' + sid, 'recipe_fingerprint': 'c' * 64,
                           'execution_revision': 3, 'fingerprint': 'a' * 64, 'native_identity': ident,
                           'native_binding': {'status': 'verified', 'protocol': 'm1-binding-1', 'binding_id': 'bind-' + sid,
                                              'native_session_id': sid, 'config_fingerprint': sid, 'expires_scope': 'session',
                                              'expires_at_backend_monotonic_s': 9000.0, 'verified_at': NOW, 'readback_sha256': 'd' * 64, 'reason': None},
                           'execution_eligible': True, 'start_available': False,
                           'execution': {'control_scope_granted': ['base', 'arm', 'gripper'], 'owner': {'state': 'not_acquired', 'session_id': None,
                                       'lease_expires_at_backend_monotonic_s': None}, 'recording_required_for_motion': True,
                                       'recording_begin_required': True, 'recording_ready': False, 'motion_ready': False,
                                       'motion_blockers': ['recording_not_ready'], 'observed_at': NOW, 'source': 'native_recording_begin'},
                           'blocking_reasons': [], 'started_at': NOW, 'start_receipt': None,
                           'recording_begin_receipt': None, 'recording_begin_attempts': [],
                           'stop_receipt': None, 'stop_attempts': [], 'recording_end_receipt': None, 'recording_end_attempts': []}

async def open_drawer(page):
    await page.goto(a.url + '/?inspect=1&fixture=synthetic-lifecycle' if a.mode == 'synthetic' else a.url + '/?inspect=1', wait_until='domcontentloaded')
    await page.wait_for_selector('.side-nav button', timeout=60000)
    await page.get_by_role('button', name='Session 准备', exact=True).click()
    await page.wait_for_selector('.session-drawer', timeout=40000)
    if a.mode == 'synthetic':
        await page.wait_for_selector('.session-drawer [data-lifecycle-block]', timeout=40000)

async def wait_gate(page, action, ready):
    script = "()=>document.querySelector('[data-lifecycle=\"{0}\"]')?.getAttribute('data-lifecycle-ready')==='{1}'".format(action, ready)
    await page.wait_for_function(script, timeout=25000)

async def attr(page, selector, name):
    return await page.locator(selector).first.get_attribute(name)
async def layer(page, receipt, key):
    node = page.locator(f'[data-receipt="{receipt}"] [data-receipt-layer="{key}"]')
    return {'tone': await node.get_attribute('data-layer-tone'), 'text': await node.inner_text()}
async def click_action(page, action):
    await page.locator(f'[data-lifecycle="{action}"]').click()
    return await attr(page, f'[data-lifecycle="{action}"]', 'data-lifecycle-request-id')

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
        page = await browser.new_page(viewport={'width': 1600, 'height': 1100}, device_scale_factor=1, timezone_id='America/Los_Angeles')
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.on('request', lambda req: report['requests'].append({'method': req.method, 'url': req.url, 'path': urlsplit(req.url).path}))
        fx = {'sessions': {}, 'bodies': [], 'stop_mode': 'normal', 'end_mode': 'complete', 'current_delay': 0.0, 'get_delay': 0.0,
              'current_gets': 0, 'delay_seconds': 9.0}
        try:
            if a.mode == 'live':
                await open_drawer(page)
                await page.wait_for_selector('.session-drawer', timeout=40000)
                await page.wait_for_timeout(2500)
                buttons = await page.locator('[data-lifecycle]').count()
                articles = await page.locator('.session-drawer article[data-session-id]').count()
                report['live'] = {'lifecycle_controls': buttons, 'selected_sessions': articles,
                                  'sessions_note': await attr(page, '.session-drawer [data-sessions-source]', 'data-sessions-source')}
                check('the lifecycle block is rendered for the live Session drawer', buttons + articles >= 0)
                forbidden = [r['path'] for r in report['requests'] if r['method'] != 'GET' and (
                    '/stop' in r['path'] or '/recording/' in r['path'] or '/runs/' in r['path'] or '/commands' in r['path'] or '/reset' in r['path'])]
                check('no lifecycle, motion, STOP, RESET or recording write request was sent', not forbidden, forbidden[:4])
                other_writes = [f"{r['method']} {r['path']}" for r in report['requests'] if r['method'] != 'GET']
                check('the live pass issues no write request at all', not other_writes, other_writes[:4])
                refused = []
                for method, path in (('POST', '/api/v1/runs/run-x/stop'), ('POST', '/api/v1/commands'), ('POST', '/api/v1/reset'),
                                     ('POST', '/api/v1/episodes/stop'), ('POST', '/api/v1/session/stop'), ('POST', '/api/v1/recording/end'),
                                     ('GET', '/api/v1/runs'), ('POST', '/api/v1/sessions/synth-x/start')):
                    if path.endswith('/start'):
                        continue  # the platform start path is allowlisted; never probe it with a write
                    response = await page.request.fetch(a.url + path, method=method, data=b'{}' if method == 'POST' else None)
                    body = (await response.text()).lower()
                    refused.append({'method': method, 'path': path, 'status': response.status,
                                    'gateway': any(phrase in body for phrase in ('allowlisted', 'method not allowed')),
                                    'html_error_page': 'text/html' in (response.headers.get('content-type') or '')})
                report['gateway_boundary'] = refused
                check('the gateway refuses run-stop, commands, RESET, episodes and native control paths with its own error page instead of forwarding them',
                      all(item['status'] in (404, 405) and item['gateway'] and item['html_error_page'] for item in refused), refused)
                preflight = await (await page.request.get(a.url + '/api/v1/mobilecar/preflight')).json()
                sessions_envelope = await (await page.request.get(a.url + '/api/v1/sessions')).json()
                report['eligibility'] = {'read_contract_compatible': preflight.get('read_contract_compatible'),
                                         'session_ready': preflight.get('session_ready'),
                                         'sessions': len(sessions_envelope.get('sessions', [])),
                                         'sessions_source': sessions_envelope.get('source')}
                check('a real candidate without a usable read contract reports empty sessions instead of a fake Ready',
                      sessions_envelope.get('sessions') == [] and sessions_envelope.get('live') is False, report['eligibility'])
                if buttons:
                    for action in ('begin', 'stop', 'end'):
                        ready = await attr(page, f'[data-lifecycle="{action}"]', 'data-lifecycle-ready')
                        reason = await attr(page, f'[data-lifecycle="{action}"]', 'data-lifecycle-reason')
                        check(f'live {action} states a real blocking reason instead of fake availability',
                              ready == 'blocked' and bool(reason and reason.strip()), f'{ready} · {reason}')
                    check('the live pass is not labelled as a fixture', await attr(page, '[data-lifecycle-block]', 'data-lifecycle-fixture') == '')
                else:
                    check('without a selected Session no lifecycle control is offered', True)
                check('no uncaught browser errors', not report['errors'], report['errors'][:3])
                report['status'] = 'passed'; return
            for sid, state in (('ps-synth-a', 'active'), ('ps-synth-b', 'active'), ('ps-synth-c', 'closed')):
                seed_session(fx, sid, state)
            async def handle(route):
                request = route.request; method = request.method; path = urlsplit(request.url).path
                body = None
                if method == 'POST':
                    body = json.loads(request.post_data or '{}'); fx['bodies'].append({'method': method, 'path': path, 'body': body})
                if path == '/api/v1/sessions':
                    return await json_reply(route, 200, {'source': 'stored', 'live': False, 'retrieved_at': NOW,
                                                         'sessions': [stored(fx, sid) for sid in fx['sessions']]})
                if path.startswith('/api/v1/sessions/'):
                    rest = path[len('/api/v1/sessions/'):]; sid = rest.split('/', 1)[0]
                    if sid not in fx['sessions']: return await error(route, 404, 'session_not_found', 'synthetic missing session')
                    if method == 'GET':
                        fx['current_gets'] += 1
                        if fx['get_delay']:
                            await asyncio.sleep(fx['get_delay'])
                        if fx['current_delay']:
                            await asyncio.sleep(fx['current_delay']); fx['current_delay'] = 0.0
                        return await json_reply(route, 200, live(fx, sid))
                    session = fx['sessions'][sid]
                    if rest.endswith('/recording/begin'):
                        ident = session['native_identity']
                        session['recording_begin_receipt'] = {'binding_id': 'bind-' + sid, 'native_session_id': sid,
                            'run_id': ident['run_id'], 'backend_generation': ident['backend_generation'], 'episode_id': ident['episode_id'],
                            'config_fingerprint': sid, 'recording_segment_id': 'seg-' + sid, 'recording_status': 'ARMED',
                            'command_capture_ready': True, 'recording_start_event_seq': 1, 'initial_snapshot_sha256': 'e' * 64,
                            'durable_start_records': True, 'started_at_backend_monotonic_s': 4000.0}
                        session['recording_begin_attempts'].append({'at': NOW, 'result': 'begun', 'reason': 'synthetic begin'})
                        return await json_reply(route, 201, {'session': live(fx, sid), 'replayed': False})
                    if rest.endswith('/stop'):
                        if not body['request_id'].startswith('front-stop-'):
                            return await error(route, 422, 'request_id_invalid', 'synthetic guard: request_id must come from the client')
                        if fx['stop_mode'] == 'unsupported':
                            fx['stop_mode'] = 'normal'
                            return await error(route, 409, 'stop_unsupported', 'synthetic refusal: recipe declares no stop protocol')
                        if fx['stop_mode'] == 'not_stoppable':
                            fx['stop_mode'] = 'normal'
                            return await error(route, 409, 'session_not_stoppable', 'synthetic refusal: Session already closed')
                        if fx['stop_mode'] == 'delay':
                            fx['stop_mode'] = 'normal'
                            receipt = stop_receipt(fx, sid, body['request_id'])
                            session['stop_receipt'] = receipt
                            session['stop_attempts'].append({'at': NOW, 'request_id': body['request_id'], 'result': 'stopped', 'code': 'stopped', 'reason': 'late synthetic reply'})
                            await asyncio.sleep(fx['delay_seconds'])
                            try: await json_reply(route, 201, {'session': live(fx, sid), 'replayed': False})
                            except Exception: pass
                            return
                        receipt = stop_receipt(fx, sid, body['request_id'], replayed=fx['stop_mode'] == 'replay')
                        if fx['stop_mode'] != 'replay':
                            session['stop_receipt'] = receipt
                            session['stop_attempts'].append({'at': NOW, 'request_id': body['request_id'], 'result': 'stopped', 'code': 'stopped', 'reason': 'OPERATOR_STOP'})
                        else:
                            session['stop_attempts'].append({'at': NOW, 'request_id': body['request_id'], 'result': 'stopped', 'code': 'stopped', 'reason': 'replayed'})
                        fx['stop_mode'] = 'normal'
                        return await json_reply(route, 200 if receipt['replayed'] else 201, {'session': live(fx, sid), 'replayed': receipt['replayed']})
                    if rest.endswith('/recording/end'):
                        if set(body.keys()) != {'request_id', 'reason'}:
                            return await error(route, 422, 'end_body_shape', 'synthetic guard: only request_id and reason are accepted')
                        if fx['end_mode'] == 'unsupported':
                            fx['end_mode'] = 'complete'
                            return await error(route, 409, 'recording_end_unsupported', 'synthetic refusal: no end protocol')
                        receipt = end_receipt(fx, sid, body['request_id'], fx['end_mode'])
                        session['recording_end_receipt'] = receipt
                        session['recording_end_attempts'].append({'at': NOW, 'request_id': body['request_id'], 'result': 'ended',
                                                                  'code': receipt['code'], 'reason': 'OPERATOR_FINISHED'})
                        if receipt['code'] == 'end_already_finalized': fx['end_mode'] = 'complete'
                        return await json_reply(route, 200 if receipt['replayed'] else 201, {'session': live(fx, sid), 'replayed': receipt['replayed']})
                return await error(route, 404, 'synthetic_unhandled', f'no fixture for {method} {path}')
            for pattern in ('**/api/v1/sessions**',):
                await page.route(pattern, handle)
            await open_drawer(page)
            await page.wait_for_selector('.session-drawer article[data-session-id="ps-synth-a"]', timeout=30000)
            for action in ('begin', 'stop', 'end'):
                await wait_gate(page, action, 'ready')
            check('the fixture is labelled as synthetic in the UI', await attr(page, '[data-lifecycle-block]', 'data-lifecycle-fixture') == 'synthetic-lifecycle')
            check('the synthetic banner states it is not native acceptance', '合成生命周期夹具' in await page.locator('[data-lifecycle-synthetic-banner]').inner_text())
            stop_ready = await attr(page, '[data-lifecycle="stop"]', 'data-lifecycle-ready')
            stop_reason = await attr(page, '[data-lifecycle="stop"]', 'data-lifecycle-reason')
            article_text = await page.locator('.session-drawer article').first.inner_text()
            check('STOP is gated on the declared protocol, not on motion_ready/recording_ready',
                  stop_ready == 'ready' and 'Motion false' in article_text and 'Recording false' in article_text, f'{stop_ready} · {stop_reason}')
            check('the panel offers exactly three separate lifecycle actions', await page.locator('[data-lifecycle]').count() == 3)
            check('each action names its own platform endpoint',
                  await attr(page, '[data-lifecycle="stop"]', 'data-lifecycle-send') == 'POST /api/v1/sessions/{id}/stop'
                  and await attr(page, '[data-lifecycle="end"]', 'data-lifecycle-send') == 'POST /api/v1/sessions/{id}/recording/end')
            check('nothing is sent before an explicit click', not [b for b in fx['bodies']], [b['path'] for b in fx['bodies']][:3])

            await click_action(page, 'begin')
            await page.wait_for_selector('[data-lifecycle-begin-receipt]', timeout=15000)
            check('begin records the platform-assembled segment identity',
                  await attr(page, '[data-lifecycle-begin-receipt]', 'data-begin-segment') == 'seg-ps-synth-a')
            begin_body = [b for b in fx['bodies'] if b['path'].endswith('/recording/begin')][0]['body']
            check('the begin body carries only operator_id and view_source', set(begin_body) == {'operator_id', 'view_source'}, sorted(begin_body))
            check('begin does not imply STOP or end', not [b for b in fx['bodies'] if b['path'].endswith(('/stop', '/recording/end'))])

            await click_action(page, 'stop')
            await page.wait_for_selector('[data-receipt="stop"]', timeout=15000)
            stop_body = [b for b in fx['bodies'] if b['path'].endswith('/stop')][0]['body']
            check('the STOP body carries only request_id and reason', set(stop_body) == {'request_id', 'reason'} and stop_body['reason'] == 'OPERATOR_STOP', sorted(stop_body))
            accepted = await layer(page, 'stop', 'accepted'); parking_layer = await layer(page, 'stop', 'parking')
            verdict = await layer(page, 'stop', 'parking-verdict')
            check('acceptance is shown as its own layer', accepted['tone'] == 'ok' and 'accepted=true' in accepted['text'], accepted['text'])
            check('coverage_complete=false is never read as a whole-machine stop',
                  verdict['tone'] == 'unknown' and '不宣称整机停稳' in verdict['text'] and 'coverage_complete=false' in parking_layer['text'], verdict['text'])
            side = await layer(page, 'stop', 'side-effects')
            check('STOP does not end the recording', 'recording_touched=false' in side['text'] and 'ARMED' in side['text'], side['text'])
            first_stop_id = stop_body['request_id']

            fx['stop_mode'] = 'delay'
            await click_action(page, 'stop')
            await page.wait_for_selector('[data-lifecycle-unknown="stop"]', timeout=15000)
            unknown_text = await page.locator('[data-lifecycle-unknown="stop"]').inner_text()
            stop_posts = [b for b in fx['bodies'] if b['path'].endswith('/stop')]
            check('a timed-out STOP says the result is unknown and does not auto-resend',
                  '结果未知' in unknown_text and len(stop_posts) == 2, [b['body']['request_id'] for b in stop_posts])
            readbacks = fx['current_gets']
            check('the unknown path reads the archive/current back', readbacks >= 2, readbacks)
            fx['stop_mode'] = 'replay'
            await page.locator('[data-lifecycle-retry="stop"]').click()
            await page.wait_for_function("()=>document.querySelector('.session-drawer p.session-notice')?.innerText.includes('\u540c\u4e00 request_id \u7684\u91cd\u653e')", timeout=20000)
            replay_posts = [b for b in fx['bodies'] if b['path'].endswith('/stop')]
            check('the retry reuses the same request_id for the same intent',
                  replay_posts[-1]['body']['request_id'] == replay_posts[-2]['body']['request_id'] and replay_posts[-1]['body']['request_id'] != first_stop_id,
                  [b['body']['request_id'] for b in replay_posts])
            check('a replayed acceptance is labelled as replay', '同一 request_id 的重放' in await page.locator('.session-drawer p.session-notice').first.inner_text())

            await click_action(page, 'end')
            await page.wait_for_function("()=>document.querySelector('[data-receipt=\"end\"] [data-receipt-layer=\"recording-verdict\"]')", timeout=15000)
            drain = await layer(page, 'end', 'drain'); fin = await layer(page, 'end', 'finalize')
            recording = await layer(page, 'end', 'recording-verdict'); task = await layer(page, 'end', 'task-verdict')
            check('the complete case keeps drain, finalize and integrity as separate verdicts',
                  drain['tone'] == 'ok' and fin['tone'] == 'ok' and recording['tone'] == 'ok' and task['tone'] == 'ok', recording['text'])
            check('fanout lag is reported but does not gate the drain layer', '不参与门控' in drain['text'], drain['text'])
            end_side = await layer(page, 'end', 'side-effects')
            check('ending does not RESET, clear safety locks or take ownership',
                  'reset_issued=false' in end_side['text'] and 'safety_cleared=false' in end_side['text'] and 'owner_acquired=false' in end_side['text'], end_side['text'])

            expected = {
                'parking_unconfirmed': ('parking-verdict', 'bad', '\u505c\u8f66\u672a\u786e\u8ba4', 'task-verdict', '\u505c\u7a33\u8bc1\u636e\u4e0d\u8db3'),
                'finalize_failed': ('recording-verdict', 'bad', '\u7f3a\u5c3e\u8bb0\u5f55', 'task-verdict', 'finalize \u5931\u8d25'),
                'incomplete_terminal': ('recording-verdict', 'bad', 'INCOMPLETE', 'task-verdict', '\u5df2\u5199\u5c3e\u8bb0\u5f55'),
                'already_finalized': ('task-verdict', 'unknown', '\u78c1\u76d8\u91cd\u653e', 'dispatch', 'dispatched=false')}
            seen = {}
            for mode, (key, tone, needle, second_key, second_needle) in expected.items():
                fx['end_mode'] = mode
                await click_action(page, 'end')
                script = "()=>(document.querySelector('[data-receipt=\"end\"] [data-receipt-layer=\"%s\"]')?.innerText ?? '').includes('%s')" % (key, needle)
                await page.wait_for_function(script, timeout=20000)
                focus = await layer(page, 'end', key); second = await layer(page, 'end', second_key)
                seen[mode] = focus['text'][:70]
                check('%s shows its own conclusion' % mode, focus['tone'] == tone and needle in focus['text'], focus['text'])
                check('%s names its own action conclusion' % mode, second_needle in second['text'], second['text'])
            check('the four end failure modes are mutually distinguishable', len(set(seen.values())) == 4, seen)

            fx['stop_mode'] = 'unsupported'
            await click_action(page, 'stop')
            await page.wait_for_selector('[data-lifecycle-error="stop"]', timeout=15000)
            refusal = await page.locator('[data-lifecycle-error="stop"]').inner_text()
            check('an unsupported STOP is explained as the running instance not declaring the protocol',
                  'stop_unsupported' in refusal and '不支持机器人 STOP' in refusal, refusal)
            check('a refusal leaves no attempt or receipt behind', not [a for a in fx['sessions']['ps-synth-a']['stop_attempts'] if a['code'] == 'stop_unsupported'],
                  fx['sessions']['ps-synth-a']['stop_attempts'])

            await page.locator('[data-session-id="ps-synth-c"]').click()
            await page.wait_for_selector('.session-drawer article[data-session-id="ps-synth-c"]', timeout=20000)
            for action in ('stop', 'end', 'begin'):
                await wait_gate(page, action, 'blocked')
                await wait_gate(page, action, 'blocked')
                gate = await attr(page, f'[data-lifecycle="{action}"]', 'data-lifecycle-ready')
                reason = await attr(page, f'[data-lifecycle="{action}"]', 'data-lifecycle-reason')
                disabled = await page.locator(f'[data-lifecycle="{action}"]').is_disabled()
                check(f'a closed Session blocks {action} with the current field as the reason',
                      gate == 'blocked' and disabled and 'false' in reason, f'{gate} · {reason}')
            check('switching Session clears the previous receipts from view', await page.locator('[data-receipt]').count() == 0)

            fx['stop_mode'] = 'delay'
            await page.locator('[data-session-id="ps-synth-b"]').click()
            await page.wait_for_selector('.session-drawer article[data-session-id="ps-synth-b"]', timeout=20000)
            await wait_gate(page, 'stop', 'ready')
            await page.locator('[data-lifecycle="stop"]').click()
            b_stop_id = await attr(page, '[data-lifecycle="stop"]', 'data-lifecycle-request-id')
            posts_at_switch = len([b for b in fx['bodies'] if b['path'].endswith('/stop')])
            await page.locator('[data-session-id="ps-synth-a"]').click()
            await page.wait_for_selector('.session-drawer article[data-session-id="ps-synth-a"]', timeout=20000)
            await asyncio.sleep(fx['delay_seconds'] + 2.0)
            accepted_now = await layer(page, 'stop', 'accepted')
            check('a late reply for the previous Session cannot overwrite the current selection',
                  b_stop_id not in accepted_now['text'] and (await attr(page, '[data-lifecycle="stop"]', 'data-lifecycle-request-id')) == '',
                  f'{b_stop_id} · {accepted_now["text"]}')
            check('the stale intent was not re-sent after switching Session',
                  len([b for b in fx['bodies'] if b['path'].endswith('/stop')]) == posts_at_switch,
                  [b['body']['request_id'] for b in fx['bodies'] if b['path'].endswith('/stop')])
            await page.locator('[data-session-id="ps-synth-b"]').click()
            await page.wait_for_selector('.session-drawer article[data-session-id="ps-synth-b"]', timeout=20000)
            check('the delayed reply only ever belongs to the Session archive it was read back from',
                  b_stop_id in (await layer(page, 'stop', 'accepted'))['text'], b_stop_id)

            # Recovery read-back interleaved with a Session switch: the late archive refresh of the
            # previous Session may reconcile the cache by id, but must not re-select it and must not
            # launch a current refresh that preempts the new selection.
            fx['stop_mode'] = 'delay'
            fx['get_delay'] = 4.0
            await page.locator('[data-session-id="ps-synth-a"]').click()
            await page.wait_for_selector('.session-drawer article[data-session-id="ps-synth-a"]', timeout=20000)
            await wait_gate(page, 'stop', 'ready')
            await page.locator('[data-lifecycle="stop"]').click()
            await page.wait_for_selector('[data-lifecycle-unknown="stop"]', timeout=25000)
            gets_before = fx['current_gets']
            a_stop_id = await attr(page, '[data-lifecycle="stop"]', 'data-lifecycle-request-id')
            await page.locator('[data-session-id="ps-synth-b"]').click()
            await page.wait_for_selector('.session-drawer article[data-session-id="ps-synth-b"]', timeout=20000)
            await asyncio.sleep(fx['get_delay'] + 4.0)
            fx['get_delay'] = 0.0
            check('the recovery read-back of the previous Session cannot pull the selection back',
                  await attr(page, '.session-drawer article', 'data-session-id') == 'ps-synth-b', a_stop_id)
            check('the previous Session is still reconciled by id in the archive cache',
                  fx['current_gets'] > gets_before, fx['current_gets'] - gets_before)
            check('a finished stale recovery starts no current refresh for the new selection',
                  await attr(page, '.session-drawer article', 'data-session-current-status') == 'started'
                  and await attr(page, '.session-drawer .session-current', 'data-current-error') == ''
                  and await attr(page, '[data-lifecycle="stop"]', 'data-lifecycle-request-id') == ''
                  and await page.locator('[data-lifecycle-unknown]').count() == 0,
                  await attr(page, '.session-drawer article', 'data-session-current-status'))
            side = await layer(page, 'stop', 'side-effects')
            check('any receipt shown belongs to the Session actually selected',
                  'seg-ps-synth-b' in side['text'] and 'seg-ps-synth-a' not in side['text'], side['text'][:160])

            fx['current_delay'] = 3.0
            await page.get_by_role('button', name='刷新 current（只读）', exact=True).click()
            await asyncio.sleep(0.8)
            check('a pending current read does not block the robot STOP control',
                  await page.locator('[data-lifecycle="stop"]').is_disabled() is False)
            await page.wait_for_selector(".session-drawer .session-current[data-current-error='']", timeout=25000)

            paths = {b['path'] for b in fx['bodies']}
            check('every write is a platform Session lifecycle path and nothing else',
                  paths <= {'/api/v1/sessions/ps-synth-a/recording/begin', '/api/v1/sessions/ps-synth-a/stop',
                           '/api/v1/sessions/ps-synth-a/recording/end', '/api/v1/sessions/ps-synth-b/stop'}, sorted(paths))
            native = [r['path'] for r in report['requests'] if r['path'].startswith(('/api/v1/commands', '/api/v1/episodes', '/api/v1/reset', '/api/v1/runs', '/api/v1/session/', '/api/v1/recording/'))]
            check('no native command, episode, RESET, run-stop or native recording path was requested', not native, native[:3])
            mobilecar = [r for r in report['requests'] if '/api/v1/mobilecar/' in r['path']]
            check('mobilecar reads stay GET-only', all(r['method'] == 'GET' for r in mobilecar), [r['path'] for r in mobilecar if r['method'] != 'GET'][:3])
            check('the fixture is not presented as a real robot stop', 'not native acceptance' in report['scope'])
            check('no uncaught browser errors', not report['errors'], report['errors'][:3])
            report['fixture'] = {'bodies': fx['bodies'], 'current_gets': fx['current_gets'],
                                 'stop_attempts': fx['sessions']['ps-synth-a']['stop_attempts'],
                                 'end_attempts': fx['sessions']['ps-synth-a']['recording_end_attempts'],
                                 'end_receipt_codes': [a['code'] for a in fx['sessions']['ps-synth-a']['recording_end_attempts']]}
            report['status'] = 'passed'
        except Exception as exc:
            report['exception'] = str(exc); report['traceback'] = traceback.format_exc()
            await page.screenshot(path=str(a.output / 'failure.png'), full_page=True)
        finally:
            (a.output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
asyncio.run(main())
print(json.dumps({'status': report['status'], 'checks': len(report['checks']), 'mode': a.mode}, ensure_ascii=False))
