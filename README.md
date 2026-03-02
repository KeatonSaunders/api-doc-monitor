# Exchange API Documentation Monitors

Monitor cryptocurrency exchange API documentation for changes and receive Telegram notifications.

## Supported Exchanges

| Exchange | Monitor Type | Description |
|----------|--------------|-------------|
| **Binance** | Changelog | Spot & Derivatives changelog |
| **Bitget** | Changelog | Classic & UTA changelog (Selenium) |
| **BitMEX** | Changelog | API changelog |
| **Bybit** | Full site | Crawls entire V5 API docs |
| **Coinbase** | Changelog | API changelog |
| **Deribit** | Full site | Crawls API reference |
| **Hyperliquid** | Full site | API, Trading, and HyperCore docs |
| **Kraken** | Changelog | API changelog |
| **Lighter** | Full site | Crawls API docs |
| **OKX** | Changelog | Upcoming changes |

## Directory Structure

```
scraper/
├── monitors/                 # Monitor implementations
│   ├── __init__.py
│   ├── base_monitor.py       # Base class with common functionality
│   ├── binance.py
│   ├── bitget.py             # Uses Selenium for JS rendering
│   ├── bitmex.py
│   ├── bybit.py
│   ├── coinbase.py
│   ├── deribit.py
│   ├── hyperliquid.py
│   ├── kraken.py
│   ├── lighter.py
│   ├── logger_config.py
│   └── okx.py
├── state/                    # State files (auto-generated)
│   ├── binance_docs_state.json
│   ├── bitget_docs_state.json
│   ├── bitmex_docs_state.json
│   ├── bybit_docs_state.json
│   ├── coinbase_docs_state.json
│   ├── deribit_docs_state.json
│   ├── hyperliquid_docs_state.json
│   ├── kraken_docs_state.json
│   ├── lighter_docs_state.json
│   └── okx_docs_state.json
├── config.json               # Telegram configuration
├── requirements.txt
├── run_all.py                # Master script to run all monitors
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

Requirements:
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `selenium` - JS rendering (for Bitget)
- `webdriver-manager` - Chrome driver management

## Configuration

Create a `config.json` file with your Telegram credentials:

```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  }
}
```

To get these:
1. Create a bot via [@BotFather](https://t.me/BotFather) to get the bot token
2. Send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your chat ID
3. For group chats, add the bot to the group and look for the negative chat ID in getUpdates

## Usage

### Run All Monitors

```bash
# Run all exchanges (saves content by default)
python run_all.py

# Run without Telegram notifications
python run_all.py --no-telegram

# Run without saving content (smaller state files)
python run_all.py --no-save-content

# Run specific exchanges only
python run_all.py --exchanges binance bybit deribit
```

### Run Individual Monitors

```bash
python -m monitors.binance
python -m monitors.bitget
python -m monitors.bitmex
python -m monitors.bybit
python -m monitors.coinbase
python -m monitors.deribit
python -m monitors.hyperliquid
python -m monitors.kraken
python -m monitors.lighter
python -m monitors.okx
```

### Command Line Arguments

#### run_all.py

| Argument | Description |
|----------|-------------|
| `--config` | Path to config file (default: `config.json`) |
| `--telegram-token` | Bot token (overrides config) |
| `--telegram-chat-id` | Chat ID (overrides config) |
| `--no-telegram` | Disable Telegram notifications |
| `--no-save-content` | Don't save page content (reduces storage) |
| `--exchanges` | Which exchanges to run: `binance`, `bitget`, `bitmex`, `bybit`, `coinbase`, `deribit`, `hyperliquid`, `kraken`, `lighter`, `okx`, or `all` |

#### Individual Monitors

All monitors support:

| Argument | Description |
|----------|-------------|
| `--config` | Path to config file |
| `--storage-file` | Path to state file |
| `--telegram-token` | Bot token (overrides config) |
| `--telegram-chat-id` | Chat ID (overrides config) |
| `--no-telegram` | Disable notifications |
| `--save-content` | Save full page content |

Some monitors have additional options (e.g., `--max-pages` for Bybit).

## State Files

State files store:
- Section hashes (for change detection)
- Last checked timestamps
- Page content (when `--save-content` or default in run_all.py)

Content is stored to help debug false positive change detections. Whitespace is normalized before hashing to prevent formatting differences from triggering false changes.

## How It Works

1. **Discovery** - Each monitor discovers sections/pages to track
2. **Fetch** - Downloads page content and extracts text
3. **Hash** - Generates SHA-256 hash of normalized content
4. **Compare** - Compares against previous state
5. **Notify** - Sends Telegram alert if changes detected
6. **Save** - Updates state file with new hashes/content
