# Exchange API Documentation Monitors

Monitor cryptocurrency exchange API documentation for changes and receive Telegram notifications.

## Directory Structure

```
scraper/
├── monitors/              # Monitor implementations
│   ├── __init__.py       # Package initialization
│   ├── base_monitor.py   # Base class with common functionality
│   ├── binance.py        # Binance monitor
│   ├── bybit.py          # Bybit monitor
│   ├── deribit.py        # Deribit monitor
│   ├── hyperliquid.py    # Hyperliquid monitor
│   └── okx.py            # OKX monitor
├── state/                # State files (JSON)
│   ├── binance_docs_state.json
│   ├── bybit_docs_state.json
│   ├── deribit_docs_state.json
│   ├── hyperliquid_docs_state.json
│   └── okx_docs_state.json
├── config.json           # Telegram configuration
├── run_all.py            # Master script to run all monitors
└── README.md             # This file
```

## Supported Exchanges

- **Binance** - Spot & Derivatives changelog
- **Bybit** - Full documentation site
- **Deribit** - API changelog
- **Hyperliquid** - API, Trading, and HyperCore docs
- **OKX** - Upcoming changes only

## Quick Start

```bash
# Run all monitors
python run_all.py --config config.json

# Run specific exchanges
python run_all.py --exchanges binance okx

# Run individual monitor
python -m monitors.binance --config config.json
```

See full documentation in the README for more details.
