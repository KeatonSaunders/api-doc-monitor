#!/usr/bin/env python3
"""
Kraken API Documentation Change Monitor with Telegram Notifications

This script monitors Kraken API changelog page and tracks changes
by storing the page hash for comparison.

Automatically sends Telegram notifications when changes are detected.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Tuple
from .base_monitor import BaseDocMonitor


class KrakenDocMonitor(BaseDocMonitor):
    def __init__(
        self,
        storage_file: str = "state/kraken_docs_state.json",
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
            exchange_name="Kraken",
            storage_file=storage_file,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
        )

        self.changelog_url = "https://docs.kraken.com/api/docs/change-log"

    def discover_sections(self) -> Dict[str, str]:
        """
        Discover sections to monitor. For Kraken, we monitor the entire changelog as one section.

        Returns:
            Dict with single entry: changelog URL -> title
        """
        self.logger.info(f"Setting up monitoring for {self.changelog_url}...")

        # Return the changelog URL as a single section to monitor
        sections = {
            self.changelog_url: "Kraken API Changelog"
        }

        self.logger.info(f"  Monitoring: Kraken API Changelog (entire page)")

        return sections

    def fetch_section_content(self, section_id: str) -> Tuple[str, str]:
        """
        Fetch the changelog page content and return its content and hash.

        Args:
            section_id: The section ID (changelog URL)

        Returns:
            Tuple of (content, hash)
        """
        try:
            response = self.session.get(section_id, timeout=15)
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
            self.logger.error(f"  Error fetching changelog: {e}")
            return "", ""

    def get_section_url(self, section_id: str) -> str:
        """
        Get the URL for a specific section.

        Args:
            section_id: The section identifier (changelog URL)

        Returns:
            The changelog URL
        """
        return section_id

    def get_telegram_footer(self) -> str:
        """
        Get the footer for Telegram messages with changelog link.

        Returns:
            Footer string with changelog link
        """
        return f"\n📚 Changelog: [Kraken API Changelog]({self.changelog_url})"

    def print_summary_footer(self):
        """Print footer for summary with changelog URL."""
        self.logger.info("View changelog at:")
        self.logger.info(f"  Kraken: {self.changelog_url}")


def main():
    """Main execution function."""
    # Create argument parser using base class helper
    parser = BaseDocMonitor.create_argument_parser(
        exchange_name="Kraken", default_storage_file="state/kraken_docs_state.json"
    )

    args = parser.parse_args()

    # Get Telegram credentials using base class helper
    telegram_token, telegram_chat_id = BaseDocMonitor.get_telegram_credentials(args)

    # Create monitor instance
    monitor = KrakenDocMonitor(
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
