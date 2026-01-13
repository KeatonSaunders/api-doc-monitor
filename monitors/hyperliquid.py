#!/usr/bin/env python3
"""
Hyperliquid API Documentation Change Monitor with Telegram Notifications

This script monitors Hyperliquid API documentation (GitBook) and tracks changes
by storing page hashes for comparison.

Automatically sends Telegram notifications when changes are detected.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Tuple
from .base_monitor import BaseDocMonitor


class HyperliquidDocMonitor(BaseDocMonitor):
    """Monitor for Hyperliquid GitBook documentation."""

    # Define sections to monitor (parent paths)
    SECTIONS_TO_MONITOR = [
        "for-developers/api",  # API Documentation
        "trading",  # Trading Documentation
        "hypercore",  # HyperCore Documentation
        "hyperliquid-improvement-proposals-hips",  # Hyperliquid Improvement Proposals
    ]

    def __init__(
        self,
        storage_file: str = "state/hyperliquid_docs_state.json",
        telegram_bot_token: str = None,
        telegram_chat_id: str = None,
        base_url: str = "https://hyperliquid.gitbook.io/hyperliquid-docs",
    ):
        """
        Initialize the documentation monitor.

        Args:
            storage_file: Path to JSON file storing previous state
            telegram_bot_token: Telegram bot token from @BotFather
            telegram_chat_id: Telegram chat ID to send messages to
            base_url: Base URL for the documentation
        """
        super().__init__(
            exchange_name="Hyperliquid",
            storage_file=storage_file,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
        )

        self.base_url = base_url

    def _discover_links_from_page(
        self, url: str, sections: Dict[str, str], visited: set
    ):
        """
        Recursively discover links from a page.

        Args:
            url: URL to fetch
            sections: Dictionary to populate with discovered sections
            visited: Set of already visited URLs to avoid loops
        """
        if url in visited:
            return

        visited.add(url)

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            all_links = soup.find_all("a", href=True)

            for link in all_links:
                href = link.get("href", "")

                # Skip external links, anchors, and empty hrefs
                if not href or href.startswith("http") or href.startswith("#"):
                    continue

                # Normalize the path
                path = href.lstrip("/")

                # Remove the base "hyperliquid-docs/" prefix if present
                if path.startswith("hyperliquid-docs/"):
                    path = path[len("hyperliquid-docs/") :]

                # Check if this path is under one of our monitored sections
                is_monitored = False
                for section in self.SECTIONS_TO_MONITOR:
                    if path.startswith(section):
                        is_monitored = True
                        break

                if not is_monitored:
                    continue

                # Build full URL
                full_url = f"{self.base_url}/{path}"

                # Skip if already added
                if full_url in sections:
                    continue

                # Get the link text as the title
                title = link.get_text(strip=True)

                # Skip empty titles or overly long ones
                if not title or len(title) > 100:
                    continue

                sections[full_url] = title
                self.logger.debug(f"  Found: {title} ({path})")

        except Exception as e:
            self.logger.error(f"  Error fetching {url}: {e}")

    def discover_sections(self) -> Dict[str, str]:
        """
        Discover documentation pages to monitor by scraping the GitBook navigation.

        Returns:
            Dict of page_url -> page_title
        """
        self.logger.info(f"Discovering documentation pages from {self.base_url}...")

        sections = {}
        visited = set()

        try:
            # Start by discovering from the main page
            self._discover_links_from_page(self.base_url, sections, visited)

            # Then visit each monitored section to find child pages
            for section_path in self.SECTIONS_TO_MONITOR:
                section_url = f"{self.base_url}/{section_path}"
                self.logger.info(f"Crawling section: {section_path}")
                self._discover_links_from_page(section_url, sections, visited)

            self.logger.info(f"Discovered {len(sections)} total pages to monitor")

        except Exception as e:
            self.logger.error(f"  Error discovering sections: {e}")
            self.logger.warning("  Falling back to empty section list")

        return sections

    def fetch_section_content(self, page_url: str) -> Tuple[str, str]:
        """
        Fetch a specific page's content and return its content and hash.

        Args:
            page_url: The full page URL

        Returns:
            Tuple of (content, hash)
        """
        url = page_url

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # GitBook typically uses specific containers for content
            # Look for the main content area
            content_area = (
                soup.find("div", class_="markdown-body")
                or soup.find("article")
                or soup.find("main")
                or soup.find("div", {"role": "main"})
            )

            if not content_area:
                # Fallback to body if no specific content area found
                content_area = soup.find("body")

            if not content_area:
                return "", ""

            # Extract text content, excluding scripts and styles
            for script in content_area(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get text content
            content = content_area.get_text(separator="\n", strip=True)
            content_hash = self.get_page_hash(content)

            return content, content_hash

        except Exception as e:
            self.logger.error(f"  Error fetching page {url}: {e}")
            return "", ""

    def get_section_url(self, page_url: str) -> str:
        """
        Get the URL for a specific page.

        Args:
            page_url: The full page URL

        Returns:
            The URL (same as page_url)
        """
        return page_url

    def get_telegram_footer(self) -> str:
        """
        Get the footer for Telegram messages with documentation links.

        Returns:
            Footer string with documentation links
        """
        return f"\n📚 Documentation: [Hyperliquid Docs]({self.base_url})"

    def print_summary_footer(self):
        """Print footer for summary with documentation URLs."""
        self.logger.info("View documentation at:")
        self.logger.info(f"  Hyperliquid: {self.base_url}")

    def _get_category_label(self, page_url: str) -> str:
        """
        Extract category label from page URL.

        Args:
            page_url: The full page URL

        Returns:
            Category label (e.g., "API", "TRADING", "HYPERCORE")
        """
        if "/for-developers/api" in page_url:
            return "API"
        elif "/trading" in page_url:
            return "TRADING"
        elif "/hypercore" in page_url:
            return "HYPERCORE"
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
                message += f"    [View]({section['id']})\n"
            if len(changes["new_sections"]) > 10:
                message += f"  ... and {len(changes['new_sections']) - 10} more\n"
            message += "\n"

        if changes["modified_sections"]:
            message += f"✏️ *MODIFIED PAGES ({len(changes['modified_sections'])})*:\n"
            for section in changes["modified_sections"][:10]:  # Limit to 10
                category = self._get_category_label(section["id"])
                message += f"  • [{category}] {section['title']}\n"
                message += f"    [View]({section['id']})\n"
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
                self.logger.info(f"    URL: {section['id']}")

        if changes["modified_sections"]:
            self.logger.info(f"✏️  MODIFIED PAGES ({len(changes['modified_sections'])}):")
            for section in changes["modified_sections"]:
                category = self._get_category_label(section["id"])
                self.logger.info(f"  ~ [{category}] {section['title']}")
                self.logger.info(f"    URL: {section['id']}")
                self.logger.info(f"    Old hash: {section['old_hash'][:16]}...")
                self.logger.info(f"    New hash: {section['new_hash'][:16]}...")

        if changes["deleted_sections"]:
            self.logger.info(f"🗑️  DELETED PAGES ({len(changes['deleted_sections'])}):")
            for section in changes["deleted_sections"]:
                category = self._get_category_label(section["id"])
                self.logger.info(f"  - [{category}] {section['title']}")
                self.logger.info(f"    URL: {section['id']}")

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


def main():
    """Main execution function."""
    # Create argument parser using base class helper
    parser = BaseDocMonitor.create_argument_parser(
        exchange_name="Hyperliquid",
        default_storage_file="state/hyperliquid_docs_state.json",
    )

    args = parser.parse_args()

    # Get Telegram credentials using base class helper
    telegram_token, telegram_chat_id = BaseDocMonitor.get_telegram_credentials(args)

    # Create monitor instance
    monitor = HyperliquidDocMonitor(
        storage_file=args.storage_file,
        telegram_bot_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
    )

    # Check for changes
    changes = monitor.check_for_changes(save_content=args.save_content)

    # Print summary
    monitor.print_summary(changes)

    # Send Telegram notification if changes detected
    monitor.send_telegram(changes)


if __name__ == "__main__":
    main()
