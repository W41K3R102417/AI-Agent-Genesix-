from pathlib import Path
import yaml
from playwright.sync_api import sync_playwright

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

SESSION_DIR = Path(__file__).resolve().parent / "Output" / "brave_session"

ANNOUNCEMENTS_FILE = Path(__file__).resolve().parent / "daily_input_enhanced.yaml"

MESSENGER_URL = "https://www.messenger.com/"

TEST_MESSAGE = "AUTOMATION LIVE SEND TEST — PLEASE IGNORE"


def normalize_text(value):
    return " ".join(str(value).split()).strip()


def load_recipient():
    with open(ANNOUNCEMENTS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    messenger = data.get("messenger", {})

    recipient = (
        messenger.get("recipient_name")
        or data.get("recipient_name")
    )

    if not recipient:
        raise RuntimeError(
            "No recipient_name found in YAML."
        )

    return str(recipient)


def find_search_box(page):
    selectors = [
        'input[aria-label="Search Messenger"]',
        'input[aria-label*="Search Messenger" i]',
        'input[role="combobox"]',
    ]

    for selector in selectors:
        try:
            candidates = page.locator(selector)

            for i in range(candidates.count()):
                candidate = candidates.nth(i)

                if candidate.is_visible() and candidate.is_enabled():
                    return candidate

        except Exception:
            continue

    return None


def find_composer(page):
    selectors = [
        '[contenteditable="true"][aria-label*="Write to" i]',
        '[contenteditable="true"]',
        '[role="textbox"]',
    ]

    for selector in selectors:
        try:
            candidates = page.locator(selector)

            for i in range(candidates.count()):
                candidate = candidates.nth(i)

                if candidate.is_visible() and candidate.is_enabled():
                    return candidate

        except Exception:
            continue

    return None


def open_conversation(page, recipient):
    search_box = find_search_box(page)

    if search_box is None:
        raise RuntimeError(
            "Messenger search box could not be located."
        )

    print(f"Searching for: {recipient}")

    search_box.click()
    search_box.fill(recipient)

    page.wait_for_timeout(2500)

    exact_text = page.get_by_text(
        recipient,
        exact=True
    )

    selected = None

    for i in range(exact_text.count()):
        try:
            element = exact_text.nth(i)

            if not element.is_visible():
                continue

            clickable = element.locator(
                "xpath=ancestor-or-self::*["
                "@role='button' or "
                "@role='link' or "
                "@tabindex='0'"
                "]"
            ).last

            if clickable.count() > 0 and clickable.is_visible():
                selected = clickable
                break

            selected = element

        except Exception:
            continue

    if selected is None:
        raise RuntimeError(
            f"Could not locate '{recipient}' in search results."
        )

    print("Conversation result found.")

    try:
        selected.click()

    except Exception:
        print("Normal click intercepted. Using DOM click...")
        selected.evaluate("(element) => element.click()")

    page.wait_for_timeout(3000)

    body = normalize_text(
        page.locator("body").inner_text()
    )

    if normalize_text(recipient).casefold() not in body.casefold():
        raise RuntimeError(
            f"Could not verify conversation '{recipient}'."
        )

    print(f"Conversation verified: {recipient}")


def read_composer(composer):
    try:
        value = composer.input_value()
        if value:
            return value
    except Exception:
        pass

    try:
        return composer.inner_text()
    except Exception:
        return ""


def main():
    recipient = load_recipient()

    print("=" * 70)
    print("LIVE MESSENGER SEND TEST")
    print("=" * 70)
    print(f"Recipient: {recipient}")
    print(f"Test message: {TEST_MESSAGE}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            executable_path=BRAVE_PATH,
            headless=False,
            viewport={
                "width": 1440,
                "height": 900,
            },
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )

        try:
            pages = context.pages
            page = pages[0] if pages else context.new_page()

            page.set_default_timeout(10000)

            print("\nOpening Messenger...")

            page.goto(
                MESSENGER_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            page.wait_for_timeout(5000)

            print(f"Current URL: {page.url}")

            open_conversation(page, recipient)

            print("\nFinding message composer...")

            composer = find_composer(page)

            if composer is None:
                raise RuntimeError(
                    "Message composer could not be located."
                )

            print(
                "Composer found: "
                f"aria-label={composer.get_attribute('aria-label')!r}"
            )

            print("\nTyping test message...")

            composer.click()
            composer.fill(TEST_MESSAGE)

            page.wait_for_timeout(500)

            typed = normalize_text(
                read_composer(composer)
            )

            expected = normalize_text(TEST_MESSAGE)

            print(f"Expected: {expected!r}")
            print(f"Detected: {typed!r}")

            if typed != expected:
                raise RuntimeError(
                    "Composer verification failed. "
                    "MESSAGE WAS NOT SENT."
                )

            print("\nComposer verification successful.")

            print("\nSending test message...")

            composer.press("Enter")

            page.wait_for_timeout(3000)

            # Check visible page text for the test message.
            body = normalize_text(
                page.locator("body").inner_text()
            )

            if expected.casefold() in body.casefold():
                print("\nSUCCESS!")
                print(
                    "The live test message appears in "
                    "the Messenger conversation."
                )
            else:
                print(
                    "\nWARNING: Enter was pressed, but the test "
                    "message could not be confirmed in the visible page."
                )

            print("\n" + "=" * 70)
            print("LIVE SEND TEST COMPLETE")
            print("=" * 70)

            input(
                "\nPress ENTER to close the Brave test session..."
            )

        finally:
            context.close()


if __name__ == "__main__":
    main()