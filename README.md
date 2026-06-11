# BTC Binary Options Probe

Browser-automated execution precision testing for binary options platforms.  
Maps UI elements, measures click-to-fill latency, collects execution data for signal matching.

## Platforms Tracked

| Platform | Status | 60s BTC | Demo | 
|----------|--------|---------|------|
| Pocket Option | 🔍 mapping | ✅ | ✅ |
| Olymp Trade | ⬜ pending | ✅ | ✅ |
| CloseOption | ⬜ pending | ✅ | ✅ |

## Project Structure

```
src/
├── platforms/     # Per-platform UI mappers (browser-harness)
│   ├── base.py        # Abstract platform interface
│   └── pocket_option.py
├── probes/        # Execution timing probes
│   └── execution_probe.py
└── utils/         # Browser wrapper, logging, helpers
    ├── browser.py
    └── logger.py

scripts/
├── map_platform.py    # Map a platform's UI elements
└── run_probe.py       # Run execution probe against mapped platform

data/               # Collected execution data (CSV)
```

## Setup

```bash
pip install -r requirements.txt
```

Chrome debug mode must be running:
```powershell
$env:BU_CDP_URL="http://127.0.0.1:9222"
```

## Workflow

1. **Map platform** → `python scripts/map_platform.py --platform pocket_option`
2. **Run probe** → `python scripts/run_probe.py --platform pocket_option --rounds 50`
3. **Analyze data** → `data/` directory contains CSVs

## Execution Metrics Collected

- `click_to_ui_response_ms` — time from clicking BUY/SELL to UI confirmation
- `click_to_fill_ms` — time from click to server-acknowledged fill
- `ticket_display_ms` — time until trade ticket shows in history
- `result_delivery_ms` — time expiry → result shown
- `slippage` — price difference at click vs fill (if detectable)
- `network_latency_rtt` — WebSocket RTT estimate

## Handoff to Codex

After mapping is complete, this repo is designed to be handed off to Codex CLI for:
- Strategy engine integration
- Signal-input bridging
- Paper-trade automation
- Risk management logic
