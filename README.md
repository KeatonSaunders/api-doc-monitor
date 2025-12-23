# Crypto Exchange API Documentation Monitors

Monitor Deribit and Bybit API documentation for changes and receive instant Telegram notifications when updates occur.

## Overview

This tool tracks changes to cryptocurrency exchange API documentation by monitoring documentation sections and pages. When changes are detected (new sections, modifications, or deletions), you receive detailed Telegram notifications with direct links to the changed content.

**Supported Exchanges:**
- **Deribit**: Section-based tracking of single-page documentation
- **Bybit**: Page-based tracking across multi-page documentation

## Features

- Real-time Telegram notifications with rich formatting
- Hash-based change detection for efficiency
- Persistent state tracking across runs
- Detailed change summaries with direct links
- Simple config file setup
- Ready for automation (cron, Docker)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Requirements: Python 3.7+, requests, beautifulsoup4

### 2. Set Up Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Save your bot token: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
4. Start a chat with your bot and send any message
5. Get your chat ID from: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Look for `"chat":{"id":987654321}`

### 3. Create Config File

```bash
cp config.json.example config.json
```

Edit `config.json` with your credentials:

```json
{
  "telegram": {
    "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "chat_id": "987654321"
  }
}
```

The config file is git-ignored for security.

### 4. Run the Monitors

```bash
# Monitor Deribit documentation
python deribit_doc_monitor_telegram.py

# Monitor Bybit documentation
python bybit_doc_monitor_telegram.py
```

That's it! The scripts automatically read from `config.json`.

## How It Works

### Deribit Monitor
Deribit uses a single-page application for documentation. The script:
1. Fetches the main documentation page
2. Extracts all sections based on H1/H2 headings with IDs
3. Tracks each section separately by ID
4. Compares content hashes to detect changes
5. Sends Telegram notification with changed sections

### Bybit Monitor
Bybit uses multi-page documentation. The script:
1. Crawls the documentation site starting from the base URL
2. Discovers all documentation pages via internal links
3. Tracks each page separately
4. Compares content hashes to detect changes
5. Sends Telegram notification with changed pages

## Telegram Notifications

Example notification when changes are detected:

```
🔔 Deribit API Documentation Changed

📊 Total Changes: 3
🕒 2024-12-23 15:30 UTC

📄 NEW SECTIONS (1):
  • Block RFQ Features
    View: https://docs.deribit.com/#block-rfq-features

✏️ MODIFIED SECTIONS (2):
  • /public/auth
    View: https://docs.deribit.com/#public-auth
  • Rate Limits
    View: https://docs.deribit.com/#rate-limits

View Full Documentation
```

## Command-Line Options

Both monitors support these options:

```bash
# Use custom storage file
python deribit_doc_monitor_telegram.py --storage-file my_state.json

# Use different config file
python deribit_doc_monitor_telegram.py --config my_config.json

# Override config with command-line args
python deribit_doc_monitor_telegram.py \
  --telegram-token "different_token" \
  --telegram-chat-id "different_chat_id"

# Disable notifications for testing
python deribit_doc_monitor_telegram.py --no-telegram

# Bybit: adjust page discovery limit
python bybit_doc_monitor_telegram.py --max-pages 1000
```

## Automation

### Cron (Linux/Mac)

Check every 6 hours:

```bash
crontab -e
```

Add these lines:

```bash
# Deribit monitor
0 */6 * * * cd /path/to/monitors && python deribit_doc_monitor_telegram.py >> deribit.log 2>&1

# Bybit monitor (30 min offset)
30 */6 * * * cd /path/to/monitors && python bybit_doc_monitor_telegram.py >> bybit.log 2>&1
```

### Shell Script

Create `run_monitors.sh`:

```bash
#!/bin/bash
cd "$(dirname "$0")"
echo "=== $(date) ==="
python deribit_doc_monitor_telegram.py
python bybit_doc_monitor_telegram.py
echo "Done!"
```

Make executable and run:

```bash
chmod +x run_monitors.sh
./run_monitors.sh
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  deribit-monitor:
    build: .
    volumes:
      - ./config.json:/app/config.json:ro
      - ./data:/app/data
    command: >
      bash -c "
        while true; do
          python deribit_doc_monitor_telegram.py \
            --storage-file /app/data/deribit_docs_state.json
          sleep 21600
        done
      "

  bybit-monitor:
    build: .
    volumes:
      - ./config.json:/app/config.json:ro
      - ./data:/app/data
    command: >
      bash -c "
        while true; do
          python bybit_doc_monitor_telegram.py \
            --storage-file /app/data/bybit_docs_state.json
          sleep 21600
        done
      "
```

Run with:

```bash
docker-compose up -d
```

## State Files

Both monitors maintain JSON state files to track changes:

```json
{
  "timestamp": "2024-12-23T10:30:00",
  "sections": {
    "section-id": {
      "title": "Section Title",
      "hash": "5f4dcc3b5aa765d61d8327deb882cf99",
      "last_checked": "2024-12-23T10:30:00"
    }
  }
}
```

State files are automatically created on first run and updated on subsequent runs.

## Testing Your Setup

To verify everything works:

```bash
# Delete state files to trigger "new" changes
rm deribit_docs_state.json bybit_docs_state.json

# Run the monitors
python deribit_doc_monitor_telegram.py
python bybit_doc_monitor_telegram.py

# You should receive Telegram messages!
```

## Telegram Setup Details

### For Groups (Multiple Recipients)

1. Create a Telegram group
2. Add all recipients to the group
3. Add your bot to the group
4. Send a message in the group
5. Use the group chat ID (negative number like `-987654321`)

Everyone in the group will receive notifications!

### Security Best Practices

- Never commit `config.json` to git (already in `.gitignore`)
- Use `chmod 600 config.json` to restrict file permissions
- Keep your bot token secret
- Regenerate token via @BotFather if compromised

## Troubleshooting

**Config file not found**
- Ensure `config.json` exists (copy from `config.json.example`)
- Verify JSON is valid (no trailing commas)

**No Telegram notifications**
- Verify bot token and chat ID in `config.json`
- Ensure you sent a message to the bot first
- Check script output for errors

**Connection failures**
- Check internet connection
- Verify documentation URLs are accessible
- Check for firewall/proxy issues

**False positives**
- Minor HTML formatting changes can trigger detection
- This is normal for hash-based change detection
- Timestamps or dynamic content may cause this

## What Gets Tracked

### Deribit
- API overview and general information
- Authentication methods
- Market data endpoints
- Trading endpoints
- Account management
- Wallet operations
- WebSocket subscriptions
- Block trading and RFQ features

### Bybit
- All API documentation pages
- Authentication guides
- Trading endpoints
- Market data APIs
- Account endpoints
- WebSocket documentation
- Rate limits and best practices

## Why Telegram Over Email?

- No SMTP server or authentication needed
- Instant delivery to mobile devices
- Rich formatting with links and emojis
- Free and reliable
- Easy multi-recipient setup via groups
- No firewall issues (uses HTTPS)

## License

MIT License - feel free to modify and use as needed.

## Contributing

Suggestions and improvements welcome! Consider adding:
- Support for additional exchanges
- Database storage instead of JSON
- Historical change tracking
- Change severity classification
- Web dashboard for monitoring
