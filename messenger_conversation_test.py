from pathlib import Path
import yaml
from playwright.sync_api import sync_playwright

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

SESSION_DIR = Path(__file__).resolve().parent / "Output" / "brave_session"

ANNOUNCEMENTS_FILE = Path(__file__).resolve().parent / "daily_input_enhanced.yaml"

MESSENGER_URL = "https://www.messenger.com/"


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


def main():
    print("=" * 70)
    print("MESSENGER CONVERSATION TEST")
    print("=" * 70)

    recipient = load_recipient()

    print(f"\nYAML recipient:")
    print(f"  {recipient}")

    print("\nOpening persistent Brave session...")

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

            print(f"Initial URL: {page.url}")

            print("Opening Messenger...")
            page.goto(
                MESSENGER_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            page.wait_for_timeout(5000)

            print(f"Current URL: {page.url}")
            print(f"Page title: {page.title()}")

            # ------------------------------------------------
            # Find Messenger search
            # ------------------------------------------------

            search_box = find_search_box(page)

            if search_box is None:
                print("\nERROR: Search Messenger input was not found.")
                print("No message was sent.")
                return

            print("\nSearch Messenger input found.")

            # ------------------------------------------------
            # Search for configured group
            # ------------------------------------------------

            print(f"Searching for: {recipient}")

            search_box.click()
            search_box.fill(recipient)

            page.wait_for_timeout(2500)

            print("\nInspecting search results...")

            page.wait_for_timeout(2000)

            print(
                f"Target conversation: {recipient!r}"
            )

            exact_text = page.get_by_text(
                recipient,
                exact=True
            )

            exact_count = exact_text.count()

            print(
                f"Exact text matches found: {exact_count}"
            )

            selected = None

            for i in range(exact_count):
                try:
                    element = exact_text.nth(i)

                    if not element.is_visible():
                        continue

                    print(f"\nExact match #{i}")

                    print(
                        f"  Tag: "
                        f"{element.evaluate('(e) => e.tagName')}"
                    )

                    print(
                        f"  Role: "
                        f"{element.get_attribute('role')!r}"
                    )

                    print(
                        f"  aria-label: "
                        f"{element.get_attribute('aria-label')!r}"
                    )

                    # Find the nearest clickable ancestor.
                    clickable = element.locator(
                        "xpath=ancestor-or-self::*["
                        "@role='button' or "
                        "@role='link' or "
                        "@tabindex='0'"
                        "]"
                    ).last

                    try:
                        if clickable.count() > 0 and clickable.is_visible():
                            selected = clickable
                            print(
                                "  Clickable ancestor found."
                            )
                            break
                    except Exception:
                        pass

                    # If no clickable ancestor was found, try the
                    # exact text element itself.
                    selected = element

                except Exception as exc:
                    print(
                        f"  Could not inspect match #{i}: {exc}"
                    )

            if selected is None:
                print(
                    "\nNo usable exact conversation result was found."
                )
                print("No message was sent.")
                return

            print("\nConversation result selected.")

            try:
                print(
                    f"Selected tag: "
                    f"{selected.evaluate('(e) => e.tagName')}"
                )

                print(
                    f"Selected role: "
                    f"{selected.get_attribute('role')!r}"
                )

                print("\nClicking conversation result...")

                selected.click()

                page.wait_for_timeout(3000)

                print(
                    f"URL after click: {page.url}"
                )

                print(
                    f"Page title after click: {page.title()}"
                )

            except Exception as exc:
                print(
                    f"\nNormal click failed: {exc}"
                )

                print(
                    "Trying JavaScript click..."
                )

                try:
                    selected.evaluate(
                        "(element) => element.click()"
                    )

                    page.wait_for_timeout(3000)

                    print(
                        f"URL after JavaScript click: {page.url}"
                    )

                except Exception as click_exc:
                    print(
                        f"JavaScript click failed: {click_exc}"
                    )

                    print("No message was sent.")
                    return

            # ------------------------------------------------
            # Verify conversation
            # ------------------------------------------------

            body_text = normalize_text(
                page.locator("body").inner_text()
            )

            print("\nCurrent URL:")
            print(page.url)

            print("\nChecking for target group name...")

            if normalize_text(recipient).casefold() in body_text.casefold():

                print(
                    f"SUCCESS: Conversation '{recipient}' "
                    "appears to be open."
                )
            else:
                print(
                    "WARNING: The target group name was not clearly "
                    "detected in the visible page text."
                )

            print("\n" + "=" * 70)
            print("CONVERSATION TEST COMPLETE")
            print("NO MESSAGE WAS TYPED OR SENT.")
            print("=" * 70)

            input(
                "\nPress ENTER to close the Brave test session..."
            )

        finally:
            context.close()


if __name__ == "__main__":
    main()