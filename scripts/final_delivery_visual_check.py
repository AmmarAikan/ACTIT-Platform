"""Capture deterministic desktop evidence for the isolated final-delivery demo."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright

BASE_URL = "http://frontend:8080"
ARTIFACTS = Path("/artifacts")
EVENT_ID = "demo-external-0001"
ATTACK_CANDIDATE_ID = "demo-external-attack-candidate"


def page_for(browser: Browser, language: str) -> tuple[Page, list[str]]:
    context = browser.new_context(base_url=BASE_URL, viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    page.add_init_script(f"sessionStorage.setItem('cti_language', '{language}')")
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
    page.on("console", lambda message: errors.append(f"console: {message.text}") if message.type == "error" else None)
    return page, errors


def capture(page: Page, name: str) -> None:
    page.screenshot(path=str(ARTIFACTS / f"{name}.png"), full_page=True)


def login(page: Page, language: str) -> None:
    page.goto("/login")
    page.locator("#username").fill("demo-analyst")
    page.locator("#password").fill("AnalystDemo!2026")
    page.get_by_role("button", name="Sign in" if language == "en" else "تسجيل الدخول", exact=True).click()
    page.wait_for_url("**/dashboard")
    page.get_by_text("demo-analyst", exact=True).wait_for()


def public_evidence(browser: Browser, language: str) -> list[str]:
    page, errors = page_for(browser, language)
    page.goto("/")
    page.get_by_role("link", name=(
        "Open the ACTIT source repository on GitHub in a new tab"
        if language == "en" else "فتح مستودع ACTIT على GitHub في علامة تبويب جديدة"
    )).wait_for()
    capture(page, f"landing-{language}")
    page.goto("/login")
    page.get_by_text("demo-viewer", exact=True).wait_for()
    page.get_by_text("demo-analyst", exact=True).wait_for()
    capture(page, f"login-{language}")
    page.context.close()
    return errors


def authenticated_evidence(browser: Browser, language: str) -> list[str]:
    page, errors = page_for(browser, language)
    login(page, language)
    capture(page, f"dashboard-{language}")

    page.goto("/system/readiness")
    page.get_by_role("heading", name="System Readiness" if language == "en" else "جاهزية النظام", level=2).wait_for()
    capture(page, f"readiness-{language}")

    page.goto("/intelligence/events")
    page.get_by_role("link", name="[DEMO] Public advisory mentions T1059.001", exact=True).wait_for()
    capture(page, f"events-{language}")

    page.goto(f"/intelligence/storyline/{EVENT_ID}")
    page.get_by_role("heading", name="[DEMO] Public advisory mentions T1059.001", level=2, exact=True).wait_for()
    capture(page, f"storyline-{language}")

    page.goto("/intelligence/attack")
    page.locator("#attack-event-select").select_option(ATTACK_CANDIDATE_ID)
    page.locator(".attack-results").get_by_text("T1053", exact=True).wait_for()
    capture(page, f"attack-{language}")
    page.context.close()
    return errors


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    all_errors: dict[str, list[str]] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for language in ("en", "ar"):
                all_errors[f"public-{language}"] = public_evidence(browser, language)
                all_errors[f"authenticated-{language}"] = authenticated_evidence(browser, language)
        finally:
            browser.close()
    (ARTIFACTS / "browser-errors.json").write_text(json.dumps(all_errors, ensure_ascii=False, indent=2), encoding="utf-8")
    error_count = sum(len(errors) for errors in all_errors.values())
    print(f"captured 14 desktop screenshots; browser errors: {error_count}")
    if error_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
