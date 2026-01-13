#!/usr/bin/env python3
"""
Deribit API Documentation Change Monitor with Telegram Notifications

This script scrapes the Deribit API documentation website and tracks changes
by crawling articles, API reference, and subscription pages.

Automatically sends Telegram notifications when changes are detected.
"""

from bs4 import BeautifulSoup
from typing import Dict, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime
import time
from .base_monitor import BaseDocMonitor


class DeribitDocMonitor(BaseDocMonitor):
    """Monitor for Deribit documentation across articles, API reference, and subscriptions."""

    # URL patterns to monitor
    SECTIONS_TO_MONITOR = [
        "articles/",
        "api-reference/",
        "subscriptions/",
    ]

    def __init__(
        self,
        storage_file: str = "state/deribit_docs_state.json",
        telegram_bot_token: str = None,
        telegram_chat_id: str = None,
        max_pages: int = 1000,
    ):
        """
        Initialize the Deribit documentation monitor.

        Args:
            storage_file: Path to JSON file storing previous state
            telegram_bot_token: Telegram bot token from @BotFather
            telegram_chat_id: Telegram chat ID to send messages to
            max_pages: Maximum number of pages to discover
        """
        super().__init__(
            exchange_name="Deribit",
            storage_file=storage_file,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
        )
        self.base_url = "https://docs.deribit.com"
        self.max_pages = max_pages

    def _is_valid_doc_page(self, url: str) -> bool:
        """
        Check if a URL is a valid documentation page to monitor.

        Args:
            url: URL to check

        Returns:
            True if the URL matches one of our monitoring patterns
        """
        parsed = urlparse(url)
        path = parsed.path

        # Check if the path starts with any of our monitored sections
        for section in self.SECTIONS_TO_MONITOR:
            if f"/{section}" in path:
                return True

        return False

    def _discover_links_from_page(
        self, url: str, discovered: Dict[str, str], visited: set
    ):
        """
        Recursively discover links from a page.

        Args:
            url: URL to fetch
            discovered: Dictionary to populate with discovered pages
            visited: Set of already visited URLs to avoid loops
        """
        if url in visited or len(discovered) >= self.max_pages:
            return

        visited.add(url)

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Get page title
            title_elem = soup.find("h1")
            title = (
                title_elem.get_text(strip=True)
                if title_elem
                else url.split("/")[-1]
            )

            # Add current page if it's a valid doc page
            if self._is_valid_doc_page(url):
                # Use the path as the key (remove base URL)
                page_path = url.replace(self.base_url, "").strip("/")
                if page_path and page_path not in discovered.values():
                    discovered[url] = title
                    self.logger.debug(f"  Found: {title} ({page_path})")

            # Find all links
            all_links = soup.find_all("a", href=True)

            for link in all_links:
                href = link.get("href", "")

                # Skip external links, anchors, and empty hrefs
                if not href or href.startswith("http") and not href.startswith(self.base_url):
                    continue

                # Convert to absolute URL
                absolute_url = urljoin(url, href)

                # Remove fragments and query params
                parsed = urlparse(absolute_url)
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

                # Check if this is a valid doc page we should follow
                if (
                    clean_url not in visited
                    and self._is_valid_doc_page(clean_url)
                    and len(discovered) < self.max_pages
                ):
                    self._discover_links_from_page(clean_url, discovered, visited)

            time.sleep(0.3)  # Rate limiting

        except Exception as e:
            self.logger.error(f"  Error fetching {url}: {e}")

    def discover_sections(self) -> Dict[str, str]:
        """
        Discover documentation pages by crawling the documentation site.

        Returns:
            Dict of url -> page_title
        """
        self.logger.info(f"Discovering documentation pages from {self.base_url}...")

        discovered = {}
        visited = set()

        # Start by discovering from each main section
        for section in self.SECTIONS_TO_MONITOR:
            section_url = f"{self.base_url}/{section}"
            self.logger.info(f"Crawling section: {section}")
            self._discover_links_from_page(section_url, discovered, visited)

        self.logger.info(f"Discovered {len(discovered)} total pages to monitor")

        return discovered

    def fetch_section_content(self, page_url: str) -> Tuple[str, str]:
        """
        Fetch a specific page's content and return its content and hash.

        Args:
            page_url: The page URL

        Returns:
            Tuple of (content, hash)
        """
        try:
            response = self.session.get(page_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove non-content elements
            for element in soup(
                ["script", "style", "nav", "footer", "header", "aside"]
            ):
                element.decompose()

            # Remove navigation menus and sidebars
            for nav_class in ["navbar", "menu", "sidebar", "toc", "navigation"]:
                for element in soup.find_all(
                    class_=lambda x: x and nav_class in x.lower()
                ):
                    element.decompose()

            # Get main content - try different content containers
            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", class_=lambda x: x and "content" in x.lower())
                or soup
            )

            content = main_content.get_text(separator="\n", strip=True)
            content_hash = self.get_page_hash(content)

            return content, content_hash

        except Exception as e:
            self.logger.error(f"  Error fetching page {page_url}: {e}")
            return "", ""

    def get_section_url(self, page_url: str) -> str:
        """
        Get the URL for a specific page.

        Args:
            page_url: The page URL

        Returns:
            The URL (same as page_url)
        """
        return page_url

    def _get_category_label(self, page_url: str) -> str:
        """
        Extract category label from page URL.

        Args:
            page_url: The page URL

        Returns:
            Category label (e.g., "ARTICLES", "API", "SUBSCRIPTIONS")
        """
        if "/articles/" in page_url:
            return "ARTICLES"
        elif "/api-reference/" in page_url:
            return "API"
        elif "/subscriptions/" in page_url:
            return "SUBSCRIPTIONS"
        else:
            return "OTHER"

    def send_telegram(self, changes: Dict):
        """
        Send Telegram notification if changes were detected.

        Overrides base class to add category labels to page names.

        Args:
            changes: Dictionary with change information
        """
        total_changes = (
            len(changes["new_sections"])
            + len(changes["modified_sections"])
            + len(changes["deleted_sections"])
        )

        if (
            total_changes == 0
            or not self.telegram_bot_token
            or not self.telegram_chat_id
        ):
            return

        # Build message
        message = f"🔔 *{self.exchange_name} Documentation Changed*\n\n"
        message += f"📊 Total Changes: *{total_changes}*\n"
        message += f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"

        if changes["new_sections"]:
            message += f"📄 *NEW PAGES ({len(changes['new_sections'])})*:\n"
            for section in changes["new_sections"][:10]:  # Limit to 10
                category = self._get_category_label(section["id"])
                message += f"  • [{category}] {section['title']}\n"
                section_url = self.get_section_url(section["id"])
                message += f"    [View]({section_url})\n"
            if len(changes["new_sections"]) > 10:
                message += f"  ... and {len(changes['new_sections']) - 10} more\n"
            message += "\n"

        if changes["modified_sections"]:
            message += f"✏️ *MODIFIED PAGES ({len(changes['modified_sections'])})*:\n"
            for section in changes["modified_sections"][:10]:  # Limit to 10
                category = self._get_category_label(section["id"])
                message += f"  • [{category}] {section['title']}\n"
                section_url = self.get_section_url(section["id"])
                message += f"    [View]({section_url})\n"
            if len(changes["modified_sections"]) > 10:
                message += f"  ... and {len(changes['modified_sections']) - 10} more\n"
            message += "\n"

        if changes["deleted_sections"]:
            message += f"🗑️ *DELETED PAGES ({len(changes['deleted_sections'])})*:\n"
            for section in changes["deleted_sections"][:10]:
                category = self._get_category_label(section["id"])
                message += f"  • [{category}] {section['title']}\n"
            if len(changes["deleted_sections"]) > 10:
                message += f"  ... and {len(changes['deleted_sections']) - 10} more\n"

        # Add footer
        message += self.get_telegram_footer()

        # Send via Telegram
        try:
            import requests

            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            self.logger.info("Telegram notification sent successfully")
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {e}")

    def print_summary(self, changes: Dict):
        """
        Print a summary of changes.

        Overrides base class to add category labels to page names.
        """
        self.logger.info("=" * 70)
        self.logger.info("CHANGE SUMMARY")
        self.logger.info("=" * 70)

        if changes["new_sections"]:
            self.logger.info(f"📄 NEW PAGES ({len(changes['new_sections'])}):")
            for section in changes["new_sections"]:
                category = self._get_category_label(section["id"])
                self.logger.info(f"  + [{category}] {section['title']}")
                # Show partial URL for readability
                short_url = section["id"].replace(self.base_url, "")
                self.logger.info(f"    Path: {short_url}")

        if changes["modified_sections"]:
            self.logger.info(f"✏️  MODIFIED PAGES ({len(changes['modified_sections'])}):")
            for section in changes["modified_sections"]:
                category = self._get_category_label(section["id"])
                self.logger.info(f"  ~ [{category}] {section['title']}")
                short_url = section["id"].replace(self.base_url, "")
                self.logger.info(f"    Path: {short_url}")
                self.logger.info(f"    Old hash: {section['old_hash'][:16]}...")
                self.logger.info(f"    New hash: {section['new_hash'][:16]}...")

        if changes["deleted_sections"]:
            self.logger.info(f"🗑️  DELETED PAGES ({len(changes['deleted_sections'])}):")
            for section in changes["deleted_sections"]:
                category = self._get_category_label(section["id"])
                self.logger.info(f"  - [{category}] {section['title']}")
                short_url = section["id"].replace(self.base_url, "")
                self.logger.info(f"    Path: {short_url}")

        self.logger.info(f"✓ UNCHANGED PAGES: {len(changes['unchanged_sections'])}")

        total_changes = (
            len(changes["new_sections"])
            + len(changes["modified_sections"])
            + len(changes["deleted_sections"])
        )

        if total_changes == 0:
            self.logger.info("✅ No changes detected!")
        else:
            self.logger.warning(f"⚠️  Total changes: {total_changes}")

        # Use the base class's print_summary_footer method
        self.print_summary_footer()

    def get_telegram_footer(self) -> str:
        """Get the footer for Telegram messages."""
        return f"\n📚 Documentation: [Deribit Docs]({self.base_url})"

    def print_summary_footer(self):
        """Print footer for summary."""
        self.logger.info("View full documentation at:")
        self.logger.info(f"  Deribit: {self.base_url}")


def main():
    """Main execution function."""
    parser = BaseDocMonitor.create_argument_parser(
        exchange_name="Deribit", default_storage_file="state/deribit_docs_state.json"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1000,
        help="Maximum number of pages to discover (default: 1000)",
    )
    args = parser.parse_args()

    # Get Telegram credentials
    telegram_token, telegram_chat_id = BaseDocMonitor.get_telegram_credentials(args)

    # Create monitor
    monitor = DeribitDocMonitor(
        storage_file=args.storage_file,
        telegram_bot_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        max_pages=args.max_pages,
    )

    # Check for changes
    changes = monitor.check_for_changes(save_content=args.save_content)

    # Print summary
    monitor.print_summary(changes)

    # Send Telegram notification if changes detected
    monitor.send_telegram(changes)


if __name__ == "__main__":
    main()
