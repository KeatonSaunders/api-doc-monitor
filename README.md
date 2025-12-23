# Deribit API Documentation Monitor

A Python tool to monitor the Deribit API documentation website for changes. The Deribit documentation is a single-page application, so this script tracks changes in individual documentation sections (identified by heading IDs) rather than separate pages.

## Features

- **Section-Based Tracking**: Monitors individual documentation sections (Overview, Authentication, Trading, etc.)
- **Hash-based Change Detection**: Uses SHA-256 hashing for efficient change tracking
- **Persistent State**: Stores previous snapshots in JSON for comparison
- **Detailed Diffs**: Optional text-level diffs showing exactly what changed
- **Rate Limiting**: Respects the server with polite crawling delays

## How It Works

The Deribit documentation (https://docs.deribit.com/) is a single-page application with all content on one page. The script:

1. Fetches the main documentation page
2. Extracts all major sections based on H1 and H2 headings with IDs
3. Tracks each section separately by its ID (e.g., `#overview`, `#public-auth`, etc.)
4. Stores a hash of each section's content
5. Compares with previous run to detect: new sections, modified sections, deleted sections

This approach detects when specific parts of the documentation change (e.g., a new API endpoint is added, or authentication instructions are updated).

## Installation

```bash
pip install -r requirements.txt
```

Requirements:
- Python 3.7+
- requests
- beautifulsoup4

## Usage

### Basic Version (deribit_doc_monitor.py)

**First Run** (establishes baseline):
```bash
python deribit_doc_monitor.py
```

**Subsequent Runs** (checks for changes):
```bash
python deribit_doc_monitor.py
```

**Options:**
```bash
# Use custom storage file
python deribit_doc_monitor.py --storage-file my_state.json

# Save full section content (enables detailed diffs later)
python deribit_doc_monitor.py --save-content
```

### Enhanced Version with Diffs (deribit_doc_monitor_diff.py)

The diff version always saves content and can show what changed:

**Show diffs in console:**
```bash
python deribit_doc_monitor_diff.py --show-diffs
```

**Export diffs to file:**
```bash
python deribit_doc_monitor_diff.py --export-diffs
```

**Combine options:**
```bash
python deribit_doc_monitor_diff.py --show-diffs --export-diffs
```

## Output Example

```
======================================================================
Deribit API Documentation Change Monitor
======================================================================
Fetching documentation from https://docs.deribit.com/...
Found section: Deribit API v2.1.1 (#deribit-api-v2-1-1)
Found section: Overview (#overview)
Found section: Naming (#naming)
Found section: Rate Limits (#rate-limits)
Found section: JSON-RPC (#json-rpc)
Found section: Authentication (#authentication-2)
Found section: /public/auth (#public-auth)
...

Discovered 150 documentation sections
Previous check: 2024-12-20T10:30:00
Checking 150 sections for changes...

[1/150] Checking Deribit API v2.1.1... UNCHANGED
[2/150] Checking Overview... UNCHANGED
[3/150] Checking /public/auth... MODIFIED
[4/150] Checking /private/buy... NEW
...

======================================================================
CHANGE SUMMARY
======================================================================

📄 NEW SECTIONS (2):
  + /private/new_endpoint (#private-new_endpoint)
  + Block RFQ Features (#block-rfq-features)

✏️  MODIFIED SECTIONS (3):
  ~ /public/auth (#public-auth)
    Old hash: 5f4dcc3b5aa765d6...
    New hash: 7c9e6679f7d3c2b8...
  ~ Rate Limits (#rate-limits)
    Old hash: a1b2c3d4e5f6g7h8...
    New hash: 9i8j7k6l5m4n3o2p...

✓ UNCHANGED SECTIONS: 145

⚠️  Total changes: 5

View full documentation at: https://docs.deribit.com/
```

## Storage Format

The state file (`deribit_docs_state.json`) has this structure:

```json
{
  "timestamp": "2024-12-23T10:30:00",
  "sections": {
    "overview": {
      "title": "Overview",
      "hash": "5f4dcc3b5aa765d61d8327deb882cf99",
      "last_checked": "2024-12-23T10:30:00",
      "content": "optional full content if save_content enabled"
    },
    "public-auth": {
      "title": "/public/auth",
      "hash": "a3c5e7f9b1d3g5h7...",
      "last_checked": "2024-12-23T10:30:00"
    }
  }
}
```

## Automation

### Linux/Mac (Cron)

Check for changes daily at 9 AM:
```bash
0 9 * * * cd /path/to/script && python deribit_doc_monitor_diff.py --export-diffs >> monitor.log 2>&1
```

### Windows (Task Scheduler)

Create a batch file `run_monitor.bat`:
```batch
@echo off
cd C:\path\to\script
python deribit_doc_monitor_diff.py --export-diffs >> monitor.log 2>&1
```

Then schedule it in Task Scheduler.

### Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY deribit_doc_monitor_diff.py .
CMD ["python", "deribit_doc_monitor_diff.py", "--export-diffs"]
```

Build and run:
```bash
docker build -t deribit-monitor .
docker run -v $(pwd)/data:/app deribit-monitor
```

## Advanced Usage

### Email Notifications on Changes

Add to your script:

```python
import smtplib
from email.mime.text import MIMEText

def send_notification(changes):
    total_changes = (len(changes['new_sections']) + 
                    len(changes['modified_sections']) + 
                    len(changes['deleted_sections']))
    
    if total_changes > 0:
        body = f"Deribit API Documentation Changes Detected:\n\n"
        body += f"New sections: {len(changes['new_sections'])}\n"
        body += f"Modified sections: {len(changes['modified_sections'])}\n"
        body += f"Deleted sections: {len(changes['deleted_sections'])}\n"
        
        msg = MIMEText(body)
        msg['Subject'] = f'Deribit API Docs Changed ({total_changes} sections)'
        msg['From'] = 'monitor@example.com'
        msg['To'] = 'you@example.com'
        
        with smtplib.SMTP('localhost') as s:
            s.send_message(msg)

# Add to main():
changes = monitor.check_for_changes(save_content=True)
send_notification(changes)
monitor.print_summary(changes)
```

### Webhook Notifications (Slack, Discord)

```python
import requests

def notify_slack(changes):
    total_changes = (len(changes['new_sections']) + 
                    len(changes['modified_sections']) + 
                    len(changes['deleted_sections']))
    
    if total_changes > 0:
        webhook_url = "YOUR_SLACK_WEBHOOK_URL"
        message = {
            "text": f"🔔 Deribit API Documentation Updated",
            "attachments": [{
                "color": "warning",
                "fields": [
                    {"title": "New Sections", "value": str(len(changes['new_sections'])), "short": True},
                    {"title": "Modified", "value": str(len(changes['modified_sections'])), "short": True}
                ]
            }]
        }
        requests.post(webhook_url, json=message)
```

### Track Specific Sections Only

Modify the `discover_pages` method:

```python
def discover_pages(self, max_pages: int = 200) -> Dict[str, str]:
    """Only track specific sections"""
    sections = {}
    
    # Define sections of interest
    target_sections = [
        'authentication-2',
        'public-auth',
        'private-buy',
        'private-sell',
        'rate-limits'
    ]
    
    response = self.session.get(self.base_url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for heading in soup.find_all(['h1', 'h2']):
        section_id = heading.get('id')
        if section_id in target_sections:
            sections[section_id] = heading.get_text(strip=True)
    
    return sections
```

## What Gets Tracked

The script tracks all major documentation sections including:

- **Overview & General Info**: API introduction, naming conventions, rate limits
- **Authentication**: OAuth methods, API keys, signature generation
- **Market Data**: Price indices, order books, trade data, volatility
- **Trading**: Order placement, editing, cancellation, position management
- **Account Management**: Subaccounts, API keys, transaction logs
- **Wallet**: Deposits, withdrawals, transfers
- **Block Trading & RFQ**: Block trade methods and request-for-quote features
- **Subscriptions**: WebSocket channels and real-time data feeds
- **FIX API**: Financial Information eXchange protocol documentation

## Limitations

- Only monitors public documentation (no authentication required)
- Text-based change detection (doesn't track images or downloadable files)
- Requires stable internet connection
- Network restrictions may prevent access in some environments

## Troubleshooting

**Problem**: Script fails to connect
- Check internet connection
- Verify https://docs.deribit.com/ is accessible in your browser
- Check for firewall/proxy issues
- Try running: `curl -I https://docs.deribit.com/`

**Problem**: No sections discovered
- The site structure may have changed
- Check if the site is using a different HTML structure
- Try viewing page source in browser to verify heading IDs exist

**Problem**: Large storage file
- The basic version stores only hashes (very small)
- The diff version stores full content (can be larger)
- Periodically archive old state files

**Problem**: False positives (sections marked as changed when they haven't)
- Minor HTML formatting changes can trigger detection
- Timestamps or dynamic content in the page
- This is normal for hash-based detection

## License

MIT License - feel free to modify and use as needed.

## Contributing

Suggestions and improvements welcome! Consider adding:
- Webhook notifications (Slack, Discord, Teams)
- Database storage instead of JSON
- Section-specific monitoring (only track certain API endpoints)
- Change severity classification (major vs minor changes)
- Historical change tracking and analytics

## Features

- **Automatic Page Discovery**: Crawls the documentation site to find all pages
- **Hash-based Change Detection**: Uses SHA-256 hashing for efficient change tracking
- **Persistent State**: Stores previous snapshots in JSON for comparison
- **Detailed Diffs**: Optional text-level diffs showing exactly what changed
- **Rate Limiting**: Respects the server with polite crawling delays
- **Change Categories**: Tracks new, modified, deleted, and unchanged pages

## Installation

```bash
pip install -r requirements.txt
```

Requirements:
- Python 3.7+
- requests
- beautifulsoup4

## Usage

### Basic Version (deribit_doc_monitor.py)

**First Run** (establishes baseline):
```bash
python deribit_doc_monitor.py
```

**Subsequent Runs** (checks for changes):
```bash
python deribit_doc_monitor.py
```

**Options:**
```bash
# Use custom storage file
python deribit_doc_monitor.py --storage-file my_state.json

# Save full page content (enables detailed analysis later)
python deribit_doc_monitor.py --save-content

# Limit number of pages to check
python deribit_doc_monitor.py --max-pages 100
```

### Enhanced Version with Diffs (deribit_doc_monitor_diff.py)

**Show diffs in console:**
```bash
python deribit_doc_monitor_diff.py --show-diffs
```

**Export diffs to file:**
```bash
python deribit_doc_monitor_diff.py --export-diffs
```

**Combine options:**
```bash
python deribit_doc_monitor_diff.py --show-diffs --export-diffs --max-pages 100
```

## How It Works

1. **Discovery Phase**: The script starts at `https://docs.deribit.com/` and crawls the site, following internal links to discover all documentation pages.

2. **Content Extraction**: For each page, it:
   - Fetches the HTML
   - Removes non-content elements (scripts, styles, navigation)
   - Extracts the text content
   - Generates a SHA-256 hash of the content

3. **Change Detection**: Compares current hashes with previous run:
   - **New**: Page exists now but didn't before
   - **Modified**: Page exists but hash has changed
   - **Deleted**: Page existed before but not now
   - **Unchanged**: Page hash is identical

4. **State Persistence**: Saves current state to JSON file for next comparison.

## Output Example

```
======================================================================
Deribit API Documentation Change Monitor
======================================================================
Discovering documentation pages from https://docs.deribit.com/...
Discovered: https://docs.deribit.com/ (1/50)
Discovered: https://docs.deribit.com/api/ (2/50)
...

Discovered 45 pages
Previous check: 2024-12-20T10:30:00
Checking 45 pages for changes...

[1/45] Checking https://docs.deribit.com/... UNCHANGED
[2/45] Checking https://docs.deribit.com/api/... MODIFIED
[3/45] Checking https://docs.deribit.com/new-endpoint/... NEW
...

======================================================================
CHANGE SUMMARY
======================================================================

📄 NEW PAGES (2):
  + https://docs.deribit.com/new-endpoint/
  + https://docs.deribit.com/new-feature/

✏️  MODIFIED PAGES (3):
  ~ https://docs.deribit.com/api/
    Old hash: 5f4dcc3b5aa765d6...
    New hash: 7c9e6679f7d3c2b8...

✓ UNCHANGED PAGES: 40

⚠️  Total changes: 5
```

## Storage Format

The state file (`deribit_docs_state.json`) has this structure:

```json
{
  "timestamp": "2024-12-23T10:30:00",
  "pages": {
    "https://docs.deribit.com/": {
      "hash": "5f4dcc3b5aa765d61d8327deb882cf99",
      "last_checked": "2024-12-23T10:30:00",
      "content": "optional full content if --save-content used"
    }
  }
}
```

## Automation

### Linux/Mac (Cron)

Check for changes daily at 9 AM:
```bash
0 9 * * * cd /path/to/script && python deribit_doc_monitor_diff.py --export-diffs >> monitor.log 2>&1
```

### Windows (Task Scheduler)

Create a batch file `run_monitor.bat`:
```batch
@echo off
cd C:\path\to\script
python deribit_doc_monitor_diff.py --export-diffs >> monitor.log 2>&1
```

Then schedule it in Task Scheduler.

### Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY deribit_doc_monitor_diff.py .
CMD ["python", "deribit_doc_monitor_diff.py", "--export-diffs"]
```

Build and run:
```bash
docker build -t deribit-monitor .
docker run -v $(pwd)/data:/app/data deribit-monitor
```

## Advanced Usage

### Monitor Specific Pages Only

Modify the `discover_pages` method to target specific sections:

```python
def discover_pages(self, max_pages: int = 50) -> Set[str]:
    # Only monitor API reference pages
    return {
        "https://docs.deribit.com/api/",
        "https://docs.deribit.com/api/authentication/",
        # Add specific pages...
    }
```

### Email Notifications

Add email notification on changes:

```python
import smtplib
from email.mime.text import MIMEText

def send_notification(changes):
    if sum(len(changes[k]) for k in ['new_pages', 'modified_pages', 'deleted_pages']) > 0:
        msg = MIMEText(f"Deribit docs changed: {changes}")
        msg['Subject'] = 'Deribit API Docs Changed'
        msg['From'] = 'monitor@example.com'
        msg['To'] = 'you@example.com'
        
        with smtplib.SMTP('localhost') as s:
            s.send_message(msg)
```

### Integration with Version Control

Save diffs to git:

```bash
#!/bin/bash
python deribit_doc_monitor_diff.py --export-diffs
git add deribit_diffs.txt deribit_docs_state.json
git commit -m "Deribit docs update $(date)"
git push
```

## Limitations

- Only monitors public documentation (no authentication)
- Text-based change detection (doesn't track images, downloads, etc.)
- Requires stable internet connection
- Rate limiting may slow down large crawls

## Troubleshooting

**Problem**: Script fails to connect
- Check internet connection
- Verify https://docs.deribit.com/ is accessible
- Check for firewall/proxy issues

**Problem**: Too many or too few pages discovered
- Adjust `--max-pages` parameter
- Check if site structure has changed

**Problem**: Large storage file
- Don't use `--save-content` unless you need diffs
- Periodically archive old state files

## License

MIT License - feel free to modify and use as needed.

## Contributing

Suggestions and improvements welcome! Consider adding:
- Webhook notifications (Slack, Discord)
- Database storage instead of JSON
- More intelligent diff algorithms
- Specific API endpoint monitoring
