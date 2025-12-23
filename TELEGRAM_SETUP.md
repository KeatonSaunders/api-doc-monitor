# Telegram Setup Guide - Much Easier Than Email!

Setting up Telegram notifications is **much simpler** than SMTP email - just 2 steps!

## Step 1: Create a Telegram Bot (2 minutes)

1. Open Telegram and search for `@BotFather`
2. Start a chat and send: `/newbot`
3. Follow the prompts:
   - Choose a name (e.g., "Deribit Docs Monitor")
   - Choose a username (e.g., "deribit_monitor_bot")
4. **Save the bot token** - it looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

## Step 2: Get Your Chat ID (1 minute)

### Option A: Personal Messages (Simplest)

1. Start a chat with your new bot (search for the username you created)
2. Send any message to it (e.g., "Hello")
3. Open this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":123456789` - that number is your chat ID
5. **Save the chat ID**

### Option B: Group Chat

1. Create a Telegram group
2. Add your bot to the group (Add Members → search for your bot)
3. Send a message in the group
4. Open the getUpdates URL (same as above)
5. Look for the negative number like `"chat":{"id":-987654321`
6. **Save the chat ID** (include the minus sign!)

## Using the Scripts

### Deribit Monitor

```bash
python deribit_doc_monitor_telegram.py \
  --telegram-token "123456789:ABCdefGHIjklMNOpqrsTUVwxyz" \
  --telegram-chat-id "987654321"
```

### Bybit Monitor

```bash
python bybit_doc_monitor_telegram.py \
  --telegram-token "123456789:ABCdefGHIjklMNOpqrsTUVwxyz" \
  --telegram-chat-id "987654321"
```

## Example Notification

When changes are detected, you'll receive a Telegram message like:

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

## Environment Variables (Recommended)

Create a script `run_monitors.sh`:

```bash
#!/bin/bash

# Your Telegram credentials
export TELEGRAM_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="987654321"

# Run Deribit monitor
python deribit_doc_monitor_telegram.py \
  --telegram-token "$TELEGRAM_TOKEN" \
  --telegram-chat-id "$TELEGRAM_CHAT_ID"

# Run Bybit monitor
python bybit_doc_monitor_telegram.py \
  --telegram-token "$TELEGRAM_TOKEN" \
  --telegram-chat-id "$TELEGRAM_CHAT_ID"
```

Make it executable:
```bash
chmod +x run_monitors.sh
./run_monitors.sh
```

## Automated Scheduling with Cron

Check every 6 hours:

```bash
crontab -e
```

Add these lines:

```bash
# Deribit monitor every 6 hours
0 */6 * * * cd /path/to/scripts && python deribit_doc_monitor_telegram.py --telegram-token "YOUR_TOKEN" --telegram-chat-id "YOUR_CHAT_ID" >> /var/log/deribit-monitor.log 2>&1

# Bybit monitor every 6 hours (offset by 30 minutes)
30 */6 * * * cd /path/to/scripts && python bybit_doc_monitor_telegram.py --telegram-token "YOUR_TOKEN" --telegram-chat-id "YOUR_CHAT_ID" >> /var/log/bybit-monitor.log 2>&1
```

## Docker Compose Setup

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  deribit-monitor:
    build: .
    environment:
      - TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
      - TELEGRAM_CHAT_ID=987654321
    volumes:
      - ./data:/app/data
    command: >
      bash -c "
        while true; do
          python deribit_doc_monitor_telegram.py \
            --storage-file /app/data/deribit_docs_state.json \
            --telegram-token $$TELEGRAM_TOKEN \
            --telegram-chat-id $$TELEGRAM_CHAT_ID
          sleep 21600
        done
      "

  bybit-monitor:
    build: .
    environment:
      - TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
      - TELEGRAM_CHAT_ID=987654321
    volumes:
      - ./data:/app/data
    command: >
      bash -c "
        while true; do
          python bybit_doc_monitor_telegram.py \
            --storage-file /app/data/bybit_docs_state.json \
            --telegram-token $$TELEGRAM_TOKEN \
            --telegram-chat-id $$TELEGRAM_CHAT_ID
          sleep 21600
        done
      "
```

Run:
```bash
docker-compose up -d
```

## Testing Your Setup

To test if Telegram notifications work:

```bash
# Delete state file to trigger "new" changes
rm deribit_docs_state.json

# Run with your credentials
python deribit_doc_monitor_telegram.py \
  --telegram-token "YOUR_TOKEN" \
  --telegram-chat-id "YOUR_CHAT_ID"

# You should receive a Telegram message with all sections marked as "new"
```

## Advantages Over Email

✅ **No SMTP server needed** - just a bot token  
✅ **No authentication issues** - works instantly  
✅ **No firewall problems** - uses HTTPS  
✅ **Rich formatting** - bold, links, emojis  
✅ **Instant delivery** - notifications arrive immediately  
✅ **Mobile-friendly** - perfect for on-the-go monitoring  
✅ **Free** - no cost for bot API usage  
✅ **Reliable** - Telegram's infrastructure handles delivery  

## Advanced: Multiple Recipients

To send to multiple people, use a Telegram group:

1. Create a new Telegram group
2. Add all recipients to the group
3. Add your bot to the group
4. Use the **group chat ID** (negative number) instead of personal chat ID

Everyone in the group will receive notifications!

## Troubleshooting

### Bot token invalid
- Make sure you copied the entire token from @BotFather
- Token should contain a colon `:` in the middle

### Chat ID not working
- Make sure you sent a message to the bot first
- Try the getUpdates URL again
- For groups, remember the ID is negative (starts with `-`)

### No notifications
- Check that the script runs without errors
- Make sure the bot hasn't been blocked
- Verify both token and chat ID are correct

### Rate limits
- Telegram allows 30 messages per second per bot
- For normal monitoring (every few hours), this is not a concern

## Security Best Practices

1. **Never commit credentials to git**
   ```bash
   echo "*.sh" >> .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use environment variables**
   ```bash
   export TELEGRAM_TOKEN="your_token"
   export TELEGRAM_CHAT_ID="your_chat_id"
   ```

3. **Restrict bot permissions**
   - Bots can only send messages, not read them (unless admin)
   - This is perfect for notifications

4. **Keep token secret**
   - Anyone with your bot token can send messages as your bot
   - Regenerate token via @BotFather if compromised
