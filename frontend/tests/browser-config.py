"""Server-only M1.2b configuration flow: real Draft save/reload/validate/snapshot.

The platform write requests in this test are limited to Draft create/save and
validate. Session create/start, motion, RESET, recording and native commands
are asserted absent. Fault fixtures (delayed validate, disconnected list) are
synthetic and are labelled as such; they do not alter native state.
"""
import argparse, asyncio, json, time, traceback
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

p = argparse.ArgumentParser()
p.add_argument('url')
p.add_argument('output', type=Path)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
report = {'scope': 'real platform Draft save/reload/validate/snapshot/Session reads; no Session create/start, motion, RESET or recording',
          'checks': [], 'errors': [], 'requests': [], 'fixtures': [], 'real': {}, 'status': 'failed'}


def check(name, condition, detail=None):
    if not condition:
        raise AssertionError(name if detail is None else f'{name} :: {detail}')
    report['checks'].append(name)


async def state(page):
    return await page.evaluate('window.__workbenchInspect()')


async def loaded(page):
    await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0', timeout=90000)


async def drawer_ready(page):
    await page.wait_for_function("()=>document.querySelector('.session-drawer [data-session-count]')!==null", timeout=20000)


async def open_drawer(page):
    button = page.get_by_role('button', name='Session 准备', exact=True)
    if not await page.locator('.session-drawer').count():
        await button.click()
    await drawer_ready(page)


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=[
            '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
        page = await browser.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=1,
                                      timezone_id='America/Los_Angeles')
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.on('request', lambda req: report['requests'].append({'method': req.method, 'url': req.url}))
        try:
            await page.goto(a.url + '/?inspect=1', wait_until='domcontentloaded')
            await loaded(page)
            await page.wait_for_function('window.__workbenchInspect().monitor.snapshots>=2')
            await open_drawer(page)
            drawer = page.locator('.session-drawer')
            await page.wait_for_function("()=>{const e=document.querySelector('.session-drawer [data-preflight-checked-at]');return !!(e&&e.getAttribute('data-preflight-checked-at'))}", timeout=20000)
            text = await drawer.inner_text()
            check('drawer shows the real configuration surface', all(token in text for token in ('草案 Draft', '校验 Validation', '不可变配置快照', 'prepared Session')))
            check('Start stays disabled before and after config work', await page.get_by_role('button', name='Start', exact=True).is_disabled())
            real_sessions = await page.request.get(a.url + '/api/v1/sessions')
            check('real GET /sessions is readable', real_sessions.status == 200)
            sessions_before = await real_sessions.json()
            report['real']['sessions_before'] = sessions_before
            check('empty real Session list is rendered as empty, not Ready', ('空 Session 列表' in text) if not sessions_before else True)
            preflight_checked = await page.locator('.session-drawer [data-preflight-checked-at]').get_attribute('data-preflight-checked-at')
            preflight_compatible = await page.locator('.session-drawer [data-preflight-compatible]').get_attribute('data-preflight-compatible')
            report['real']['preflight'] = {'checked_at': preflight_checked, 'read_contract_compatible': preflight_compatible}
            check('18944 preflight is displayed as a current native observation with checked_at', bool(preflight_checked))
            check('18944 live preflight does not claim a compatible session contract', preflight_compatible == 'false')
            check('preflight renders the real interface_profile failure', await page.locator('.session-drawer [data-preflight-check="interface_profile"][data-preflight-check-status="failed"]').count() == 1)
            check('archive and current observation are labelled separately', '刷新存档（不调用 native）' in text and '刷新 native 观测（只读）' in text)
            check('archive GET is not described as refreshing native', '不会刷新 native' in text or '不调用 native' in text)

            # ---- create ----
            stamp = time.strftime('%Y-%m-%d %H:%M:%S')
            create_name = f'前端 M1.2c 保存检查 {stamp}'
            await page.get_by_role('button', name='新建草案', exact=True).click()
            await page.get_by_label('新草案名称', exact=True).fill(create_name)
            await page.get_by_label('新草案描述', exact=True).fill('真实保存 / 校验 / 快照检查')
            async with page.expect_response(lambda r: urlsplit(r.url).path == '/api/v1/experiment-drafts' and r.request.method == 'POST') as created_info:
                await page.get_by_role('button', name='创建草案', exact=True).click()
            created_response = await created_info.value
            created = await created_response.json()
            draft_id = created['draft_id']
            check('POST create returned a real Draft', created_response.status == 201 and draft_id.startswith('draft-'), draft_id)
            await page.wait_for_selector(f'.session-drawer [data-draft-id="{draft_id}"]', timeout=15000)
            report['real']['created'] = {key: created[key] for key in ('draft_id', 'draft_revision', 'execution_revision', 'fingerprint', 'recipe_fingerprint', 'name')}
            check('created draft starts at draft/execution revision 1 and is unvalidated', created['draft_revision'] == 1 and created['execution_revision'] == 1 and created['validation']['status'] == 'unvalidated')
            check('only backend-supported name/description are editable', await page.get_by_label('草案名称', exact=True).is_editable() and await page.get_by_label('草案描述', exact=True).is_editable())

            # ---- save ----
            saved_name = create_name + ' · saved'
            await page.get_by_label('草案名称', exact=True).fill(saved_name)
            await page.get_by_label('草案描述', exact=True).fill('保存后重新加载仍应可见')
            async with page.expect_response(lambda r: urlsplit(r.url).path == f'/api/v1/experiment-drafts/{draft_id}' and r.request.method == 'PUT') as saved_info:
                await page.get_by_role('button', name='保存草案', exact=True).click()
            saved_response = await saved_info.value
            saved = await saved_response.json()
            check('PUT save increments only draft_revision', saved_response.status == 200 and saved['draft_revision'] == 2 and saved['execution_revision'] == 1, (saved['draft_revision'], saved['execution_revision']))
            check('save response persists name and description', saved['name'] == saved_name and saved['description'] == '保存后重新加载仍应可见')
            report['real']['saved'] = {key: saved[key] for key in ('draft_id', 'draft_revision', 'execution_revision', 'name', 'description')}

            # ---- reload the browser and selected draft ----
            await page.reload(wait_until='domcontentloaded'); await loaded(page); await open_drawer(page)
            await page.wait_for_function("(id)=>[...document.querySelectorAll('.session-drawer select[aria-label=\"选择草案\"] option')].some(o=>o.value===id)", arg=draft_id, timeout=15000)
            await page.get_by_label('选择草案', exact=True).select_option(draft_id)
            await page.wait_for_selector(f'.session-drawer [data-draft-id="{draft_id}"]', timeout=15000)
            check('reloaded draft keeps the saved metadata', await page.get_by_label('草案名称', exact=True).input_value() == saved_name)
            direct = await page.request.get(a.url + f'/api/v1/experiment-drafts/{draft_id}')
            check('GET /experiment-drafts/{id} reads the same saved revision', direct.status == 200 and (await direct.json())['draft_revision'] == 2)

            # ---- validate ----
            async with page.expect_response(lambda r: urlsplit(r.url).path == f'/api/v1/experiment-drafts/{draft_id}/validate' and r.request.method == 'POST') as valid_info:
                await page.get_by_role('button', name='运行校验', exact=True).click()
            valid_response = await valid_info.value
            validated = await valid_response.json()
            result = validated['validation']['result']
            check('validate returns a real server result and immutable snapshot id', valid_response.status == 200 and result['snapshot_id'].startswith('cs-') and len(result['snapshot_sha256']) == 64)
            check('real environment is failed and not execution eligible', result['status'] == 'failed' and result['execution_eligible'] is False and result['validated_snapshot_id'] is None)
            check('configuration and readiness checks are both present', any(c['phase'] == 'configuration' for c in result['checks']) and any(c['phase'] == 'readiness' for c in result['checks']))
            check('failed configuration and unsupported readiness are explicit', any(c['status'] == 'failed' for c in result['checks']) and any(c['status'] == 'unsupported' for c in result['checks']))
            check('blocking reasons are returned with keys and scopes', bool(result['blocking_reasons']) and all('key' in r and 'scope' in r and 'message' in r for r in result['blocking_reasons']))
            check('recipe fingerprint is a stable 64-hex value', len(result['recipe_fingerprint']) == 64 and result['recipe_fingerprint'] == validated['recipe_fingerprint'])
            report['real']['validation'] = {'snapshot_id': result['snapshot_id'], 'snapshot_sha256': result['snapshot_sha256'], 'status': result['status'],
                                            'execution_eligible': result['execution_eligible'], 'validated_snapshot_id': result['validated_snapshot_id'],
                                            'recipe_fingerprint': result['recipe_fingerprint'], 'checks': len(result['checks']),
                                            'blocking_reasons': result['blocking_reasons'][:6]}
            await page.wait_for_selector('.session-drawer [data-snapshot-id]', timeout=20000)
            check('UI shows execution_eligible=false rather than Ready', await page.locator('.session-drawer [data-execution-eligible]').get_attribute('data-execution-eligible') == 'false')
            post_validation_text = await drawer.inner_text()
            check('real failed snapshot is not presented as Ready or config eligible', 'execution_eligible' in post_validation_text and '不是 Ready' in post_validation_text)
            create_button = page.locator('.session-drawer [data-session-create]')
            check('real ineligible snapshot keeps create prepared Session disabled', await create_button.get_attribute('data-session-create') == 'blocked' and await create_button.is_disabled())
            check('real empty Session list offers no Start action', await page.locator('.session-drawer [data-session-start]').count() == 0)
            check('UI counts checks but keeps the eligibility verdict separate', '通过' in await drawer.inner_text() and '不能替代 execution_eligible' in await drawer.inner_text())
            check('UI shows snapshot hash and recipe fingerprint', await page.locator('.session-drawer [data-snapshot-sha]').get_attribute('data-snapshot-sha') == result['snapshot_sha256']
                  and await page.locator('.session-drawer [data-recipe-fingerprint]').get_attribute('data-recipe-fingerprint') == result['recipe_fingerprint'])
            ui_checks = await page.locator('.session-drawer [data-check-key]').count()
            check('UI renders every server check with phase/status', ui_checks == len(result['checks']), (ui_checks, len(result['checks'])))
            check('UI renders blocking reasons', await page.locator('.session-drawer [data-blocking-key]').count() >= len(result['blocking_reasons']))

            # ---- independent immutable snapshot read ----
            snap_response = await page.request.get(a.url + '/api/v1/config-snapshots/' + result['snapshot_id'])
            snap = await snap_response.json()
            check('GET /config-snapshots/{id} returns the same immutable document', snap_response.status == 200 and snap['snapshot_sha256'] == result['snapshot_sha256'] and snap['checks'] == result['checks'])
            check('snapshot keeps eligibility and blocking reasons', snap['execution_eligible'] is False and snap['validated_snapshot_id'] is None and snap['blocking_reasons'] == result['blocking_reasons'])
            report['real']['snapshot'] = {'snapshot_id': snap['snapshot_id'], 'snapshot_sha256': snap['snapshot_sha256'], 'validation_scope': snap['validation_scope'], 'check_count': len(snap['checks'])}
            await page.screenshot(path=str(a.output / 'config-validated.png'), full_page=True)

            # ---- real 409 save conflict ----
            current = await (await page.request.get(a.url + f'/api/v1/experiment-drafts/{draft_id}')).json()
            external_name = saved_name + ' · external'
            external = await page.request.put(a.url + f'/api/v1/experiment-drafts/{draft_id}', data={
                'base_revision': current['draft_revision'], 'name': external_name, 'description': '外部宿主保存'})
            check('external host save succeeds and advances draft_revision', external.status == 200 and (await external.json())['draft_revision'] == current['draft_revision'] + 1)
            await page.get_by_label('草案名称', exact=True).fill(saved_name + ' · local stale')
            async with page.expect_response(lambda r: urlsplit(r.url).path == f'/api/v1/experiment-drafts/{draft_id}' and r.request.method == 'PUT') as conflict_info:
                await page.get_by_role('button', name='保存草案', exact=True).click()
            conflict_response = await conflict_info.value
            check('stale base_revision gets a real 409 conflict', conflict_response.status == 409)
            conflict_body = await conflict_response.json()
            check('conflict code is preserved', conflict_body['detail']['code'] == 'conflict', conflict_body)
            await page.wait_for_selector('.session-drawer [data-session-error]')
            check('UI reports the conflict without overwriting local text', '保存冲突' in await page.locator('.session-drawer [data-session-error]').inner_text()
                  and await page.get_by_label('草案名称', exact=True).input_value() == saved_name + ' · local stale')
            after_conflict = await (await page.request.get(a.url + f'/api/v1/experiment-drafts/{draft_id}')).json()
            check('server keeps the other host value after conflict', after_conflict['name'] == external_name)
            await page.get_by_role('button', name='读取服务器版本', exact=True).click()
            await page.wait_for_function("(name)=>document.querySelector('.session-drawer input[aria-label=\\'草案名称\\']')?.value===name", arg=external_name, timeout=15000)
            check('explicit reload adopts the server revision', await page.get_by_label('草案名称', exact=True).input_value() == external_name)
            await page.screenshot(path=str(a.output / 'config-conflict.png'), full_page=True)

            # ---- delayed validate cannot overwrite a switched draft ----
            other = next((d for d in await (await page.request.get(a.url + '/api/v1/experiment-drafts')).json() if d['draft_id'] != draft_id), None)
            if other:
                hold = asyncio.Event(); released = asyncio.Event()
                async def delayed(route):
                    hold.set()
                    try:
                        response = await route.fetch()
                    except Exception:
                        released.set(); return
                    await asyncio.sleep(2.5)
                    try:
                        await route.fulfill(response=response)
                    except Exception:
                        pass
                    released.set()
                await page.route('**/api/v1/experiment-drafts/*/validate', delayed)
                await page.get_by_label('选择草案', exact=True).select_option(draft_id)
                await page.wait_for_selector(f'.session-drawer [data-draft-id="{draft_id}"]', timeout=15000)
                await page.get_by_role('button', name='运行校验', exact=True).click()
                await asyncio.wait_for(hold.wait(), 8)
                await page.get_by_label('选择草案', exact=True).select_option(other['draft_id'])
                await page.wait_for_selector(f'.session-drawer [data-draft-id="{other["draft_id"]}"]', timeout=15000)
                await asyncio.sleep(3.0)
                still = await page.locator('.session-drawer [data-draft-id]').get_attribute('data-draft-id')
                check('late validate result cannot overwrite the switched draft', still == other['draft_id'], still)
                report['fixtures'].append({'name': 'delayed validate', 'synthetic': True, 'result': 'switched draft preserved'})
                await page.unroute('**/api/v1/experiment-drafts/*/validate', delayed)
                if released.is_set():
                    pass
            else:
                report['fixtures'].append({'name': 'delayed validate', 'synthetic': True, 'result': 'skipped: only one draft exists'})

            # ---- disconnected draft list ----
            async def offline(route):
                if route.request.method == 'GET' and urlsplit(route.request.url).path == '/api/v1/experiment-drafts':
                    await route.abort(); return
                await route.continue_()
            await page.route('**/api/v1/experiment-drafts', offline)
            await page.get_by_role('button', name='刷新列表', exact=True).click()
            await page.wait_for_selector('.session-drawer [data-session-error]', timeout=15000)
            check('disconnected draft list becomes a visible error', 'Failed to fetch' in await page.locator('.session-drawer [data-session-error]').inner_text() or 'fetch' in (await page.locator('.session-drawer [data-session-error]').inner_text()).lower())
            await page.unroute('**/api/v1/experiment-drafts', offline)
            await page.get_by_role('button', name='刷新列表', exact=True).click()
            await page.wait_for_function("()=>!document.querySelector('.session-drawer [data-session-error]')", timeout=15000)
            check('draft list recovers after an explicit refresh', True)
            report['fixtures'].append({'name': 'draft list disconnect', 'synthetic': True, 'result': 'visible error then explicit recovery'})

            # ---- Session and method boundary ----
            await open_drawer(page)
            final_sessions = await (await page.request.get(a.url + '/api/v1/sessions')).json()
            report['real']['sessions_after'] = final_sessions
            check('real environment still has no prepared/active Session', final_sessions == [])
            check('UI keeps the empty Session list and Start disabled', '空 Session 列表' in await drawer.inner_text() and await page.get_by_role('button', name='Start', exact=True).is_disabled())
            forbidden = [r for r in report['requests'] if r['method'] != 'GET' and not (
                (r['method'] == 'POST' and urlsplit(r['url']).path == '/api/v1/experiment-drafts') or
                (r['method'] == 'PUT' and urlsplit(r['url']).path == f'/api/v1/experiment-drafts/{draft_id}') or
                (r['method'] == 'POST' and urlsplit(r['url']).path == f'/api/v1/experiment-drafts/{draft_id}/validate'))]
            check('browser writes are only Draft create/save/validate', not forbidden, forbidden[:5])
            session_writes = [r for r in report['requests'] if urlsplit(r['url']).path.startswith('/api/v1/sessions') and r['method'] != 'GET']
            command_calls = [r for r in report['requests'] if any(token in r['url'] for token in ('/commands', '/episodes', '/reset', '/recording', '/session/start', '/sessions/' + 'start')) or (r['method'] != 'GET' and '/sessions/' in r['url'])]
            check('no Session create/start, motion, RESET, recording or native command request', not session_writes and not command_calls, (session_writes[:3], command_calls[:3]))
            check('no uncaught browser errors', not report['errors'], report['errors'][:3])
            report['real']['request_count'] = len(report['requests'])
            report['real']['write_requests'] = [r for r in report['requests'] if r['method'] != 'GET']
            report['status'] = 'passed'
        except Exception as exc:
            report['exception'] = str(exc)
            report['traceback'] = traceback.format_exc()
            await page.screenshot(path=str(a.output / 'failure.png'), full_page=True)
        finally:
            (a.output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            await browser.close()
asyncio.run(main())
print(json.dumps({'status': report['status'], 'checks': len(report['checks']), 'error': report.get('exception')}, ensure_ascii=False))
raise SystemExit(report['status'] != 'passed')
