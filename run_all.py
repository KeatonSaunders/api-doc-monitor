#!/usr/bin/env python3
"""
Master script to run all exchange documentation monitors.

This script runs all configured exchange monitors sequentially and collects
results. Useful for cron jobs or scheduled monitoring.
"""

import argparse
import sys
from datetime import datetime
from monitors import (
    BinanceDocMonitor,
    BybitDocMonitor,
    DeribitDocMonitor,
    HyperliquidDocMonitor,
    OKXDocMonitor,
    BaseDocMonitor,
)


def run_monitor(monitor_class, monitor_name, **kwargs):
    """
    Run a single monitor and return results.

    Args:
        monitor_class: The monitor class to instantiate
        monitor_name: Human-readable name for logging
        **kwargs: Additional arguments to pass to the monitor

    Returns:
        Dict with change information
    """
    print("\n" + "=" * 80)
    print(f"Running {monitor_name} Monitor")
    print("=" * 80)

    try:
        monitor = monitor_class(**kwargs)
        changes = monitor.check_for_changes(save_content=False)
        monitor.print_summary(changes)
        monitor.send_telegram(changes)

        return {
            "success": True,
            "monitor": monitor_name,
            "changes": changes,
            "error": None,
        }

    except Exception as e:
        print(f"\n❌ Error running {monitor_name} monitor: {e}")
        return {
            "success": False,
            "monitor": monitor_name,
            "changes": None,
            "error": str(e),
        }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Run all exchange documentation monitors"
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
        "--save-content",
        action="store_true",
        help="Save full section content for detailed diffs (increases storage)",
    )
    parser.add_argument(
        "--exchanges",
        nargs="+",
        choices=["binance", "bybit", "deribit", "hyperliquid", "okx", "all"],
        default=["all"],
        help="Which exchanges to monitor (default: all)",
    )

    args = parser.parse_args()

    # Get Telegram credentials
    class DummyArgs:
        def __init__(self, config, telegram_token, telegram_chat_id, no_telegram):
            self.config = config
            self.telegram_token = telegram_token
            self.telegram_chat_id = telegram_chat_id
            self.no_telegram = no_telegram

    dummy_args = DummyArgs(
        args.config, args.telegram_token, args.telegram_chat_id, args.no_telegram
    )
    telegram_token, telegram_chat_id = BaseDocMonitor.get_telegram_credentials(
        dummy_args
    )

    # Determine which exchanges to run
    exchanges_to_run = set(args.exchanges)
    if "all" in exchanges_to_run:
        exchanges_to_run = {"binance", "bybit", "deribit", "hyperliquid", "okx"}

    # Monitor configuration
    monitors_config = []

    if "binance" in exchanges_to_run:
        monitors_config.append(
            {
                "class": BinanceDocMonitor,
                "name": "Binance",
                "kwargs": {
                    "telegram_bot_token": telegram_token,
                    "telegram_chat_id": telegram_chat_id,
                },
            }
        )

    if "bybit" in exchanges_to_run:
        monitors_config.append(
            {
                "class": BybitDocMonitor,
                "name": "Bybit",
                "kwargs": {
                    "telegram_bot_token": telegram_token,
                    "telegram_chat_id": telegram_chat_id,
                },
            }
        )

    if "deribit" in exchanges_to_run:
        monitors_config.append(
            {
                "class": DeribitDocMonitor,
                "name": "Deribit",
                "kwargs": {
                    "telegram_bot_token": telegram_token,
                    "telegram_chat_id": telegram_chat_id,
                },
            }
        )

    if "hyperliquid" in exchanges_to_run:
        monitors_config.append(
            {
                "class": HyperliquidDocMonitor,
                "name": "Hyperliquid",
                "kwargs": {
                    "telegram_bot_token": telegram_token,
                    "telegram_chat_id": telegram_chat_id,
                },
            }
        )

    if "okx" in exchanges_to_run:
        monitors_config.append(
            {
                "class": OKXDocMonitor,
                "name": "OKX",
                "kwargs": {
                    "telegram_bot_token": telegram_token,
                    "telegram_chat_id": telegram_chat_id,
                },
            }
        )

    # Run all monitors
    print("\n" + "=" * 80)
    print(f"Exchange Documentation Monitor Suite")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Monitoring {len(monitors_config)} exchange(s)")
    print("=" * 80)

    results = []
    for config in monitors_config:
        result = run_monitor(config["class"], config["name"], **config["kwargs"])
        results.append(result)

    # Print summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    total_changes = 0
    successful_monitors = 0
    failed_monitors = 0

    for result in results:
        if result["success"]:
            successful_monitors += 1
            changes = result["changes"]
            change_count = (
                len(changes["new_sections"])
                + len(changes["modified_sections"])
                + len(changes["deleted_sections"])
            )
            total_changes += change_count

            status = "✅" if change_count == 0 else f"⚠️  {change_count} change(s)"
            print(f"  {result['monitor']}: {status}")
        else:
            failed_monitors += 1
            print(f"  {result['monitor']}: ❌ Failed - {result['error']}")

    print(f"\nTotal monitors run: {len(results)}")
    print(f"Successful: {successful_monitors}")
    print(f"Failed: {failed_monitors}")
    print(f"Total changes detected: {total_changes}")
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Exit with error code if any monitors failed
    if failed_monitors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
