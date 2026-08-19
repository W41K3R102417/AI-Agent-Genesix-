from pathlib import Path
import yaml
from playwright.sync_api import sync_playwright

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

SESSION_DIR = Path(__file__).resolve().parent / "Output" / "brave_session"

ANNOUNCEMENTS_FILE = Path(__file__).resolve().parent / "daily_input_enhanced.yaml"

MESSENGER_URL = "https://www.messenger.com/"

TEST_MESSAGE = "AUTOMATION COMPOSER TEST — DO NOT SEND"


def normalize_text(value):
    return " ".join(str(value).split()).strip()


def load_recipient():
    if not ANNOUNCEMENTS_FILE.exists():
        raise FileNotFoundError(
            f"YAML file not found: {ANNOUNCEMENTS_FILE}"
        )

    with open(ANNOUNCEMENTS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    messenger = data.get("messenger", {})

    recipient = (
        messenger.get("recipient_name")
        or data.get("recipient_name")
    )

    if not recipient:
        raise ValueError(
            "No recipient_name was found in the YAML configuration."
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

    exact_count = exact_text.count()

    print(f"Exact group-name matches: {exact_count}")

    selected = None

    for i in range(exact_count):
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
            f"Could not locate conversation '{recipient}'."
        )

    print("Conversation result identified.")

    try:
        selected.click()

    except Exception:
        print("Normal click intercepted. Using DOM click...")
        selected.evaluate("(element) => element.click()")

    page.wait_for_timeout(3000)

    body_text = normalize_text(
        page.locator("body").inner_text()
    )

    if normalize_text(recipient).casefold() not in body_text.casefold():
        raise RuntimeError(
            f"Conversation '{recipient}' could not be verified."
        )

    print(f"Conversation verified: {recipient}")


def find_message_box(page):
    selectors = [
        '[contenteditable="true"]',
        '[role="textbox"]',
        'textarea',
    ]

    for selector in selectors:
        try:
            candidates = page.locator(selector)

            for i in range(candidates.count()):
                candidate = candidates.nth(i)

                if not candidate.is_visible() or not candidate.is_enabled():
                    continue

                aria = candidate.get_attribute("aria-label")
                placeholder = candidate.get_attribute("placeholder")

                print(
                    f"Possible composer: selector={selector}, "
                    f"aria-label={aria!r}, "
                    f"placeholder={placeholder!r}"
                )

                return candidate

        except Exception:
            continue

    return None


def read_box_text(element):
    try:
        value = element.input_value()
        if value:
            return value
    except Exception:
        pass

    try:
        return element.inner_text()
    except Exception:
        return ""


def main():
    print("=" * 70)
    print("MESSENGER COMPOSER TEST")
    print("=" * 70)

    recipient = load_recipient()

    print(f"\nYAML recipient:")
    print(f"  {recipient}")

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
            print(f"Page title: {page.title()}")

            open_conversation(page, recipient)

            print("\nLooking for message composer...")

            page.wait_for_timeout(2000)

            message_box = find_message_box(page)

            if message_box is None:
                print(
                    "\nERROR: Messenger message composer "
                    "could not be located."
                )
                print("No message was sent.")
                return

            print("Message composer found.")

            print("\nTyping test message...")

            message_box.click()
            message_box.fill(TEST_MESSAGE)

            page.wait_for_timeout(500)

            current_text = normalize_text(
                read_box_text(message_box)
            )

            expected_text = normalize_text(TEST_MESSAGE)

            print(f"Expected: {expected_text!r}")
            print(f"Detected: {current_text!r}")

            if current_text != expected_text:
                print(
                    "\nERROR: Composer verification failed."
                )
                print("No message was sent.")
                return

            print(
                "\nSUCCESS: Composer accepted and verified "
                "the test message."
            )

            # Clear the test text without sending it.
            try:
                message_box.fill("")
            except Exception:
                try:
                    message_box.click()
                    message_box.press("Control+A")
                    message_box.press("Backspace")
                except Exception:
                    pass

            page.wait_for_timeout(500)

            print(
                "\nTest message cleared from the composer."
            )

            print("\n" + "=" * 70)
            print("COMPOSER TEST COMPLETE")
            print("NO MESSAGE WAS SENT.")
            print("=" * 70)

            input(
                "\nPress ENTER to close the Brave test session..."
            )

        finally:
            context.close()


if __name__ == "__main__":
    main()