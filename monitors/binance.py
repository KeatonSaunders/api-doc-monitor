#!/usr/bin/env python3
"""
Binance API Documentation Change Monitor with Telegram Notifications

This script monitors Binance API documentation (Spot and Derivatives) and tracks changes
by storing section hashes for comparison.

Automatically sends Telegram notifications when changes are detected.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Tuple
import re
from .base_monitor import BaseDocMonitor


class BinanceDocMonitor(BaseDocMonitor):
    def __init__(
        self,
        storage_file: str = "state/binance_docs_state.json",
        telegram_bot_token: str = None,
        telegram_chat_id: str = None,
        monitor_spot: bool = True,
        monitor_derivatives: bool = True,
    ):
        """
        Initialize the documentation monitor.

        Args:
            storage_file: Path to JSON file storing previous state
            telegram_bot_token: Telegram bot token from @BotFather
            telegram_chat_id: Telegram chat ID to send messages to
            monitor_spot: Whether to monitor Spot API docs
            monitor_derivatives: Whether to monitor Derivatives docs
        """
        super().__init__(
            exchange_name="Binance",
            storage_file=storage_file,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
        )

        self.urls = {}
        if monitor_spot:
            self.urls["spot"] = (
                "https://developers.binance.com/docs/binance-spot-api-docs"
            )
        if monitor_derivatives:
            self.urls["derivatives"] = (
                "https://developers.binance.com/docs/derivatives/change-log"
            )

        # Get current year and previous year for filtering
        current_year = datetime.now().year
        self.years_to_monitor = [current_year, current_year - 1]

    def _is_recent_section(self, section_id: str, section_title: str) -> bool:
        """
        Check if a section is from current or previous year.

        Args:
            section_id: The section ID
            section_title: The section title

        Returns:
            True if section contains current or previous year
        """
        # Look for year patterns in both ID and title (e.g., 2026, 2025)
        combined_text = f"{section_id} {section_title}"

        # Find all 4-digit years in the text
        years = re.findall(r"\b(20\d{2})\b", combined_text)

        if years:
            # Check if any found year matches our monitored years
            for year_str in years:
                if int(year_str) in self.years_to_monitor:
                    return True
            # If we found years but none match, exclude this section
            return False

        # If no year found in section, include it (might be an overview/intro section)
        return True

    def discover_sections(self) -> Dict[str, str]:
        """
        Discover documentation sections from all configured Binance documentation pages.
        Only includes sections from current and previous year.

        Returns:
            Dict of url -> section_title
        """
        all_sections = {}
        filtered_count = 0

        for api_type, url in self.urls.items():
            self.logger.info(f"Fetching {api_type.upper()} documentation from {url}...")
            self.logger.info(
                f"  Filtering for years: {', '.join(map(str, self.years_to_monitor))}"
            )

            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # Find all headings that represent changelog entries
                # Binance uses h2, h3, or other headings with IDs for date-based sections
                for heading in soup.find_all(["h1", "h2", "h3"]):
                    section_id = heading.get("id")
                    if section_id:
                        section_title = heading.get_text(strip=True)

                        # Check if this is a recent section
                        if self._is_recent_section(section_id, section_title):
                            # Create full URL with fragment
                            full_url = f"{url}#{section_id}"
                            all_sections[full_url] = section_title
                            self.logger.debug(
                                f"  Found section: {section_title} (#{section_id})"
                            )
                        else:
                            filtered_count += 1
                            self.logger.debug(
                                f"  Filtered old section: {section_title}"
                            )

                self.logger.info(
                    f"  Discovered {len([k for k in all_sections if k.startswith(url)])} sections for {api_type}"
                )
                if filtered_count > 0:
                    self.logger.info(f"  Filtered out {filtered_count} older sections")

            except Exception as e:
                self.logger.error(f"  Error fetching documentation: {e}")

        return all_sections

    def fetch_section_content(self, section_url: str) -> Tuple[str, str]:
        """
        Fetch a specific section's content and return its content and hash.

        Args:
            section_url: The full section URL with fragment

        Returns:
            Tuple of (content, hash)
        """
        # Extract the section ID from the URL fragment
        section_id = section_url.split("#")[-1] if "#" in section_url else None

        if not section_id:
            return "", ""

        # Get the base URL (without fragment)
        base_url = section_url.split("#")[0]

        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find the section by ID
            section = soup.find(id=section_id)

            if not section:
                return "", ""

            # Get all content until the next heading of same or higher level
            content_parts = [section.get_text(strip=True)]
            current_level = section.name  # h1, h2, h3, etc.

            for sibling in section.find_all_next():
                # Stop at the next heading of same or higher level
                if sibling.name in ["h1", "h2", "h3", "h4"]:
                    # Compare heading levels (h1 < h2 < h3)
                    if (
                        sibling.name <= current_level
                        and sibling.get("id") != section_id
                    ):
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
            self.logger.error(f"  Error fetching section {section_url}: {e}")
            return "", ""

    def get_section_url(self, section_url: str) -> str:
        """
        Get the URL for a specific section.

        Args:
            section_url: The full section URL

        Returns:
            The URL (same as section_url)
        """
        return section_url

    def get_telegram_footer(self) -> str:
        """
        Get the footer for Telegram messages with documentation links.

        Returns:
            Footer string with documentation links
        """
        message = "\n📚 Documentation:\n"
        if "spot" in self.urls:
            message += f"  • [Spot API]({self.urls['spot']})\n"
        if "derivatives" in self.urls:
            message += f"  • [Derivatives]({self.urls['derivatives']})"
        return message

    def get_section_label(self, section_id: str) -> str:
        """Get API type label from URL."""
        for api_type, api_url in self.urls.items():
            if section_id.startswith(api_url):
                return api_type.upper()
        return ""

    def print_summary_footer(self):
        """Print footer for summary with documentation URLs."""
        self.logger.info("View documentation at:")
        for api_type, url in self.urls.items():
            self.logger.info(f"  {api_type.upper()}: {url}")


def main():
    """Main execution function."""
    # Create argument parser using base class helper
    parser = BaseDocMonitor.create_argument_parser(
        exchange_name="Binance", default_storage_file="state/binance_docs_state.json"
    )

    # Add Binance-specific arguments
    parser.add_argument(
        "--spot-only",
        action="store_true",
        help="Monitor only Spot API documentation",
    )
    parser.add_argument(
        "--derivatives-only",
        action="store_true",
        help="Monitor only Derivatives documentation",
    )

    args = parser.parse_args()

    # Determine which APIs to monitor
    monitor_spot = not args.derivatives_only
    monitor_derivatives = not args.spot_only

    # Get Telegram credentials using base class helper
    telegram_token, telegram_chat_id = BaseDocMonitor.get_telegram_credentials(args)

    # Create monitor instance
    monitor = BinanceDocMonitor(
        storage_file=args.storage_file,
        telegram_bot_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        monitor_spot=monitor_spot,
        monitor_derivatives=monitor_derivatives,
    )

    # Check for changes
    changes = monitor.check_for_changes(save_content=args.save_content)

    # Print summary
    monitor.print_summary(changes)

    # Send Telegram notification if changes detected
    monitor.send_telegram(changes)


if __name__ == "__main__":
    main()
