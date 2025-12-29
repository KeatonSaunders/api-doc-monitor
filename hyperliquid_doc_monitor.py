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
from base_monitor import BaseDocMonitor


class HyperliquidDocMonitor(BaseDocMonitor):
    """Monitor for Hyperliquid GitBook documentation."""

    # Define the documentation sections to monitor
    DOCUMENTATION_PAGES = {
        # API Documentation
        "api:notation": ("for-developers/api/notation", "API - Notation"),
        "api:asset-ids": ("for-developers/api/asset-ids", "API - Asset IDs"),
        "api:tick-and-lot-size": ("for-developers/api/tick-and-lot-size", "API - Tick and lot size"),
        "api:nonces-and-api-wallets": ("for-developers/api/nonces-and-api-wallets", "API - Nonces and API wallets"),
        "api:info-endpoint": ("for-developers/api/info-endpoint", "API - Info endpoint"),
        "api:info-endpoint-perpetuals": ("for-developers/api/info-endpoint/perpetuals", "API - Info endpoint (Perpetuals)"),
        "api:info-endpoint-spot": ("for-developers/api/info-endpoint/spot", "API - Info endpoint (Spot)"),
        "api:exchange-endpoint": ("for-developers/api/exchange-endpoint", "API - Exchange endpoint"),
        "api:websocket": ("for-developers/api/websocket", "API - Websocket"),
        "api:websocket-subscriptions": ("for-developers/api/websocket/subscriptions", "API - Websocket Subscriptions"),
        "api:websocket-post-requests": ("for-developers/api/websocket/post-requests", "API - Websocket Post requests"),
        "api:websocket-timeouts": ("for-developers/api/websocket/timeouts-and-heartbeats", "API - Websocket Timeouts"),
        "api:error-responses": ("for-developers/api/error-responses", "API - Error responses"),
        "api:signing": ("for-developers/api/signing", "API - Signing"),
        "api:rate-limits": ("for-developers/api/rate-limits-and-user-limits", "API - Rate limits"),
        "api:activation-gas-fee": ("for-developers/api/activation-gas-fee", "API - Activation gas fee"),
        "api:optimizing-latency": ("for-developers/api/optimizing-latency", "API - Optimizing latency"),
        "api:bridge2": ("for-developers/api/bridge2", "API - Bridge2"),
        "api:deploying-hip-assets": ("for-developers/api/deploying-hip-1-and-hip-2-assets", "API - Deploying HIP-1/HIP-2"),
        "api:hip3-deployer": ("for-developers/api/hip-3-deployer-actions", "API - HIP-3 deployer actions"),

        # Trading Documentation
        "trading:fees": ("trading/fees", "Trading - Fees"),
        "trading:assets": ("trading/assets", "Trading - Assets"),
        "trading:margin": ("trading/margin", "Trading - Margin"),
        "trading:liquidations": ("trading/liquidations", "Trading - Liquidations"),
        "trading:order-types": ("trading/order-types", "Trading - Order types"),

        # HyperCore
        "hypercore:bridge": ("hypercore/bridge", "HyperCore - Bridge"),
        "hypercore:oracle": ("hypercore/oracle", "HyperCore - Oracle"),
        "hypercore:staking": ("hypercore/staking", "HyperCore - Staking"),
    }

    def __init__(
        self,
        storage_file: str = "hyperliquid_docs_state.json",
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

    def discover_sections(self) -> Dict[str, str]:
        """
        Discover documentation pages to monitor.

        Returns:
            Dict of page_id -> page_title
        """
        print(f"\nMonitoring {len(self.DOCUMENTATION_PAGES)} documentation pages...")

        sections = {}
        for page_id, (page_path, page_title) in self.DOCUMENTATION_PAGES.items():
            sections[page_id] = page_title
            print(f"  Will monitor: {page_title}")

        return sections

    def fetch_section_content(self, page_id: str) -> Tuple[str, str]:
        """
        Fetch a specific page's content and return its content and hash.

        Args:
            page_id: The page identifier (e.g., "api:notation", "trading:fees")

        Returns:
            Tuple of (content, hash)
        """
        url = self.get_section_url(page_id)

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # GitBook typically uses specific containers for content
            # Look for the main content area
            content_area = soup.find("div", class_="markdown-body") or \
                          soup.find("article") or \
                          soup.find("main") or \
                          soup.find("div", {"role": "main"})

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
            print(f"  Error fetching page {page_id}: {e}")
            return "", ""

    def get_section_url(self, page_id: str) -> str:
        """
        Get the URL for a specific page.

        Args:
            page_id: The page identifier (e.g., "api:notation")

        Returns:
            Full URL to the page
        """
        page_path, _ = self.DOCUMENTATION_PAGES.get(page_id, ("", ""))
        if not page_path:
            return ""
        return f"{self.base_url}/{page_path}"

    def get_telegram_footer(self) -> str:
        """
        Get the footer for Telegram messages with documentation links.

        Returns:
            Footer string with documentation links
        """
        return f"\n📚 Documentation: [Hyperliquid Docs]({self.base_url})"

    def print_summary_footer(self):
        """Print footer for summary with documentation URLs."""
        print(f"\nView documentation at:")
        print(f"  Hyperliquid: {self.base_url}")

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
                # Parse category from page ID (format: "category:page-name")
                category = section["id"].split(":", 1)[0].upper()
                message += f"  • [{category}] {section['title']}\n"
                section_url = self.get_section_url(section["id"])
                message += f"    [View]({section_url})\n"
            if len(changes["new_sections"]) > 10:
                message += f"  ... and {len(changes['new_sections']) - 10} more\n"
            message += "\n"

        if changes["modified_sections"]:
            message += f"✏️ *MODIFIED PAGES ({len(changes['modified_sections'])})*:\n"
            for section in changes["modified_sections"][:10]:  # Limit to 10
                # Parse category from page ID (format: "category:page-name")
                category = section["id"].split(":", 1)[0].upper()
                message += f"  • [{category}] {section['title']}\n"
                section_url = self.get_section_url(section["id"])
                message += f"    [View]({section_url})\n"
            if len(changes["modified_sections"]) > 10:
                message += f"  ... and {len(changes['modified_sections']) - 10} more\n"
            message += "\n"

        if changes["deleted_sections"]:
            message += f"🗑️ *DELETED PAGES ({len(changes['deleted_sections'])})*:\n"
            for section in changes["deleted_sections"][:10]:
                # Parse category from page ID (format: "category:page-name")
                category = section["id"].split(":", 1)[0].upper()
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
            print(f"\n✅ Telegram notification sent successfully")
        except Exception as e:
            print(f"\n❌ Failed to send Telegram notification: {e}")

    def print_summary(self, changes: Dict):
        """
        Print a summary of changes.

        Overrides base class to add category labels to page names.
        """
        print("\n" + "=" * 70)
        print("CHANGE SUMMARY")
        print("=" * 70)

        if changes["new_sections"]:
            print(f"\n📄 NEW PAGES ({len(changes['new_sections'])}):")
            for section in changes["new_sections"]:
                # Parse category from page ID (format: "category:page-name")
                category, page_id = section["id"].split(":", 1)
                category_label = category.upper()
                print(f"  + [{category_label}] {section['title']} (#{page_id})")

        if changes["modified_sections"]:
            print(f"\n✏️  MODIFIED PAGES ({len(changes['modified_sections'])}):")
            for section in changes["modified_sections"]:
                # Parse category from page ID (format: "category:page-name")
                category, page_id = section["id"].split(":", 1)
                category_label = category.upper()
                print(f"  ~ [{category_label}] {section['title']} (#{page_id})")
                print(f"    Old hash: {section['old_hash'][:16]}...")
                print(f"    New hash: {section['new_hash'][:16]}...")

        if changes["deleted_sections"]:
            print(f"\n🗑️  DELETED PAGES ({len(changes['deleted_sections'])}):")
            for section in changes["deleted_sections"]:
                # Parse category from page ID (format: "category:page-name")
                category, page_id = section["id"].split(":", 1)
                category_label = category.upper()
                print(f"  - [{category_label}] {section['title']} (#{page_id})")

        print(f"\n✓ UNCHANGED PAGES: {len(changes['unchanged_sections'])}")

        total_changes = (
            len(changes["new_sections"])
            + len(changes["modified_sections"])
            + len(changes["deleted_sections"])
        )

        if total_changes == 0:
            print("\n✅ No changes detected!")
        else:
            print(f"\n⚠️  Total changes: {total_changes}")

        # Use the base class's print_summary_footer method
        self.print_summary_footer()


def main():
    """Main execution function."""
    # Create argument parser using base class helper
    parser = BaseDocMonitor.create_argument_parser(
        exchange_name="Hyperliquid",
        default_storage_file="hyperliquid_docs_state.json"
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
