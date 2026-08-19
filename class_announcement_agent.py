"""
Class Announcement Agent
------------------------
Robust Windows/Brave/Playwright class announcement automation.

Commands:
    python class_announcement_agent_fixed.py setup
    python class_announcement_agent_fixed.py test
    python class_announcement_agent_fixed.py run
    python class_announcement_agent_fixed.py schedule
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

ANNOUNCEMENTS_FILE = BASE_DIR / "daily_input_enhanced.yaml"

OUTPUT_DIR = BASE_DIR / "Output"
CACHE_FILE = OUTPUT_DIR / "announcement_cache.json"
QUEUE_DIR = OUTPUT_DIR / "queue"
LOG_DIR = OUTPUT_DIR / "logs"
SESSION_DIR = OUTPUT_DIR / "brave_session"

DEFAULT_HOUR = 8
DEFAULT_MINUTE = 0
DEFAULT_DUPLICATE_WINDOW_HOURS = 24

MESSENGER_URL = "https://www.messenger.com/"

BRAVE_PATHS = [
    Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave_browser.exe"),
    Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave_browser.exe"),
]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ClassAnnouncementAgent")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logfile = LOG_DIR / f"agent_{dt.datetime.now():%Y%m%d}.log"
    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger


logger = configure_logging()


def ensure_directories() -> None:
    for directory in (
        BASE_DIR,
        OUTPUT_DIR,
        QUEUE_DIR,
        LOG_DIR,
        SESSION_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def find_brave() -> Optional[Path]:
    """Find Brave without relying on shutil.which() for absolute paths."""
    for candidate in BRAVE_PATHS:
        if candidate.is_file():
            return candidate

    for executable in ("brave.exe", "brave_browser.exe"):
        found = shutil.which(executable)
        if found:
            return Path(found)

    return None


def normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


# ---------------------------------------------------------------------------
# Announcement model
# ---------------------------------------------------------------------------

@dataclass
class Announcement:
    type: str
    title: str = ""
    body: str = ""
    priority: str = "normal"
    category: str = "general"
    target_audience: Optional[str] = None
    expires_date: Optional[str] = None
    attachments: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.type = str(self.type or "misc")
        self.title = str(self.title or "").strip()
        self.body = str(self.body or "").strip()
        self.priority = str(self.priority or "normal").lower().strip()
        self.category = str(self.category or "general").strip()

        if self.attachments is None:
            self.attachments = []
        elif isinstance(self.attachments, str):
            self.attachments = [self.attachments]
        else:
            self.attachments = [str(x) for x in self.attachments]

    def is_expired(self, now: dt.datetime) -> bool:
        if not self.expires_date:
            return False

        try:
            expiry = dt.datetime.strptime(
                self.expires_date, "%Y-%m-%d"
            ).date()
        except (TypeError, ValueError):
            logger.warning(
                "Invalid expires_date for %r; treating as non-expired.",
                self.title,
            )
            return False

        return expiry < now.date()

    def fingerprint(self) -> str:
        payload = {
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "priority": self.priority,
            "category": self.category,
            "target_audience": self.target_audience,
            "expires_date": self.expires_date,
            "attachments": self.attachments,
        }

        raw = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# PDF backup
# ---------------------------------------------------------------------------

class PDFGenerator:
    def generate(
        self,
        announcements: List[Announcement],
        output_path: Path,
        class_name: str,
    ) -> Path:
        pdf_path = output_path.with_suffix(".pdf")

        try:
            from fpdf import FPDF
            from fpdf.enums import XPos, YPos
        except ImportError:
            markdown_path = output_path.with_suffix(".md")
            markdown_path.write_text(
                self._to_markdown(announcements, class_name),
                encoding="utf-8",
            )
            logger.warning(
                "fpdf2 is not installed; Markdown backup saved: %s",
                markdown_path,
            )
            return markdown_path

        pdf = FPDF()

        # Prefer a local Unicode font, then fall back to a built-in PDF font.
        font_candidates = [
            (
                "DejaVu",
                Path(r"C:\Windows\Fonts\DejaVuSans.ttf"),
                Path(r"C:\Windows\Fonts\DejaVuSans-Bold.ttf"),
                Path(r"C:\Windows\Fonts\DejaVuSans-Oblique.ttf"),
            ),
            (
                "Arial",
                Path(r"C:\Windows\Fonts\arial.ttf"),
                Path(r"C:\Windows\Fonts\arialbd.ttf"),
                Path(r"C:\Windows\Fonts\ariali.ttf"),
            ),
        ]

        pdf_font = "Helvetica"
        unicode_font = False
        for family, regular, bold, italic in font_candidates:
            if regular.is_file() and bold.is_file() and italic.is_file():
                pdf.add_font(family, "", str(regular))
                pdf.add_font(family, "B", str(bold))
                pdf.add_font(family, "I", str(italic))
                pdf_font = family
                unicode_font = True
                break
        else:
            logger.warning(
                "No local Unicode font was found. Using built-in Helvetica for PDF output."
            )

        def pdf_text(value: str) -> str:
            text = str(value or "")
            if unicode_font:
                return text
            return text.encode("latin-1", "replace").decode("latin-1")

        def pdf_multi_cell(height: float, text: str) -> None:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, height, pdf_text(text))

        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_font(pdf_font, "B", 16)
        pdf.cell(
            0,
            10,
            pdf_text(f"{class_name} - Daily Announcement"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="C",
        )

        pdf.set_font(pdf_font, "I", 10)
        pdf.cell(
            0,
            8,
            pdf_text(f"Date: {dt.datetime.now():%A, %B %d, %Y}"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="C",
        )
        pdf.ln(5)

        priority_order = {
            "urgent": 0,
            "high": 1,
            "normal": 2,
            "low": 3,
        }

        for ann in sorted(
            announcements,
            key=lambda x: priority_order.get(x.priority, 2),
        ):
            pdf.set_font(pdf_font, "B", 12)
            pdf.set_text_color(
                *{
                    "urgent": (220, 50, 50),
                    "high": (240, 150, 50),
                    "normal": (50, 100, 200),
                    "low": (100, 100, 100),
                }.get(ann.priority, (50, 100, 200))
            )

            pdf_multi_cell(8, f"[{ann.priority.upper()}] {ann.title}")

            pdf.set_text_color(0, 0, 0)
            pdf.set_font(pdf_font, "", 10)

            for line in ann.body.splitlines() or [""]:
                pdf_multi_cell(5, line)

            if ann.attachments:
                pdf.set_font(pdf_font, "I", 9)
                pdf_multi_cell(5, "Attachments: " + ", ".join(ann.attachments))

            pdf.ln(3)

        pdf.set_y(-15)
        pdf.set_font(pdf_font, "I", 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(
            0,
            5,
            pdf_text("Automated by the Class Announcement Agent"),
            align="C",
        )

        pdf.output(str(pdf_path))
        logger.info("PDF backup saved: %s", pdf_path)
        return pdf_path

    @staticmethod
    def _to_markdown(
        announcements: List[Announcement],
        class_name: str,
    ) -> str:
        lines = [
            f"# {class_name} - Daily Announcement",
            "",
            f"**Date:** {dt.datetime.now():%A, %B %d, %Y}",
            "",
        ]

        for ann in announcements:
            lines += [
                f"## [{ann.priority.upper()}] {ann.title}",
                "",
                ann.body,
                "",
            ]

            if ann.attachments:
                lines += [
                    "**Attachments:** " + ", ".join(ann.attachments),
                    "",
                ]

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Messenger sender
# ---------------------------------------------------------------------------

class FacebookMessengerSender:
    """
    Sends messages through a persistent Brave profile.

    Messenger's DOM is not a stable API. This implementation therefore uses
    several selector fallbacks and refuses to send when the conversation or
    composer cannot be verified.
    """

    def __init__(
        self,
        recipient_name: Optional[str] = None,
        session_dir: Path = SESSION_DIR,
        headless: bool = False,
        send_delay_seconds: float = 2.0,
    ):
        self.recipient_name = (
            recipient_name
            or os.getenv("FB_RECIPIENT")
            or "Teacher"
        ).strip()

        self.session_dir = Path(session_dir)
        self.headless = bool(headless)
        self.send_delay_seconds = max(0.5, float(send_delay_seconds))

    @classmethod
    def from_config(cls, config: Dict[str, Any]):
        messenger = config.get("messenger", {}) or {}

        recipient = (
            messenger.get("recipient_name")
            or config.get("recipient_name")
            or os.getenv("FB_RECIPIENT")
            or "Teacher"
        )

        configured_session = messenger.get("session_dir")
        session_dir = (
            Path(os.path.expandvars(os.path.expanduser(configured_session)))
            if configured_session
            else SESSION_DIR
        )

        return cls(
            recipient_name=recipient,
            session_dir=session_dir,
            headless=messenger.get("headless", False),
            send_delay_seconds=messenger.get(
                "send_delay_seconds",
                2,
            ),
        )

    def send(
        self,
        text: str,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        attachments = attachments or []

        full_message = text.strip()

        if attachments:
            clean_attachments = [
                str(x).strip()
                for x in attachments
                if str(x).strip()
            ]

            if clean_attachments:
                full_message += (
                    "\n\n📎 Attachments:\n"
                    + "\n".join(
                        f"- {x}" for x in clean_attachments
                    )
                )

        queue_file = self._queue_message(full_message)

        try:
            success = self._send_via_brave(full_message)

            if success:
                try:
                    queue_file.unlink(missing_ok=True)
                except OSError:
                    pass

            return success

        except Exception:
            logger.exception(
                "Messenger send failed. Queued message retained: %s",
                queue_file,
            )
            return False

    @staticmethod
    def _queue_message(message: str) -> Path:
        ensure_directories()

        timestamp = dt.datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )
        queue_file = QUEUE_DIR / f"queued_msg_{timestamp}.txt"

        queue_file.write_text(
            message,
            encoding="utf-8",
        )

        logger.info("Message queued: %s", queue_file)
        return queue_file

    def _send_via_brave(self, message: str) -> bool:
        try:
            from playwright.sync_api import (
                TimeoutError as PlaywrightTimeoutError,
                sync_playwright,
            )
        except ImportError:
            logger.error(
                "Playwright is not installed. Run: "
                "python -m pip install playwright"
            )
            return False

        brave_path = find_brave()

        if not brave_path:
            logger.error(
                "Brave executable was not found."
            )
            return False

        self.session_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        with sync_playwright() as p:
            context = None

            try:
                # IMPORTANT: executable_path is the correct Playwright
                # parameter for launching Brave.
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_dir),
                    executable_path=str(brave_path),
                    headless=self.headless,
                    viewport={
                        "width": 1440,
                        "height": 900,
                    },
                    args=[
                        "--disable-blink-features=AutomationControlled",
                    ],
                )

                pages = context.pages
                if pages:
                    page = pages[0]
                else:
                    page = context.new_page()

                page.set_default_timeout(10000)

                logger.info("Opening Messenger...")
                logger.info(f"Initial page URL: {page.url}")

                page.goto(
                    MESSENGER_URL,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                logger.info(f"Messenger navigation completed. Current URL: {page.url}")

                page.wait_for_timeout(3000)

                logger.info(f"Final Messenger URL: {page.url}")

                if self._looks_like_login_page(page):
                    if self.headless:
                        logger.error(
                            "Messenger login is required but headless mode "
                            "is enabled. Run setup first."
                        )
                        return False

                    logger.warning(
                        "Login/verification required. Complete it in Brave."
                    )
                    self._wait_for_manual_login(page)

                self._navigate_to_conversation(page)

                message_box = self._find_message_box(page)

                if message_box is None:
                    logger.error(
                        "Could not locate Messenger message composer."
                    )
                    self._save_debug_screenshot(
                        page,
                        "no_message_box",
                    )
                    return False

                logger.info("Composing message...")
                message_box.click()
                message_box.fill(message)

                # Do not press Enter unless the composer contains exactly the
                # message we intended to send.
                composer_value = normalize_text(
                    self._read_textbox(message_box)
                )

                if composer_value != normalize_text(message):
                    logger.error(
                        "Composer verification failed. Message NOT sent."
                    )
                    self._save_debug_screenshot(
                        page,
                        "composer_verification_failed",
                    )
                    return False

                logger.info("Sending message...")
                message_box.press("Enter")

                time.sleep(self.send_delay_seconds)

                if self._verify_message_sent(
                    page,
                    message,
                ):
                    logger.info(
                        "Messenger delivery verified."
                    )
                    return True

                logger.error(
                    "Delivery could not be verified."
                )
                self._save_debug_screenshot(
                    page,
                    "delivery_verification_failed",
                )
                return False

            except PlaywrightTimeoutError as exc:
                logger.error(
                    "Playwright timeout: %s",
                    exc,
                )

                if context and context.pages:
                    self._save_debug_screenshot(
                        context.pages[0],
                        "playwright_timeout",
                    )

                return False

            except Exception as exc:
                logger.exception(
                    "Brave automation failed: %s",
                    exc,
                )

                if context and context.pages:
                    self._save_debug_screenshot(
                        context.pages[0],
                        "automation_exception",
                    )

                return False

            finally:
                if context:
                    try:
                        context.close()
                    except Exception:
                        pass

    @staticmethod
    def _looks_like_login_page(page) -> bool:
        url = page.url.lower()

        if "login" in url or "checkpoint" in url:
            return True

        selectors = [
            'input[name="email"]',
            'input[name="pass"]',
            'button:has-text("Log in")',
            'button:has-text("Log In")',
            '[role="button"]:has-text("Log in")',
            '[role="button"]:has-text("Log In")',
            
        ]

        for selector in selectors:
            try:
                if page.locator(selector).count() > 0:
                    return True
            except Exception:
                pass

        return False

    def _wait_for_manual_login(self, page) -> None:
        logger.info("=" * 60)
        logger.info("MANUAL FACEBOOK/MESSENGER AUTHENTICATION")
        logger.info("=" * 60)
        logger.info(
            "Complete Facebook login and all verification steps "
            "in the Brave window."
        )
        logger.info(
            "Do NOT close the Brave window."
        )
        logger.info(
            "When Messenger is fully logged in and you can see "
            "your Messenger conversations, return here."
        )

        try:
            input(
                "\nPress ENTER after you have completed "
                "Facebook verification and Messenger is fully loaded..."
            )
        except KeyboardInterrupt:
            raise RuntimeError(
                "Authentication setup was cancelled."
            )

        page.wait_for_timeout(5000)

        logger.info(
            f"Current Messenger URL after manual verification: {page.url}"
        )

        # Give Messenger additional time to finish loading.
        page.wait_for_timeout(5000)

        if self._looks_like_login_page(page):
            logger.error(
                "Messenger still appears to be unauthenticated."
            )
            raise RuntimeError(
                "Messenger authentication was not detected after "
                "manual verification."
            )

        logger.info(
            "Manual authentication confirmation accepted."
        )

    def _find_search_box(self, page):
        selectors = [
            'input[aria-label="Search Messenger"]',
            'input[aria-label*="Search Messenger" i]',
            'input[role="combobox"]',
        ]

        page.wait_for_timeout(2000)

        for selector in selectors:
            try:
                candidates = page.locator(selector)

                for i in range(candidates.count()):
                    candidate = candidates.nth(i)

                    if candidate.is_visible() and candidate.is_enabled():
                        logger.info(
                            f"Messenger search box found using selector: {selector}"
                        )
                        return candidate

            except Exception:
                continue

        logger.warning(
            f"Messenger search box could not be located. Current URL: {page.url}"
        )

        return None

    def _navigate_to_conversation(self, page) -> None:
        target = normalize_text(self.recipient_name)

        if not target:
            raise RuntimeError(
                "Messenger recipient/group name is empty."
            )

        logger.info(
            f"Looking for Messenger conversation: {self.recipient_name}"
        )

        page.wait_for_timeout(3000)

        search_box = self._find_search_box(page)

        if search_box is None:
            try:
                search_button = page.locator(
                    '[aria-label="Search"][role="button"]'
                )

                if (
                    search_button.is_visible()
                    and search_button.is_enabled()
                ):
                    logger.info(
                        "Search input not visible. "
                        "Clicking Messenger Search button..."
                    )

                    search_button.click()
                    page.wait_for_timeout(1000)

                    search_box = self._find_search_box(page)

            except Exception as exc:
                logger.debug(
                    f"Could not activate Messenger Search button: {exc}"
                )

        if search_box is None:
            raise RuntimeError(
                "Messenger search box could not be located."
            )

        logger.info(
            f"Searching Messenger for: {self.recipient_name}"
        )

        search_box.click()
        search_box.fill(self.recipient_name)

        page.wait_for_timeout(2500)

        exact_text = page.get_by_text(
            self.recipient_name,
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

                if (
                    clickable.count() > 0
                    and clickable.is_visible()
                ):
                    selected = clickable
                    break

                selected = element

            except Exception:
                continue

        if selected is None:
            raise RuntimeError(
                f"Could not locate conversation "
                f"'{self.recipient_name}' in search results."
            )

        logger.info(
            "Messenger conversation result found."
        )

        try:
            selected.click()

        except Exception:
            logger.info(
                "Normal Messenger click was intercepted. "
                "Using DOM click fallback..."
            )

            selected.evaluate(
                "(element) => element.click()"
            )

        page.wait_for_timeout(3000)

        body_text = normalize_text(
            page.locator("body").inner_text()
        )

        if (
            normalize_text(self.recipient_name).casefold()
            not in body_text.casefold()
        ):
            raise RuntimeError(
                f"Conversation '{self.recipient_name}' "
                "could not be verified."
            )

        logger.info(
            f"Conversation verified: {self.recipient_name}"
        )

    def _find_message_box(self, page):
        selectors = [
            '[contenteditable="true"][aria-label*="Write to" i]',
            '[contenteditable="true"]',
            '[role="textbox"]',
            'textarea',
        ]

        for selector in selectors:
            try:
                candidates = page.locator(selector)

                for i in range(candidates.count()):
                    candidate = candidates.nth(i)

                    if (
                        candidate.is_visible()
                        and candidate.is_enabled()
                    ):
                        logger.info(
                            f"Messenger composer found using selector: {selector}"
                        )
                        return candidate

            except Exception:
                continue

        return None

    @staticmethod
    def _read_textbox(locator) -> str:
        try:
            return locator.input_value()
        except Exception:
            pass

        try:
            return locator.inner_text()
        except Exception:
            return ""

    def _verify_message_sent(
        self,
        page,
        message: str,
    ) -> bool:
        """
        Conservative post-send verification.

        A message is considered verified only when:
          1. the composer is empty, and
          2. the exact normalized message text is found in the
             currently open conversation area.

        The check is repeated for up to 15 seconds to allow Messenger
        to update the conversation UI.
        """
        expected = normalize_text(message)

        for _ in range(15):
            page.wait_for_timeout(1000)

            try:
                # --------------------------------------------------
                # 1. Verify that the composer is empty after sending.
                # --------------------------------------------------
                composer = self._find_message_box(page)

                composer_empty = True

                if composer is not None:
                    composer_empty = (
                        normalize_text(
                            self._read_textbox(composer)
                        )
                        == ""
                    )

                if not composer_empty:
                    continue

                # --------------------------------------------------
                # 2. Verify the exact message appears in the
                # currently open conversation.
                # --------------------------------------------------
                message_matches = page.get_by_text(
                    message,
                    exact=True,
                )

                visible_matches = 0

                for i in range(message_matches.count()):
                    try:
                        match = message_matches.nth(i)

                        if match.is_visible():
                            visible_matches += 1

                    except Exception:
                        continue

                if visible_matches > 0:
                    logger.info(
                        "Exact sent message text found in the "
                        "currently open Messenger conversation."
                    )
                    return True

            except Exception as exc:
                logger.debug(
                    f"Post-send verification attempt failed: {exc}"
                )

        return False

    @staticmethod
    def _save_debug_screenshot(
        page,
        label: str,
    ) -> None:
        try:
            path = LOG_DIR / (
                f"{dt.datetime.now():%Y%m%d_%H%M%S}_{label}.png"
            )

            page.screenshot(
                path=str(path),
                full_page=True,
            )

            logger.info(
                "Debug screenshot saved: %s",
                path,
            )
        except Exception as exc:
            logger.debug(
                "Could not save screenshot: %s",
                exc,
            )


# ---------------------------------------------------------------------------
# Main agent
# ---------------------------------------------------------------------------

class AnnouncementAgent:
    def __init__(self):
        ensure_directories()

        self.pdf_gen = PDFGenerator()

        data = self.read_input()
        self.messenger = FacebookMessengerSender.from_config(data)

    def read_input(self) -> Dict[str, Any]:
        ensure_directories()

        if not ANNOUNCEMENTS_FILE.exists():
            template = {
                "class_name": "BSIT 1A",
                "recipient_name": "YOUR MESSENGER GROUP NAME",
                "messenger": {
                    "recipient_name": "YOUR MESSENGER GROUP NAME",
                    "headless": False,
                    "send_delay_seconds": 2,
                },
                "send_time": {
                    "hour": DEFAULT_HOUR,
                    "minute": DEFAULT_MINUTE,
                },
                "duplicate_window_hours": 24,
                "announcements": [
                    {
                        "type": "reminder",
                        "title": "Example Reminder",
                        "body": (
                            "Replace this announcement with your actual "
                            "class reminder."
                        ),
                        "priority": "normal",
                        "category": "general",
                        "target_audience": "all",
                        "expires_date": (
                            dt.datetime.now()
                            + dt.timedelta(days=1)
                        ).strftime("%Y-%m-%d"),
                        "attachments": [],
                    }
                ],
            }

            ANNOUNCEMENTS_FILE.write_text(
                yaml.safe_dump(
                    template,
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            logger.info(
                "Created YAML template: %s",
                ANNOUNCEMENTS_FILE,
            )

            return template

        try:
            data = yaml.safe_load(
                ANNOUNCEMENTS_FILE.read_text(
                    encoding="utf-8"
                )
            )
        except yaml.YAMLError as exc:
            raise RuntimeError(
                f"Invalid YAML: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError(
                "daily_input.yaml must contain a YAML object/mapping."
            )

        return data

    def format_announcements(
        self,
        data: Dict[str, Any],
    ) -> List[Announcement]:
        result = []
        now = dt.datetime.now()

        for index, raw in enumerate(
            data.get("announcements", [])
        ):
            if not isinstance(raw, dict):
                logger.warning(
                    "Skipping announcement #%d: invalid object.",
                    index + 1,
                )
                continue

            allowed = {
                "type",
                "title",
                "body",
                "priority",
                "category",
                "target_audience",
                "expires_date",
                "attachments",
            }

            clean = {
                key: value
                for key, value in raw.items()
                if key in allowed
            }

            announcement = Announcement(**clean)

            if not announcement.title and not announcement.body:
                logger.warning(
                    "Skipping empty announcement #%d.",
                    index + 1,
                )
                continue

            if announcement.is_expired(now):
                logger.info(
                    "Skipping expired announcement: %s",
                    announcement.title,
                )
                continue

            result.append(announcement)

        return result

    @staticmethod
    def format_for_messenger(
        announcements: List[Announcement],
        class_name: str,
    ) -> str:
        lines = [
            f"📢 {class_name} - Daily Announcement",
            f"📅 {dt.datetime.now():%A, %B %d, %Y}",
            "",
        ]

        priority_order = {
            "urgent": 0,
            "high": 1,
            "normal": 2,
            "low": 3,
        }

        tags = {
            "urgent": "🔴 URGENT",
            "high": "⚠️ HIGH",
            "normal": "📌 NORMAL",
            "low": "ℹ️ LOW",
        }

        for ann in sorted(
            announcements,
            key=lambda x: priority_order.get(
                x.priority,
                2,
            ),
        ):
            lines.extend(
                [
                    f"{tags.get(ann.priority, '📍')} {ann.title}",
                    ann.body,
                    "",
                ]
            )

        return "\n".join(lines).strip()

    def get_cache(self) -> Dict[str, Any]:
        if not CACHE_FILE.exists():
            return {"sent": []}

        try:
            data = json.loads(
                CACHE_FILE.read_text(
                    encoding="utf-8"
                )
            )

            if not isinstance(data, dict):
                return {"sent": []}

            if not isinstance(data.get("sent"), list):
                data["sent"] = []

            return data

        except (
            OSError,
            json.JSONDecodeError,
        ):
            logger.warning(
                "Cache is unreadable. Starting with empty cache."
            )
            return {"sent": []}

    @staticmethod
    def is_duplicate(
        announcement: Announcement,
        cache: Dict[str, Any],
        hours: int,
    ) -> bool:
        fingerprint = announcement.fingerprint()
        cutoff = (
            dt.datetime.now()
            - dt.timedelta(hours=hours)
        )

        for item in cache.get("sent", []):
            if not isinstance(item, dict):
                continue

            if item.get("fingerprint") != fingerprint:
                continue

            try:
                sent_at = dt.datetime.fromisoformat(
                    str(item.get("timestamp"))
                )
            except (
                ValueError,
                TypeError,
            ):
                continue

            if sent_at >= cutoff:
                return True

        return False

    def update_cache(
        self,
        cache: Dict[str, Any],
        announcements: List[Announcement],
    ) -> None:
        timestamp = dt.datetime.now().isoformat(
            timespec="seconds"
        )

        cache.setdefault("sent", [])

        for announcement in announcements:
            cache["sent"].append(
                {
                    "fingerprint": announcement.fingerprint(),
                    "title": announcement.title,
                    "body": announcement.body,
                    "timestamp": timestamp,
                }
            )

        cache["sent"] = cache["sent"][-200:]

        CACHE_FILE.write_text(
            json.dumps(
                cache,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def run(self, dry_run: bool = False):
        logger.info("=" * 60)
        logger.info("Running Class Announcement Agent")
        logger.info("=" * 60)

        data = self.read_input()
        announcements = self.format_announcements(data)

        if not announcements:
            logger.info(
                "No valid announcements to send."
            )
            return None

        class_name = str(
            data.get("class_name", "Class")
        ).strip() or "Class"

        cache = self.get_cache()

        duplicate_window = int(
            data.get(
                "duplicate_window_hours",
                DEFAULT_DUPLICATE_WINDOW_HOURS,
            )
        )

        new_announcements = [
            x
            for x in announcements
            if not self.is_duplicate(
                x,
                cache,
                duplicate_window,
            )
        ]

        if not new_announcements:
            logger.info(
                "All announcements are duplicates."
            )
            return None

        message = self.format_for_messenger(
            new_announcements,
            class_name,
        )

        attachments = []
        for announcement in new_announcements:
            attachments.extend(
                announcement.attachments
            )

        timestamp = dt.datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup = self.pdf_gen.generate(
            new_announcements,
            OUTPUT_DIR / f"announcement_{timestamp}",
            class_name,
        )

        if dry_run:
            logger.info(
                "DRY RUN: Messenger will NOT be contacted."
            )

            print("\n" + "=" * 70)
            print(
                "DRY RUN — NO MESSENGER MESSAGE WAS SENT"
            )
            print("=" * 70)
            print(message)
            print("=" * 70)
            print(f"Backup: {backup}")

            return {
                "announcements_sent": 0,
                "announcements_ready": len(
                    new_announcements
                ),
                "backup_path": str(backup),
                "send_failed": False,
                "dry_run": True,
            }

        logger.info(
            "Sending %d announcement(s)...",
            len(new_announcements),
        )

        success = self.messenger.send(
            message,
            attachments=attachments[:10],
        )

        if not success:
            logger.error(
                "Send failed. Cache will NOT be updated."
            )

            return {
                "announcements_sent": 0,
                "announcements_ready": len(
                    new_announcements
                ),
                "backup_path": str(backup),
                "send_failed": True,
                "dry_run": False,
            }

        # Critical: only record the announcements after the sender confirms
        # the message appeared in Messenger.
        self.update_cache(
            cache,
            new_announcements,
        )

        logger.info(
            "Announcement cycle completed successfully."
        )

        return {
            "announcements_sent": len(
                new_announcements
            ),
            "announcements_ready": len(
                new_announcements
            ),
            "backup_path": str(backup),
            "send_failed": False,
            "dry_run": False,
        }

    def setup(self) -> bool:
        """
        Establish the persistent Brave session.

        Setup never sends a class announcement.
        """
        ensure_directories()

        brave = find_brave()

        if not brave:
            logger.error(
                "Brave was not found."
            )
            return False

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.info(
                "Installing Playwright..."
            )
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "playwright",
                ]
            )
            from playwright.sync_api import sync_playwright

        logger.info(
            "Launching Brave with persistent session..."
        )

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(
                    self.messenger.session_dir
                ),
                executable_path=str(brave),
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
                page = (
                    context.pages[0]
                    if context.pages
                    else context.new_page()
                )

                page.set_default_timeout(10000)

                page.goto(
                    MESSENGER_URL,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                page.wait_for_timeout(3000)

                if self.messenger._looks_like_login_page(
                    page
                ):
                    logger.info(
                        "Please complete Facebook login/verification "
                        "in the Brave window."
                    )

                    self.messenger._wait_for_manual_login(
                        page
                    )

                page.wait_for_timeout(3000)

                if self.messenger._looks_like_login_page(
                    page
                ):
                    logger.error(
                        "Messenger is still not authenticated."
                    )
                    return False

                logger.info(
                    "Setup successful."
                )
                logger.info(
                    "Persistent session: %s",
                    self.messenger.session_dir,
                )

                return True

            finally:
                context.close()


# ---------------------------------------------------------------------------
# Windows Task Scheduler
# ---------------------------------------------------------------------------

def setup_scheduled_task(
    task_name: str = "Class Announcement Agent",
) -> None:
    if os.name != "nt":
        logger.error(
            "This Task Scheduler helper is for Windows."
        )
        return

    agent = AnnouncementAgent()
    data = agent.read_input()

    send_time = data.get(
        "send_time",
        {},
    ) or {}

    try:
        hour = int(
            send_time.get(
                "hour",
                DEFAULT_HOUR,
            )
        )
        minute = int(
            send_time.get(
                "minute",
                DEFAULT_MINUTE,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        hour = DEFAULT_HOUR
        minute = DEFAULT_MINUTE

    if not (
        0 <= hour <= 23
        and 0 <= minute <= 59
    ):
        raise ValueError(
            f"Invalid send_time: "
            f"{hour:02d}:{minute:02d}"
        )

    script = Path(__file__).resolve()

    # Use the exact Python executable running this agent.
    task_command = (
        f'"{sys.executable}" "{script}" run'
    )

    command = [
        "schtasks",
        "/Create",
        "/TN",
        task_name,
        "/SC",
        "DAILY",
        "/ST",
        f"{hour:02d}:{minute:02d}",
        "/TR",
        task_command,
        "/F",
    ]

    logger.info(
        "Creating Windows scheduled task '%s' "
        "for %02d:%02d.",
        task_name,
        hour,
        minute,
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Task Scheduler failed:\n"
            + (result.stderr or result.stdout)
        )

    logger.info(
        "Windows scheduled task created successfully."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Autonomous Class Announcement Agent"
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=(
            "run",
            "test",
            "setup",
            "schedule",
        ),
        default="run",
    )

    parser.add_argument(
        "--task-name",
        default="Class Announcement Agent",
    )

    return parser.parse_args()


def main() -> int:
    ensure_directories()

    args = parse_args()

    try:
        agent = AnnouncementAgent()

        if args.command == "setup":
            if agent.setup():
                print(
                    "\nSetup completed successfully."
                )
                print(
                    "No class announcement was sent."
                )
                print(
                    "\nNext:"
                    "\n  python "
                    "class_announcement_agent_fixed.py schedule"
                )
                return 0

            return 1

        if args.command == "schedule":
            setup_scheduled_task(
                args.task_name
            )
            return 0

        if args.command == "test":
            result = agent.run(
                dry_run=True
            )
            return 0 if result else 0

        result = agent.run(
            dry_run=False
        )

        if not result:
            print(
                "No new announcements to send."
            )
            return 0

        if result.get("send_failed"):
            print(
                "Messenger delivery failed. "
                "The announcement was NOT marked as sent."
            )
            print(
                f"Backup: {result['backup_path']}"
            )
            return 1

        print(
            f"Successfully sent "
            f"{result['announcements_sent']} announcement(s)."
        )
        print(
            f"Backup: {result['backup_path']}"
        )
        return 0

    except KeyboardInterrupt:
        logger.warning(
            "Interrupted by user."
        )
        return 130

    except Exception:
        logger.exception(
            "Fatal agent error."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
