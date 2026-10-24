"""Supplemental same-release evidence: capture the real 409 save conflict state.
Uses only the platform Draft create/save API through the preview proxy. No native calls.
"""
import asyncio, json, time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

URL = 'http://127.0.0.1:18946'
DRAFT = 'draft-68597f12a82545c8aeadc8cb8d7c4b56'
OUT = Path('/tmp/config-conflict-actual.png')

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
        page = await browser.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=1, timezone_id='America/Los_Angeles')
        try:
            await page.goto(URL + '/?inspect=1', wait_until='domcontentloaded')
            await page.wait_for_function('window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 && window.__workbenchInspect().scene.renderCount>0', timeout=90000)
            await page.get_by_role('button', name='Session 准备', exact=True).click()
            await page.wait_for_function("(id)=>[...document.querySelectorAll('.session-drawer select[aria-label=\"选择草案\"] option')].some(o=>o.value===id)", arg=DRAFT, timeout=20000)
            await page.get_by_label('选择草案', exact=True).select_option(DRAFT)
            await page.wait_for_selector(f'.session-drawer [data-draft-id="{DRAFT}"]', timeout=20000)
            current = int(await page.locator('.session-drawer [data-draft-id]').get_attribute('data-draft-revision'))
            stamp = time.strftime('%H:%M:%S')
            external_name = f'外部宿主冲突证据 {stamp}'
            external = await page.request.put(URL + f'/api/v1/experiment-drafts/{DRAFT}', data={'base_revision': current, 'name': external_name, 'description': '外部宿主已推进 revision'})
            external_body = await external.json()
            local_name = f'本地未保存冲突文本 {stamp}'
            await page.get_by_label('草案名称', exact=True).fill(local_name)
            async with page.expect_response(lambda r: urlsplit(r.url).path == f'/api/v1/experiment-drafts/{DRAFT}' and r.request.method == 'PUT') as info:
                await page.get_by_role('button', name='保存草案', exact=True).click()
            response = await info.value
            body = await response.json()
            await page.wait_for_selector('.session-drawer [data-session-error]', timeout=15000)
            error_text = await page.locator('.session-drawer [data-session-error]').inner_text()
            input_value = await page.get_by_label('草案名称', exact=True).input_value()
            await page.screenshot(path=str(OUT), full_page=True)
            print(json.dumps({'external_status': external.status, 'external_revision': external_body.get('draft_revision'),
                              'ui_status': response.status, 'ui_code': body.get('detail', {}).get('code'),
                              'error_text': error_text, 'local_input_preserved': input_value == local_name,
                              'screenshot': str(OUT), 'current_revision_before': current}, ensure_ascii=False))
        finally:
            await browser.close()

asyncio.run(main())
