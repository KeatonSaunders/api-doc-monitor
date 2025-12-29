#!/usr/bin/env python3
"""
Deribit API Documentation Change Monitor with Telegram Notifications

This script scrapes the Deribit API documentation website and tracks changes
by storing page hashes and optionally full content for comparison.

Automatically sends Telegram notifications when changes are detected.
"""

from bs4 import BeautifulSoup
from typing import Dict, Tuple
from datetime import datetime
import time
from .base_monitor import BaseDocMonitor


class DeribitDocMonitor(BaseDocMonitor):
    def __init__(
        self,
        storage_file: str = "state/deribit_docs_state.json",
        telegram_bot_token: str = None,
        telegram_chat_id: str = None,
    ):
        """
        Initialize the Deribit documentation monitor.

        Args:
            storage_file: Path to JSON file storing previous state
            telegram_bot_token: Telegram bot token from @BotFather
            telegram_chat_id: Telegram chat ID to send messages to
        """
        super().__init__(
            exchange_name="Deribit",
            storage_file=storage_file,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
        )
        self.base_url = "https://docs.deribit.com/"
        self._cached_soup = None  # Cache the parsed page

    def _fetch_and_cache_page(self):
        """Fetch the documentation page once and cache it."""
        if self._cached_soup is None:
            print(f"Fetching documentation from {self.base_url}...")
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            self._cached_soup = BeautifulSoup(response.text, "html.parser")

    def discover_sections(self) -> Dict[str, str]:
        """
        Discover documentation sections from the single-page docs.

        Since Deribit docs is a single-page app, we extract major sections
        as separate trackable items.

        Returns:
            Dict of section_id -> section_title
        """
        sections = {}

        try:
            self._fetch_and_cache_page()

            # Find all major headings (h1, h2) which represent different sections
            for heading in self._cached_soup.find_all(["h1", "h2"]):
                # Get the id attribute for the section
                section_id = heading.get("id")
                if section_id:
                    section_title = heading.get_text(strip=True)
                    sections[section_id] = section_title
                    print(f"Found section: {section_title} (#{section_id})")

            print(f"\nDiscovered {len(sections)} documentation sections")

        except Exception as e:
            print(f"Error fetching documentation: {e}")

        return sections

    def fetch_section_content(self, section_id: str) -> Tuple[str, str]:
        """
        Fetch a specific section's content and return its content and hash.
        Uses cached page to avoid redundant HTTP requests.

        Args:
            section_id: The section ID

        Returns:
            Tuple of (content, hash)
        """
        try:
            # Ensure page is cached (will only fetch if not already cached)
            self._fetch_and_cache_page()

            # Find the section by ID from cached soup
            section = self._cached_soup.find(id=section_id)

            if not section:
                print(f"Section {section_id} not found")
                return "", ""

            # Get all content until the next major heading
            content_parts = []
            for sibling in section.find_all_next():
                # Stop at the next h1 or h2
                if sibling.name in ["h1", "h2"] and sibling.get("id") != section_id:
                    break

                # Get text from this element
                if sibling.name not in ["script", "style", "nav", "footer", "header"]:
                    text = sibling.get_text(separator=" ", strip=True)
                    if text:
                        content_parts.append(text)

            content = "\n".join(content_parts)
            content_hash = self.get_page_hash(content)

            return content, content_hash
        except Exception as e:
            print(f"Error fetching section {section_id}: {e}")
            return "", ""

    def get_section_url(self, section_id: str) -> str:
        """
        Get the URL for a specific section.

        Args:
            section_id: The section ID

        Returns:
            Full URL to the section
        """
        return f"{self.base_url}#{section_id}"

    def check_for_changes(self, save_content: bool = False) -> Dict:
        """
        Override to clear cache after checking.

        Args:
            save_content: Whether to save full content

        Returns:
            Dictionary with change information
        """
        try:
            # Run the base class check
            changes = super().check_for_changes(save_content)
            return changes
        finally:
            # Clear the cache after checking
            self._cached_soup = None

    def get_telegram_footer(self) -> str:
        """Get the footer for Telegram messages."""
        return f"\n[View Full Documentation]({self.base_url})"

    def print_summary_footer(self):
        """Print footer for summary."""
        print(f"\nView full documentation at: {self.base_url}")


def main():
    """Main execution function."""
    parser = BaseDocMonitor.create_argument_parser(
        exchange_name="Deribit", default_storage_file="state/deribit_docs_state.json"
    )
    args = parser.parse_args()

    # Get Telegram credentials
    telegram_token, telegram_chat_id = BaseDocMonitor.get_telegram_credentials(args)

    # Create monitor
    monitor = DeribitDocMonitor(
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
