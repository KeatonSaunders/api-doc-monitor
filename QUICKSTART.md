# Quick Start Guide - Config File Setup

The easiest way to run the monitors is with a config file. This keeps your credentials safe and makes the commands simple.

## Setup (One Time)

### 1. Create Your Telegram Bot

1. Open Telegram, search for `@BotFather`
2. Send: `/newbot`
3. Follow prompts to create your bot
4. **Save the bot token**: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### 2. Get Your Chat ID

1. Start a chat with your bot
2. Send it any message
3. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Find your chat ID: `"chat":{"id":987654321`

### 3. Create Config File

Copy the example config:
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

**Important**: The `.gitignore` file already excludes `config.json` so your credentials won't be committed to git!

## Running the Monitors

Once you have `config.json` set up, running the monitors is simple:

### Deribit
```bash
python deribit_doc_monitor_telegram.py
```

### Bybit
```bash
python bybit_doc_monitor_telegram.py
```

That's it! The scripts automatically read from `config.json`.

## Testing

To test that everything works:

```bash
# Delete state files to trigger "new" changes
rm deribit_docs_state.json bybit_docs_state.json

# Run the monitors
python deribit_doc_monitor_telegram.py
python bybit_doc_monitor_telegram.py

# You should receive Telegram messages for both!
```

## Automation

### Simple Cron Setup

Edit crontab:
```bash
crontab -e
```

Add these lines to check every 6 hours:
```bash
# Deribit monitor
0 */6 * * * cd /path/to/monitors && python deribit_doc_monitor_telegram.py >> deribit.log 2>&1

# Bybit monitor (30 min offset)
30 */6 * * * cd /path/to/monitors && python bybit_doc_monitor_telegram.py >> bybit.log 2>&1
```

### Run Script

Create `run_monitors.sh`:
```bash
#!/bin/bash
cd "$(dirname "$0")"
echo "=== $(date) ==="
echo "Running Deribit monitor..."
python deribit_doc_monitor_telegram.py
echo ""
echo "Running Bybit monitor..."
python bybit_doc_monitor_telegram.py
echo "Done!"
```

Make executable and run:
```bash
chmod +x run_monitors.sh
./run_monitors.sh
```

## Command-Line Override

You can still override config file settings from command line:

```bash
# Use different token for this run
python deribit_doc_monitor_telegram.py \
  --telegram-token "different_token" \
  --telegram-chat-id "different_chat_id"

# Use different config file
python deribit_doc_monitor_telegram.py --config my_config.json

# Disable notifications for testing
python deribit_doc_monitor_telegram.py --no-telegram
```

## File Structure

```
your-project/
├── .gitignore                          # Excludes config.json and state files
├── config.json.example                 # Template (safe to commit)
├── config.json                         # Your credentials (NOT in git)
├── deribit_doc_monitor_telegram.py    # Deribit monitor
├── bybit_doc_monitor_telegram.py      # Bybit monitor
├── deribit_docs_state.json            # Deribit state (auto-generated)
├── bybit_docs_state.json              # Bybit state (auto-generated)
└── requirements.txt                    # Dependencies
```

## Docker Compose with Config File

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

Run:
```bash
docker-compose up -d
```

## Troubleshooting

### "Could not load config file"
- Make sure `config.json` exists (copy from `config.json.example`)
- Check that the JSON is valid (no trailing commas, proper quotes)

### No Telegram notifications
- Verify bot token and chat ID are correct in `config.json`
- Make sure you messaged the bot first
- Check script output for errors

### Bybit finding too many/few pages
- Default is now 500 pages (was 200)
- You can adjust with: `--max-pages 1000`
- Current Bybit docs have ~300 pages

## Security Notes

✅ `config.json` is in `.gitignore` - safe from git  
✅ Use `chmod 600 config.json` to restrict file permissions  
✅ Never share `config.json` or commit it  
✅ You can regenerate bot token via @BotFather if compromised  

## Benefits of Config File Approach

1. **Simple commands** - no long parameter lists
2. **Secure** - credentials not in shell history
3. **Git-safe** - `.gitignore` prevents accidents
4. **Reusable** - same config for all runs
5. **Shareable** - `config.json.example` shows format without exposing secrets
