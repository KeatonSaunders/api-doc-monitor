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

    def discover_sections(self) -> Dict[str, str]:
        """
        Discover documentation sections from all configured Binance documentation pages.

        Returns:
            Dict of section_id -> section_title (section_id format: "api_type:section_id")
        """
        all_sections = {}

        for api_type, url in self.urls.items():
            self.logger.info(f"Fetching {api_type.upper()} documentation from {url}...")

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
                        # Create a unique key combining API type and section ID
                        full_id = f"{api_type}:{section_id}"
                        all_sections[full_id] = section_title
                        self.logger.debug(f"  Found section: {section_title} (#{section_id})")

                self.logger.info(f"  Discovered {len([k for k in all_sections if k.startswith(api_type)])} sections for {api_type}")

            except Exception as e:
                self.logger.error(f"  Error fetching documentation: {e}")

        return all_sections

    def fetch_section_content(self, full_section_id: str) -> Tuple[str, str]:
        """
        Fetch a specific section's content and return its content and hash.

        Args:
            full_section_id: The section ID in format "api_type:section_id"

        Returns:
            Tuple of (content, hash)
        """
        # Parse the full_section_id to get api_type and section_id
        api_type, section_id = full_section_id.split(":", 1)
        url = self.urls.get(api_type)

        if not url:
            return "", ""

        try:
            response = self.session.get(url, timeout=10)
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
            self.logger.error(f"  Error fetching section {full_section_id}: {e}")
            return "", ""

    def get_section_url(self, full_section_id: str) -> str:
        """
        Get the URL for a specific section.

        Args:
            full_section_id: The section ID in format "api_type:section_id"

        Returns:
            Full URL to the section
        """
        # Parse the full_section_id to get api_type and section_id
        api_type, section_id = full_section_id.split(":", 1)
        url = self.urls.get(api_type, "")

        if url:
            return f"{url}#{section_id}"
        return ""

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

    def print_summary_footer(self):
        """Print footer for summary with documentation URLs."""
        self.logger.info("View documentation at:")
        for api_type, url in self.urls.items():
            self.logger.info(f"  {api_type.upper()}: {url}")

    def send_telegram(self, changes: Dict):
        """
        Send Telegram notification if changes were detected.

        Overrides base class to add API type labels to section names.

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
            for section in changes["new_sections"][:10]:  # Limit to 10
                # Parse api_type from section ID (format: "api_type:section_id")
                api_type = section["id"].split(":", 1)[0]
                api_label = api_type.upper()
                message += f"  • [{api_label}] {section['title']}\n"
                section_url = self.get_section_url(section["id"])
                message += f"    [View]({section_url})\n"
            if len(changes["new_sections"]) > 10:
                message += f"  ... and {len(changes['new_sections']) - 10} more\n"
            message += "\n"

        if changes["modified_sections"]:
            message += f"✏️ *MODIFIED SECTIONS ({len(changes['modified_sections'])})*:\n"
            for section in changes["modified_sections"][:10]:  # Limit to 10
                # Parse api_type from section ID (format: "api_type:section_id")
                api_type = section["id"].split(":", 1)[0]
                api_label = api_type.upper()
                message += f"  • [{api_label}] {section['title']}\n"
                section_url = self.get_section_url(section["id"])
                message += f"    [View]({section_url})\n"
            if len(changes["modified_sections"]) > 10:
                message += f"  ... and {len(changes['modified_sections']) - 10} more\n"
            message += "\n"

        if changes["deleted_sections"]:
            message += f"🗑️ *DELETED SECTIONS ({len(changes['deleted_sections'])})*:\n"
            for section in changes["deleted_sections"][:10]:
                # Parse api_type from section ID (format: "api_type:section_id")
                api_type = section["id"].split(":", 1)[0]
                api_label = api_type.upper()
                message += f"  • [{api_label}] {section['title']}\n"
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

        Overrides base class to add API type labels to section names.
        """
        self.logger.info("=" * 70)
        self.logger.info("CHANGE SUMMARY")
        self.logger.info("=" * 70)

        if changes["new_sections"]:
            self.logger.info(f"📄 NEW SECTIONS ({len(changes['new_sections'])}):")
            for section in changes["new_sections"]:
                # Parse api_type from section ID (format: "api_type:section_id")
                api_type, section_id = section["id"].split(":", 1)
                api_label = api_type.upper()
                self.logger.info(f"  + [{api_label}] {section['title']} (#{section_id})")

        if changes["modified_sections"]:
            self.logger.info(f"✏️  MODIFIED SECTIONS ({len(changes['modified_sections'])}):")
            for section in changes["modified_sections"]:
                # Parse api_type from section ID (format: "api_type:section_id")
                api_type, section_id = section["id"].split(":", 1)
                api_label = api_type.upper()
                self.logger.info(f"  ~ [{api_label}] {section['title']} (#{section_id})")
                self.logger.info(f"    Old hash: {section['old_hash'][:16]}...")
                self.logger.info(f"    New hash: {section['new_hash'][:16]}...")

        if changes["deleted_sections"]:
            self.logger.info(f"🗑️  DELETED SECTIONS ({len(changes['deleted_sections'])}):")
            for section in changes["deleted_sections"]:
                # Parse api_type from section ID (format: "api_type:section_id")
                api_type, section_id = section["id"].split(":", 1)
                api_label = api_type.upper()
                self.logger.info(f"  - [{api_label}] {section['title']} (#{section_id})")

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

        # Use the base class's print_summary_footer method
        self.print_summary_footer()


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
