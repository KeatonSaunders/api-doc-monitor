#!/usr/bin/env python3
"""
Coinbase CDP Documentation Change Monitor with Telegram Notifications

This script monitors Coinbase CDP documentation (Exchange, International Exchange,
Prime, and Derivatives) and tracks changes by storing page hashes for comparison.

Automatically sends Telegram notifications when changes are detected.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Tuple
from .base_monitor import BaseDocMonitor


class CoinbaseDocMonitor(BaseDocMonitor):
    def __init__(
        self,
        storage_file: str = "state/coinbase_docs_state.json",
        telegram_bot_token: str = None,
        telegram_chat_id: str = None,
    ):
        """
        Initialize the documentation monitor.

        Args:
            storage_file: Path to JSON file storing previous state
            telegram_bot_token: Telegram bot token from @BotFather
            telegram_chat_id: Telegram chat ID to send messages to
        """
        super().__init__(
            exchange_name="Coinbase",
            storage_file=storage_file,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
        )

        # Monitor multiple Coinbase documentation pages
        self.urls = {
            "exchange_upcoming": {
                "url": "https://docs.cdp.coinbase.com/exchange/changes/upcoming-changes",
                "title": "Exchange Upcoming Changes"
            },
            "intl_exchange_upcoming": {
                "url": "https://docs.cdp.coinbase.com/international-exchange/changes/upcoming-changes",
                "title": "International Exchange Upcoming Changes"
            },
            "prime_upcoming": {
                "url": "https://docs.cdp.coinbase.com/prime/changes/upcoming-changes",
                "title": "Prime Upcoming Changes"
            },
            "derivatives_changelog": {
                "url": "https://docs.cdp.coinbase.com/derivatives/changes/changelog",
                "title": "Derivatives Changelog"
            }
        }

    def discover_sections(self) -> Dict[str, str]:
        """
        Discover sections to monitor. Returns all configured Coinbase documentation pages.

        Returns:
            Dict of url -> section_title
        """
        self.logger.info(f"Setting up monitoring for Coinbase documentation pages...")

        sections = {}
        for page_type, page_info in self.urls.items():
            # Use full URL as the key
            sections[page_info["url"]] = page_info["title"]
            self.logger.info(f"  Monitoring: {page_info['title']}")

        return sections

    def fetch_section_content(self, section_id: str) -> Tuple[str, str]:
        """
        Fetch the documentation page content and return its content and hash.

        Args:
            section_id: The section ID (full URL)

        Returns:
            Tuple of (content, hash)
        """
        url = section_id

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove non-content elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
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
            self.logger.error(f"  Error fetching {url}: {e}")
            return "", ""

    def get_section_url(self, section_id: str) -> str:
        """
        Get the URL for a specific section.

        Args:
            section_id: The section identifier (full URL)

        Returns:
            The docs URL (same as section_id)
        """
        return section_id

    def get_telegram_footer(self) -> str:
        """
        Get the footer for Telegram messages with docs links.

        Returns:
            Footer string with docs links
        """
        message = "\n📚 Documentation:\n"
        for page_type, page_info in self.urls.items():
            # Shorten labels for Telegram
            label = page_info["title"].replace("Upcoming Changes", "").replace("Changelog", "").strip()
            if not label:
                label = page_info["title"]
            message += f"  • [{label}]({page_info['url']})\n"
        return message.rstrip()

    def print_summary_footer(self):
        """Print footer for summary with docs URLs."""
        self.logger.info("View documentation at:")
        for page_type, page_info in self.urls.items():
            self.logger.info(f"  {page_info['title']}: {page_info['url']}")

    def print_summary(self, changes: Dict):
        """
        Print a summary of changes.

        Overrides base class to add page type labels to section names.
        """
        self.logger.info("=" * 70)
        self.logger.info("CHANGE SUMMARY")
        self.logger.info("=" * 70)

        if changes["new_sections"]:
            self.logger.info(f"📄 NEW SECTIONS ({len(changes['new_sections'])}):")
            for section in changes["new_sections"]:
                self.logger.info(f"  + {section['title']}")
                self.logger.info(f"    URL: {section['id']}")

        if changes["modified_sections"]:
            self.logger.info(f"✏️  MODIFIED SECTIONS ({len(changes['modified_sections'])}):")
            for section in changes["modified_sections"]:
                self.logger.info(f"  ~ {section['title']}")
                self.logger.info(f"    URL: {section['id']}")
                self.logger.info(f"    Old hash: {section['old_hash'][:16]}...")
                self.logger.info(f"    New hash: {section['new_hash'][:16]}...")

        if changes["deleted_sections"]:
            self.logger.info(f"🗑️  DELETED SECTIONS ({len(changes['deleted_sections'])}):")
            for section in changes["deleted_sections"]:
                self.logger.info(f"  - {section['title']}")
                self.logger.info(f"    URL: {section['id']}")

        self.logger.info(f"✓ UNCHANGED SECTIONS: {len(changes['unchanged_sections'])}")

        total_changes = (
            len(changes["new_sections"])
            + len(changes["modified_sections"])
            + len(changes["deleted_sections"])
        )

        if total_changes == 0:
            self.logger.info("✅ No changes detected!")
        else:
            self.logger.warning(f"⚠️  Total changes: {total_changes}")

        self.print_summary_footer()

    def send_telegram(self, changes: Dict):
        """
        Send Telegram notification if changes were detected.

        Overrides base class to add page type labels to section names.

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
        message = f"🔔 *{self.exchange_name} API Documentation Changed*\n\n"
        message += f"📊 Total Changes: *{total_changes}*\n"
        message += f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"

        if changes["new_sections"]:
            message += f"📄 *NEW SECTIONS ({len(changes['new_sections'])})*:\n"
            for section in changes["new_sections"][:10]:
                message += f"  • {section['title']}\n"
                message += f"    [View]({section['id']})\n"
            if len(changes["new_sections"]) > 10:
                message += f"  ... and {len(changes['new_sections']) - 10} more\n"
            message += "\n"

        if changes["modified_sections"]:
            message += f"✏️ *MODIFIED SECTIONS ({len(changes['modified_sections'])})*:\n"
            for section in changes["modified_sections"][:10]:
                message += f"  • {section['title']}\n"
                message += f"    [View]({section['id']})\n"
            if len(changes["modified_sections"]) > 10:
                message += f"  ... and {len(changes['modified_sections']) - 10} more\n"
            message += "\n"

        if changes["deleted_sections"]:
            message += f"🗑️ *DELETED SECTIONS ({len(changes['deleted_sections'])})*:\n"
            for section in changes["deleted_sections"][:10]:
                message += f"  • {section['title']}\n"
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


def main():
    """Main execution function."""
    # Create argument parser using base class helper
    parser = BaseDocMonitor.create_argument_parser(
        exchange_name="Coinbase", default_storage_file="state/coinbase_docs_state.json"
    )

    args = parser.parse_args()

    # Get Telegram credentials using base class helper
    telegram_token, telegram_chat_id = BaseDocMonitor.get_telegram_credentials(args)

    # Create monitor instance
    monitor = CoinbaseDocMonitor(
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
