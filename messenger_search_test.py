from pathlib import Path
from playwright.sync_api import sync_playwright

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
SESSION_DIR = Path(__file__).resolve().parent / "Output" / "brave_session"
MESSENGER_URL = "https://www.messenger.com/"


def main():
    print("=" * 70)
    print("MESSENGER UI DIAGNOSTIC")
    print("=" * 70)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            executable_path=str(BRAVE_PATH),
            headless=False,
            viewport={"width": 1440, "height": 900},
        )

        try:
            pages = context.pages
            page = pages[0] if pages else context.new_page()

            page.set_default_timeout(10000)

            print(f"\nInitial URL: {page.url}")

            page.goto(
                MESSENGER_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            page.wait_for_timeout(5000)

            print(f"Current URL: {page.url}")
            print(f"Page title: {page.title()}")

            print("\n" + "=" * 70)
            print("VISIBLE BUTTONS")
            print("=" * 70)

            buttons = page.locator("button")
            button_count = buttons.count()
            print(f"Total button elements: {button_count}")

            for i in range(min(button_count, 50)):
                try:
                    button = buttons.nth(i)

                    if not button.is_visible():
                        continue

                    print(f"\nButton #{i}")
                    print(
                        f"  Text: {button.inner_text()[:200]!r}"
                    )
                    print(
                        f"  aria-label: "
                        f"{button.get_attribute('aria-label')!r}"
                    )
                    print(
                        f"  title: "
                        f"{button.get_attribute('title')!r}"
                    )
                    print(
                        f"  data-testid: "
                        f"{button.get_attribute('data-testid')!r}"
                    )

                except Exception as exc:
                    print(f"  Could not inspect button #{i}: {exc}")

            print("\n" + "=" * 70)
            print("ELEMENTS CONTAINING 'SEARCH'")
            print("=" * 70)

            search_elements = page.locator(
                "[aria-label*='search' i], "
                "[title*='search' i], "
                "[placeholder*='search' i]"
            )

            search_count = search_elements.count()
            print(f"Matching elements: {search_count}")

            for i in range(min(search_count, 30)):
                try:
                    element = search_elements.nth(i)

                    if not element.is_visible():
                        continue

                    print(f"\nElement #{i}")
                    print(
                        f"  Tag: "
                        f"{element.evaluate('(e) => e.tagName')}"
                    )
                    print(
                        f"  Text: {element.inner_text()[:200]!r}"
                    )
                    print(
                        f"  aria-label: "
                        f"{element.get_attribute('aria-label')!r}"
                    )
                    print(
                        f"  title: "
                        f"{element.get_attribute('title')!r}"
                    )
                    print(
                        f"  role: "
                        f"{element.get_attribute('role')!r}"
                    )

                except Exception as exc:
                    print(f"  Could not inspect element #{i}: {exc}")

            print("\n" + "=" * 70)
            print("VISIBLE PAGE TEXT")
            print("=" * 70)

            try:
                text = page.locator("body").inner_text()
                print(text[:5000])
            except Exception as exc:
                print(f"Could not read page text: {exc}")

            print("\n" + "=" * 70)
            print("NO MESSAGE WILL BE SENT")
            print("=" * 70)

            input("\nPress ENTER to close the diagnostic...")

        finally:
            context.close()


if __name__ == "__main__":
    main()