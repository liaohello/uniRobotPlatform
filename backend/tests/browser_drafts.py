"""Server-only draft UI checks; metadata is synthetic and no native writes occur."""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(base_url, output_dir):
    output = Path(output_dir)
    checks = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        page.goto(base_url + "/mobilecar/", wait_until="networkidle")
        page.locator('[data-draft-name]').fill('M1.2 synthetic browser draft')
        page.locator('[data-draft-description]').fill('UI verification metadata; not a human demonstration')
        with page.expect_response(lambda response: response.url.endswith('/api/v1/experiment-drafts') and response.request.method == 'POST') as saved:
            page.locator('[data-draft-save]').click()
        draft = saved.value.json()
        page.wait_for_function("!document.querySelector('[data-draft-save]').disabled")
        assert draft['draft_id'] in page.locator('[data-draft-summary]').inner_text()
        draft_id = draft['draft_id']
        draft_path = '/api/v1/experiment-drafts/' + draft_id

        def load(page):
            page.goto(base_url + '/mobilecar/', wait_until='networkidle')
            page.locator('[data-draft-list]').select_option(draft_id)
            page.wait_for_function("!document.querySelector('[data-draft-save]').disabled")
            assert draft_id in page.locator('[data-draft-summary]').inner_text()

        load(page)
        assert page.locator('[data-draft-name]').input_value() == draft['name']
        checks.append('saved_draft_survives_page_reload')

        with page.expect_response(lambda response: response.url.endswith(draft_path + '/validate')) as validation:
            page.locator('[data-draft-validate]').click()
        checked = validation.value.json()
        page.wait_for_function("!document.querySelector('[data-draft-save]').disabled")
        assert checked['validation']['status'] == 'failed'
        assert checked['validation']['result']['validated_snapshot_id'] is None
        assert '未签发执行快照' in page.locator('[data-draft-status]').inner_text()
        assert page.get_by_role('button', name='Start', exact=True).is_disabled()
        checks.append('unsupported_binding_does_not_issue_snapshot_or_session')

        page.locator('[data-draft-name]').fill('Metadata rename')
        with page.expect_response(lambda response: response.url.endswith(draft_path) and response.request.method == 'PUT') as saved:
            page.locator('[data-draft-save]').click()
        renamed = saved.value.json()
        page.wait_for_function("!document.querySelector('[data-draft-save]').disabled")
        assert renamed['draft_revision'] == 2
        assert renamed['execution_revision'] == draft['execution_revision']
        assert renamed['fingerprint'] == draft['fingerprint']
        assert renamed['validation'] == checked['validation']
        checks.append('metadata_save_preserves_execution_identity_and_validation')

        other = browser.new_page()
        load(other)
        page.locator('[data-draft-name]').fill('Accepted host update')
        page.locator('[data-draft-save]').click()
        page.wait_for_function("!document.querySelector('[data-draft-save]').disabled")
        other.locator('[data-draft-name]').fill('Rejected stale host update')
        with other.expect_response(lambda response: response.url.endswith(draft_path) and response.request.method == 'PUT') as rejected:
            other.locator('[data-draft-save]').click()
        assert rejected.value.status == 409
        other.wait_for_function("!document.querySelector('[data-draft-save]').disabled")
        assert other.locator('[data-draft-error]').is_visible()
        other.locator('[data-draft-discard]').click()
        other.wait_for_function("!document.querySelector('[data-draft-save]').disabled")
        assert other.locator('[data-draft-name]').input_value() == 'Accepted host update'
        checks.append('stale_host_save_conflicts_and_explicit_reload_recovers')

        invalid = page.request.post(base_url + '/api/v1/experiment-drafts', data={'name': 'invalid fixture', 'initial_state': {'joint1': 0}})
        assert invalid.status == 422
        session = page.request.post(base_url + '/api/v1/sessions', data={
            'execution_revision': draft['execution_revision'], 'fingerprint': draft['fingerprint'],
            'validated_snapshot_id': 'forged', 'idempotency_key': 'synthetic-browser-key'})
        assert session.status == 409
        assert all('/commands' not in url and '/episodes' not in url for url in requests)
        checks.append('unsupported_execution_fields_and_forged_snapshot_rejected')
        page.locator('#draft-editor').screenshot(path=str(output / 'draft-editor.png'))
        browser.close()
    report = {'status': 'passed', 'checks': checks, 'draft_id': draft_id,
              'synthetic_cases_are_product_acceptance': False}
    (output / 'draft-browser.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    verify(sys.argv[1], sys.argv[2])
