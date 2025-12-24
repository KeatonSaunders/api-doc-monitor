#!/usr/bin/env python3
"""
Binance API Documentation Change Monitor with Telegram Notifications

This script monitors Binance API documentation (Spot and Derivatives) and tracks changes
by storing section hashes for comparison.

Automatically sends Telegram notifications when changes are detected.
"""

import requests
from bs4 import BeautifulSoup
import hashlib
import json
import os
from datetime import datetime
import time
from typing import Dict, Tuple, List


class BinanceDocMonitor:
    def __init__(
        self,
        storage_file: str = "binance_docs_state.json",
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
        self.urls = {}
        if monitor_spot:
            self.urls["spot"] = (
                "https://developers.binance.com/docs/binance-spot-api-docs"
            )
        if monitor_derivatives:
            self.urls["derivatives"] = (
                "https://developers.binance.com/docs/derivatives/change-log"
            )

        self.storage_file = storage_file
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    def get_page_hash(self, content: str) -> str:
        """Generate SHA-256 hash of page content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def discover_sections(self, url: str, api_type: str) -> Dict[str, str]:
        """
        Discover documentation sections from the changelog page.

        Args:
            url: The URL to fetch
            api_type: Type of API (spot or derivatives)

        Returns:
            Dict of section_id -> section_title
        """
        print(f"\nFetching {api_type.upper()} documentation from {url}...")

        sections = {}

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
                    sections[full_id] = section_title
                    print(f"  Found section: {section_title} (#{section_id})")

            print(f"  Discovered {len(sections)} sections")

        except Exception as e:
            print(f"  Error fetching documentation: {e}")

        return sections

    def fetch_section_content(self, url: str, section_id: str) -> Tuple[str, str]:
        """
        Fetch a specific section's content and return its content and hash.

        Args:
            url: The base URL
            section_id: The section ID (without api_type prefix)

        Returns:
            Tuple of (content, hash)
        """
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
            print(f"  Error fetching section {section_id}: {e}")
            return "", ""

    def load_previous_state(self) -> Dict:
        """Load previous state from storage file."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading previous state: {e}")
        return {}

    def save_state(self, state: Dict):
        """Save current state to storage file."""
        try:
            with open(self.storage_file, "w") as f:
                json.dump(state, f, indent=2)
            print(f"\nState saved to {self.storage_file}")
        except Exception as e:
            print(f"Error saving state: {e}")

    def check_for_changes(self, save_content: bool = False) -> Dict:
        """
        Check all documentation sections for changes.

        Args:
            save_content: Whether to save full content (for detailed diffs)

        Returns:
            Dictionary with change information
        """
        print("=" * 70)
        print("Binance API Documentation Change Monitor")
        print("=" * 70)

        # Load previous state
        previous_state = self.load_previous_state()
        previous_sections = previous_state.get("sections", {})
        previous_timestamp = previous_state.get("timestamp", "Never")

        print(f"Previous check: {previous_timestamp}")

        # Current state
        current_state = {"timestamp": datetime.now().isoformat(), "sections": {}}

        # Track changes
        changes = {
            "new_sections": [],
            "modified_sections": [],
            "deleted_sections": [],
            "unchanged_sections": [],
        }

        # Discover and check all sections from all URLs
        all_sections = {}
        for api_type, url in self.urls.items():
            sections = self.discover_sections(url, api_type)
            all_sections.update(sections)

        print(f"\nTotal sections discovered: {len(all_sections)}")
        print(f"Checking {len(all_sections)} sections for changes...\n")

        # Check each section
        for i, (full_section_id, section_title) in enumerate(
            sorted(all_sections.items()), 1
        ):
            # Parse the full_section_id to get api_type and section_id
            api_type, section_id = full_section_id.split(":", 1)
            url = self.urls[api_type]

            print(
                f"[{i}/{len(all_sections)}] Checking {api_type.upper()}: {section_title}...",
                end=" ",
            )

            content, content_hash = self.fetch_section_content(url, section_id)

            if not content_hash:
                print("FAILED")
                continue

            # Store in current state
            section_data = {
                "title": section_title,
                "hash": content_hash,
                "api_type": api_type,
                "section_id": section_id,
                "last_checked": datetime.now().isoformat(),
            }

            if save_content:
                section_data["content"] = content

            current_state["sections"][full_section_id] = section_data

            # Compare with previous state
            if full_section_id not in previous_sections:
                print("NEW")
                changes["new_sections"].append(
                    {
                        "id": full_section_id,
                        "title": section_title,
                        "api_type": api_type,
                        "section_id": section_id,
                    }
                )
            elif previous_sections[full_section_id].get("hash") != content_hash:
                print("MODIFIED")
                changes["modified_sections"].append(
                    {
                        "id": full_section_id,
                        "title": section_title,
                        "api_type": api_type,
                        "section_id": section_id,
                        "old_hash": previous_sections[full_section_id].get("hash"),
                        "new_hash": content_hash,
                    }
                )
            else:
                print("UNCHANGED")
                changes["unchanged_sections"].append(full_section_id)

            time.sleep(0.3)  # Rate limiting

        # Check for deleted sections
        for full_section_id in previous_sections:
            if full_section_id not in current_state["sections"]:
                prev_section = previous_sections[full_section_id]
                changes["deleted_sections"].append(
                    {
                        "id": full_section_id,
                        "title": prev_section.get("title", "Unknown"),
                        "api_type": prev_section.get("api_type", "unknown"),
                        "section_id": prev_section.get("section_id", ""),
                    }
                )

        # Save current state
        self.save_state(current_state)

        return changes

    def send_telegram(self, changes: Dict):
        """
        Send Telegram notification if changes were detected.

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
        message = f"🔔 *Binance API Documentation Changed*\n\n"
        message += f"📊 Total Changes: *{total_changes}*\n"
        message += f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"

        if changes["new_sections"]:
            message += f"📄 *NEW SECTIONS ({len(changes['new_sections'])})*:\n"
            for section in changes["new_sections"][:10]:  # Limit to 10
                api_label = section["api_type"].upper()
                message += f"  • [{api_label}] {section['title']}\n"
                url = self.urls[section["api_type"]]
                message += f"    [View]({url}#{section['section_id']})\n"
            if len(changes["new_sections"]) > 10:
                message += f"  ... and {len(changes['new_sections']) - 10} more\n"
            message += "\n"

        if changes["modified_sections"]:
            message += f"✏️ *MODIFIED SECTIONS ({len(changes['modified_sections'])})*:\n"
            for section in changes["modified_sections"][:10]:  # Limit to 10
                api_label = section["api_type"].upper()
                message += f"  • [{api_label}] {section['title']}\n"
                url = self.urls[section["api_type"]]
                message += f"    [View]({url}#{section['section_id']})\n"
            if len(changes["modified_sections"]) > 10:
                message += f"  ... and {len(changes['modified_sections']) - 10} more\n"
            message += "\n"

        if changes["deleted_sections"]:
            message += f"🗑️ *DELETED SECTIONS ({len(changes['deleted_sections'])})*:\n"
            for section in changes["deleted_sections"][:10]:
                api_label = section["api_type"].upper()
                message += f"  • [{api_label}] {section['title']}\n"
            if len(changes["deleted_sections"]) > 10:
                message += f"  ... and {len(changes['deleted_sections']) - 10} more\n"

        message += "\n📚 Documentation:\n"
        if "spot" in self.urls:
            message += f"  • [Spot API]({self.urls['spot']})\n"
        if "derivatives" in self.urls:
            message += f"  • [Derivatives]({self.urls['derivatives']})"

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
            print(f"\n✅ Telegram notification sent successfully")
        except Exception as e:
            print(f"\n❌ Failed to send Telegram notification: {e}")

    def print_summary(self, changes: Dict):
        """Print a summary of changes."""
        print("\n" + "=" * 70)
        print("CHANGE SUMMARY")
        print("=" * 70)

        if changes["new_sections"]:
            print(f"\n📄 NEW SECTIONS ({len(changes['new_sections'])}):")
            for section in changes["new_sections"]:
                api_label = section["api_type"].upper()
                print(
                    f"  + [{api_label}] {section['title']} (#{section['section_id']})"
                )

        if changes["modified_sections"]:
            print(f"\n✏️  MODIFIED SECTIONS ({len(changes['modified_sections'])}):")
            for section in changes["modified_sections"]:
                api_label = section["api_type"].upper()
                print(
                    f"  ~ [{api_label}] {section['title']} (#{section['section_id']})"
                )
                print(f"    Old hash: {section['old_hash'][:16]}...")
                print(f"    New hash: {section['new_hash'][:16]}...")

        if changes["deleted_sections"]:
            print(f"\n🗑️  DELETED SECTIONS ({len(changes['deleted_sections'])}):")
            for section in changes["deleted_sections"]:
                api_label = section["api_type"].upper()
                print(
                    f"  - [{api_label}] {section['title']} (#{section['section_id']})"
                )

        print(f"\n✓ UNCHANGED SECTIONS: {len(changes['unchanged_sections'])}")

        total_changes = (
            len(changes["new_sections"])
            + len(changes["modified_sections"])
            + len(changes["deleted_sections"])
        )

        if total_changes == 0:
            print("\n✅ No changes detected!")
        else:
            print(f"\n⚠️  Total changes: {total_changes}")

        print("\nView documentation at:")
        for api_type, url in self.urls.items():
            print(f"  {api_type.upper()}: {url}")


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor Binance API documentation for changes with Telegram notifications"
    )
    parser.add_argument(
        "--storage-file",
        default="binance_docs_state.json",
        help="Path to state storage file (default: binance_docs_state.json)",
    )
    parser.add_argument(
        "--save-content",
        action="store_true",
        help="Save full section content for detailed diffs (increases storage)",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file with Telegram credentials (default: config.json)",
    )
    parser.add_argument(
        "--telegram-token",
        help="Telegram bot token from @BotFather (overrides config file)",
    )
    parser.add_argument(
        "--telegram-chat-id",
        help="Telegram chat ID to send notifications to (overrides config file)",
    )
    parser.add_argument(
        "--no-telegram", action="store_true", help="Disable Telegram notifications"
    )
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

    # Load config file if it exists
    telegram_token = args.telegram_token
    telegram_chat_id = args.telegram_chat_id

    if not args.no_telegram and os.path.exists(args.config):
        try:
            with open(args.config, "r") as f:
                config = json.load(f)
                if not telegram_token:
                    telegram_token = config.get("telegram", {}).get("bot_token")
                if not telegram_chat_id:
                    telegram_chat_id = config.get("telegram", {}).get("chat_id")
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")

    # Disable if no-telegram flag set
    if args.no_telegram:
        telegram_token = None
        telegram_chat_id = None

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
