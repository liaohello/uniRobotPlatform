"""Server-only browser verification. Synthetic responses are explicitly labelled.

Run with a server Playwright environment, passing the isolated gateway URL and
an output directory. Does not start a native service or send native commands.
"""

import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(base_url, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(base_url + "/api/v1/mobilecar/preflight", timeout=15) as response:
        native_report = json.load(response)
    assert native_report["session_ready"] is False
    assert native_report["read_only"] is True

    checks = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        requests = []
        page.on("request", lambda request: requests.append((request.method, request.url)))
        page.goto(base_url + "/mobilecar/", wait_until="networkidle")
        page.get_by_role("button", name="核对当前服务", exact=True).click()
        page.wait_for_function("!document.querySelector('[data-check]').disabled")
        assert page.get_by_role("button", name="创建 prepared Session").is_disabled()
        assert page.get_by_role("button", name="Start", exact=True).is_disabled()
        assert "Session" in page.locator("[data-status]").inner_text()
        assert "未就绪" in page.locator("[data-status]").inner_text()
        checks.append("live_native_read_only_and_disabled_session_actions")
        page.screenshot(path=str(output / "mobilecar-preflight.png"), full_page=True)

        # This fixture demonstrates UI behavior, not a successful native preset.
        fixture = json.loads(json.dumps(native_report))
        fixture["read_contract_compatible"] = True
        fixture["runtime_identity"] = {
            "run_id": '<img src=x onerror="window.__injected=true">',
            "backend_generation": 1,
            "episode_id": "synthetic-browser-episode",
        }
        fixture["checks"] = [{"key": "synthetic_fixture", "status": "passed", "detail": "synthetic UI verification only"}]
        page.route("**/api/v1/mobilecar/preflight", lambda route: route.fulfill(json=fixture))
        page.get_by_role("button", name="核对当前服务", exact=True).click()
        page.wait_for_function("!document.querySelector('[data-check]').disabled")
        assert "Session 仍未就绪" in page.locator("[data-status]").inner_text()
        assert page.get_by_role("button", name="Start", exact=True).is_disabled()
        assert '<img src=x onerror=' in page.locator("[data-runtime]").inner_text()
        assert page.locator("[data-runtime] img").count() == 0
        assert page.evaluate("window.__injected === undefined")
        checks.append("synthetic_compatible_fields_do_not_enable_session_or_parse_html")

        page.unroute("**/api/v1/mobilecar/preflight")
        page.route("**/api/v1/mobilecar/preflight", lambda route: route.abort())
        page.get_by_role("button", name="核对当前服务", exact=True).click()
        page.wait_for_function("!document.querySelector('[data-check]').disabled")
        assert "本次读取失败" in page.locator("[data-runtime]").inner_text()
        assert "synthetic-browser-episode" not in page.locator("[data-runtime]").inner_text()
        assert page.locator("[data-preset]").inner_text() == ""
        assert page.locator("[data-checks]").inner_text() == ""
        assert page.locator("[data-error]").is_visible()
        checks.append("failed_refresh_clears_old_identity_and_results")

        # Exercise two real mounts in one document, not two isolated browser tabs.
        awaitable = """async (fixture) => {
          const { mountIntegration } = await import('/mobilecar/panel.js');
          const original = document.querySelector('#integration');
          const clone = original.cloneNode(true);
          clone.id = 'integration-second';
          document.body.append(clone);
          const before = original.querySelector('[data-runtime]').textContent;
          const dispose = mountIntegration(clone, { loadPreflight: async () => fixture });
          clone.querySelector('[data-check]').click();
          await new Promise(resolve => setTimeout(resolve, 0));
          const independent = original.querySelector('[data-runtime]').textContent === before
            && clone.querySelector('[data-runtime]').textContent.includes('synthetic-browser-episode');
          dispose();
          clone.remove();
          return independent;
        }"""
        assert page.evaluate(awaitable, fixture)
        checks.append("two_host_mounts_have_independent_state")
        assert all(method == "GET" for method, _ in requests)
        checks.append("browser_sent_get_requests_only")

        page.unroute("**/api/v1/mobilecar/preflight")
        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="核对当前服务", exact=True).click()
        page.wait_for_function("!document.querySelector('[data-check]').disabled")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(output / "mobilecar-preflight-mobile.png"), full_page=True)
        checks.append("mobile_layout_has_no_horizontal_overflow")
        browser.close()

    report = {"status": "passed", "checks": checks, "native_preflight": native_report,
              "synthetic_cases_are_product_acceptance": False}
    (output / "browser.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "passed", "checks": checks}))


if __name__ == "__main__":
    verify(sys.argv[1], sys.argv[2])
