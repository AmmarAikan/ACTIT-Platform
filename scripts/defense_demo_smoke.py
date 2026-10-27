"""Browser-level smoke validation for the isolated graduation-defense flow."""
from __future__ import annotations

import argparse
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright

EVENT_ID = "demo-external-0001"
ATTACK_CANDIDATE_ID = "demo-external-attack-candidate"
ACCOUNTS = {
    "viewer": ("demo-viewer", "ViewerDemo!2026"),
    "analyst": ("demo-analyst", "AnalystDemo!2026"),
    "admin": ("demo-admin", "AdminDemo!2026"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def new_page(browser: Browser, base_url: str, language: str = "en") -> Page:
    context = browser.new_context(base_url=base_url, accept_downloads=True)
    page = context.new_page()
    page.add_init_script(f"sessionStorage.setItem('cti_language', '{language}')")
    return page


def login(page: Page, role: str, language: str = "en") -> None:
    username, password = ACCOUNTS[role]
    page.goto("/login")
    page.locator("#username").fill(username)
    page.locator("#password").fill(password)
    page.get_by_role("button", name="Sign in" if language == "en" else "تسجيل الدخول", exact=True).click()
    page.wait_for_url("**/dashboard")
    page.get_by_text(username, exact=True).wait_for()


def api_json(page: Page, path: str, method: str = "GET") -> tuple[int, Any]:
    return page.evaluate(
        """async ({path, method}) => {
          const token = sessionStorage.getItem('cti_access_token');
          const response = await fetch(path, {method, headers: {Authorization: `Bearer ${token}`, Accept: 'application/json'}});
          let body = null; try { body = await response.json(); } catch (_) {}
          return [response.status, body];
        }""",
        {"path": path, "method": method},
    )


def public_flow(browser: Browser, base_url: str) -> None:
    page = new_page(browser, base_url)
    page.goto("/")
    repository = page.get_by_role("link", name="Open the ACTIT source repository on GitHub in a new tab")
    repository.wait_for()
    require(repository.get_attribute("href") == "https://github.com/AmmarAikan/ACTIT-Platform", "public repository href is incorrect")
    require(repository.get_attribute("target") == "_blank", "public repository link does not open a new tab")
    require("noreferrer" in (repository.get_attribute("rel") or ""), "public repository link is missing noreferrer")

    page.goto("/login")
    page.get_by_role("heading", name="Demo access", exact=True).wait_for()
    page.get_by_text("demo-viewer", exact=True).wait_for()
    page.get_by_text("ViewerDemo!2026", exact=True).wait_for()
    page.get_by_text("demo-analyst", exact=True).wait_for()
    page.get_by_text("AnalystDemo!2026", exact=True).wait_for()
    require(page.get_by_text("demo-admin", exact=True).count() == 0, "admin credentials are visible on the public login page")

    page.context.close()

    arabic_page = new_page(browser, base_url, "ar")
    arabic_page.goto("/login")
    arabic_page.get_by_role("heading", name="وصول العرض التجريبي", exact=True).wait_for()
    require(arabic_page.locator("html").get_attribute("dir") == "rtl", "Arabic public login is not RTL")
    arabic_page.get_by_text("demo-viewer", exact=True).wait_for()
    arabic_page.get_by_text("demo-analyst", exact=True).wait_for()
    arabic_page.context.close()


def viewer_flow(browser: Browser, base_url: str) -> None:
    page = new_page(browser, base_url)
    login(page, "viewer")
    page.goto("/admin")
    page.get_by_text("Access denied", exact=True).wait_for()
    status, _ = api_json(page, "/api/v1/admin/users")
    require(status == 403, "viewer unexpectedly accessed administration API")
    page.goto(f"/intelligence/events/{EVENT_ID}")
    page.get_by_text("[DEMO] Public advisory mentions T1059.001", exact=True).wait_for()
    page.get_by_text("9.8", exact=True).wait_for()
    page.get_by_text("CWE-78", exact=False).wait_for()
    status, stix = api_json(page, f"/api/v1/events/{EVENT_ID}/stix")
    require(status == 200 and stix.get("type") == "bundle", "STIX 2.1 bundle was not available")
    require(any(item.get("type") == "vulnerability" for item in stix.get("objects", [])), "STIX vulnerability object missing")
    page.context.close()


def analyst_flow(browser: Browser, base_url: str, reviews_mode: str) -> None:
    page = new_page(browser, base_url)
    login(page, "analyst")
    require(page.locator("#primary-navigation").get_by_text("Analysis Runs", exact=True).count() == 0, "Analysis Runs remains in normal navigation")
    page.goto("/system/readiness")
    page.get_by_role("heading", name="System Readiness", level=2).wait_for()
    page.get_by_text("Central database", exact=True).wait_for()
    require(page.get_by_text("Extraction model", exact=True).count() == 0, "Extraction Model remains on System Readiness")

    page.goto("/intelligence/events")
    page.get_by_role("heading", name="Events", level=2).wait_for()
    event_link = page.get_by_role("link", name="[DEMO] Public advisory mentions T1059.001", exact=True)
    event_link.wait_for()
    event_link.click()
    page.wait_for_url(f"**/intelligence/events/{EVENT_ID}")
    page.get_by_text("CVE-2026-1234", exact=False).first.wait_for()

    page.goto("/intelligence/search?q=CVE-2026-1234")
    page.get_by_text('Results for “CVE-2026-1234”', exact=True).wait_for()

    page.goto(f"/intelligence/storyline/{EVENT_ID}")
    page.get_by_text("Explainable risk", exact=True).wait_for()
    page.get_by_text("Internal and external link", exact=True).wait_for()

    page.goto(f"/intelligence/events/{ATTACK_CANDIDATE_ID}")
    page.get_by_text("Automated candidate for review", exact=False).wait_for()
    page.get_by_text("T1053", exact=False).wait_for()

    page.goto("/intelligence/attack")
    page.get_by_role("heading", name="MITRE ATT&CK", level=2).wait_for()
    page.locator("#attack-event-select").select_option(ATTACK_CANDIDATE_ID)
    page.get_by_text("T1053", exact=False).wait_for()
    page.get_by_text("Automated candidate for review", exact=False).wait_for()

    page.goto("/intelligence/outliers")
    page.get_by_text("Credential attempts", exact=False).wait_for()
    page.get_by_text("Maximum rule severity", exact=False).wait_for()

    page.goto("/analysis")
    status, ml = api_json(page, "/api/v1/intelligence/ml/status")
    require(status == 200, "ML transparency contract was unavailable")
    runtime_state = ml.get("runtime_state")
    require(runtime_state in {"secondary_fallback_active", "unavailable"}, f"unexpected isolated ML state: {runtime_state}")
    require(len(ml.get("quality_gates", [])) == 9, "ML quality-gate evidence was incomplete")
    require(bool(ml.get("limitations")), "ML limitations were not projected")
    runtime_label = "Secondary fallback active" if runtime_state == "secondary_fallback_active" else "No model available"
    page.get_by_text(runtime_label, exact=True).wait_for(timeout=30_000)
    page.get_by_text("Saved metrics do not represent live production accuracy.", exact=True).wait_for()

    page.goto("/reviews")
    if reviews_mode == "available":
        page.get_by_text("[DEMO] Analyst review candidate", exact=True).wait_for()
    else:
        page.get_by_text("No reviews yet", exact=True).wait_for()

    page.goto("/internal-sources/web-access")
    page.get_by_text("Available", exact=True).wait_for()
    status, health = api_json(page, "/api/v1/integrations/web-access/health")
    require(status == 200 and health.get("reachable") is True and health.get("contract_valid") is True, "Web Access health contract failed")
    status, page_data = api_json(page, "/api/v1/internal/sources/web-access/events?limit=10&offset=0")
    require(status == 200 and page_data.get("total", 0) >= 1, "Web Access read projection is empty")
    if reviews_mode == "available":
        status, pull = api_json(page, "/api/v1/integrations/web-access/pull", method="POST")
        require(status == 200 and pull.get("pipeline") == "internal", "isolated Web Access pull failed")
        require(pull.get("failed_count") == 0, "isolated Web Access pull reported failures")

    page.context.close()

    arabic_page = new_page(browser, base_url, "ar")
    login(arabic_page, "analyst", "ar")
    arabic_page.goto("/system/readiness")
    arabic_page.get_by_role("heading", name="جاهزية النظام", level=2).wait_for()
    require(arabic_page.locator("html").get_attribute("dir") == "rtl", "Arabic authenticated interface is not RTL")
    require(arabic_page.get_by_text("نموذج الاستخراج", exact=True).count() == 0, "Arabic Extraction Model remains on System Readiness")
    arabic_page.goto("/intelligence/events")
    arabic_page.get_by_role("link", name="[DEMO] Public advisory mentions T1059.001", exact=True).wait_for()
    require(arabic_page.locator('[role="alert"]').count() == 0, "Arabic Events rendered an error state")
    arabic_page.goto(f"/intelligence/storyline/{EVENT_ID}")
    arabic_page.get_by_role("heading", name="[DEMO] Public advisory mentions T1059.001", level=2, exact=True).wait_for()
    require(arabic_page.locator('[role="alert"]').count() == 0, "Arabic Storyline rendered an error state")
    arabic_page.goto("/intelligence/attack")
    arabic_page.locator("#attack-event-select").select_option(EVENT_ID)
    arabic_page.locator(".attack-results").get_by_text("T1059.001", exact=True).wait_for()
    require(arabic_page.locator('[role="alert"]').count() == 0, "Arabic ATT&CK rendered an error state")
    arabic_page.context.close()


def admin_flow(browser: Browser, base_url: str) -> None:
    page = new_page(browser, base_url)
    login(page, "admin")
    page.goto("/admin")
    page.get_by_role("cell", name="demo-viewer", exact=True).first.wait_for()
    page.get_by_role("cell", name="demo-analyst", exact=True).first.wait_for()
    page.get_by_role("cell", name="demo-admin", exact=True).first.wait_for()

    page.goto("/misp")
    page.get_by_text("Non-delivery demo mode", exact=True).wait_for()
    page.get_by_text("[DEMO] Public advisory mentions T1059.001", exact=True).wait_for()
    require(page.get_by_role("button", name="Send selected events").count() == 0, "live MISP send control is visible in demo mode")
    page.get_by_role("button", name="Review preview").first.click()
    page.get_by_text("CVE-2026-1234", exact=True).wait_for()
    page.get_by_text("No", exact=True).wait_for()
    page.context.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:19090")
    parser.add_argument("--reviews-mode", choices=("available", "empty"), default="available")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            if args.reviews_mode == "available":
                public_flow(browser, args.base_url)
                viewer_flow(browser, args.base_url)
                admin_flow(browser, args.base_url)
            analyst_flow(browser, args.base_url, args.reviews_mode)
        finally:
            browser.close()
    print(f"browser smoke passed (reviews={args.reviews_mode})")


if __name__ == "__main__":
    main()
