# Codex Token Monitor

Local, read-only Codex token monitor for macOS. It parses Codex Desktop/CLI JSONL logs and displays current token usage, 5-hour window usage, weekly window usage, reset times, context usage, alerts, reports, a local dashboard, a compact widget page, and an xbar/SwiftBar-compatible menu bar script.

## Privacy

The parser reads only `event_msg` records where `payload.type == "token_count"`.

It does not display prompt text, assistant output text, tool output text, or auth data. It does not modify `.codex` files and does not send data off-machine.

Runtime token cost: the monitor does not call Codex, OpenAI, or any model API. SwiftBar reads the local SQLite cache with `--no-history-log`, and the dashboard/LAN pages call only this monitor's local `/api/snapshot` HTTP endpoint. This should consume 0 Codex/OpenAI model tokens; it still uses normal local CPU, disk I/O, and optional LAN HTTP traffic when another device opens the phone URL.

## Quick Start

```bash
cd "/Users/linzezhang/Documents/Codex/2026-06-02/new-chat/outputs/codex-usage-monitor"
chmod +x codex-usage menubar/codex-usage.30s.sh
./codex-usage now
```

Expected result:

```text
Codex Token Monitor
Generated: ...
Plan: pro
5h window: ... used, resets ...
Weekly window: ... used, resets ...
Context: ... of ...
1h average burn rate: ...% / hour
Custom average burn rate: ...% / hour over 60 minutes
Total tokens: ...
```

## Commands

Current snapshot:

```bash
./codex-usage now
```

The monitor uses a derived SQLite cache by default:

```text
/Users/linzezhang/.codex_usage_monitor/usage.sqlite
```

This cache stores normalized usage metrics only, not prompt or answer text. To bypass the cache for diagnostics:

```bash
./codex-usage --no-cache now
```

For high-frequency display surfaces such as menu bar plugins, use cache-only mode:

```bash
./codex-usage --cache-only json
./codex-usage menu
```

Full JSON:

```bash
./codex-usage json
```

Generate reports:

```bash
./codex-usage report
```

Outputs:

- `reports/codex_usage_report.json`
- `reports/codex_usage_report.csv`
- `reports/codex_usage_report.md`

Live terminal view:

```bash
./codex-usage watch --interval 5
```

Dashboard and widget:

```bash
./codex-usage dashboard --port 8765
```

Open:

- Dashboard: `http://127.0.0.1:8765/`
- Compact widget: `http://127.0.0.1:8765/widget`

This machine already had port `8765` in use during verification, so the verified running port is `8766`:

```bash
./start-dashboard.sh
```

Open:

- Dashboard: `http://127.0.0.1:8766/`
- Compact widget: `http://127.0.0.1:8766/widget`

Stop:

```bash
./stop-dashboard.sh
```

Start at login:

```bash
./install-launch-agent.sh
```

Remove login start:

```bash
./uninstall-launch-agent.sh
```

## macOS Top Menu

Verified xbar/SwiftBar plugin:

The menu bar script is compatible with xbar or SwiftBar:

```text
/Users/linzezhang/Documents/Codex/2026-06-02/new-chat/outputs/codex-usage-monitor/menubar/codex-usage.30s.sh
```

Install xbar or SwiftBar, then install the menu plugin:

```bash
./install-menubar.sh
```

The menu title shows the remaining 5-hour Codex window allowance, not the used percentage. The `Weekly left` menu row is shown with two decimal places for a more precise weekly-window reading.
Color rules: `>50%` clear blue `#00A3FF`, `10-50%` violet blue `#7C5CFF`, `<10%` red `#FF3B30`. At `0%`, it shows the minutes until the 5-hour window resets.

### Simple Daily Use

SwiftBar is the daily control center. You do not need to remember dashboard commands for normal use.

Open the SwiftBar Codex menu and use:

- `Open dashboard`: opens the local dashboard on this Mac.
- `Refresh`: refreshes the menu data.
- `Phone`: opens or shows the exact phone URL after phone access is running.
- `Start Mac dashboard` / `Start phone access`: only appear when that service is stopped.
- `Stop services`: stops both the local dashboard and the phone-access server.
- `Quit SwiftBar`: quits only the SwiftBar/xbar menu bar app from the Codex plugin home menu.
- `Quit Completely`: stops the local dashboard, stops phone access, writes the disabled marker to prevent auto-restart, and quits SwiftBar/xbar.
- `Resume background monitor`: appears after quitting; removes the disabled marker and starts the dashboard plus phone access again.

The SwiftBar plugin auto-starts the local Mac dashboard on port `8766` when it notices the dashboard is not running. It also auto-starts phone access on port `8767` whenever the local dashboard is running, so the phone URL stays available while monitoring is active.
If the background monitor has been disabled by the low-level quit script, auto-start is disabled until you click `Resume background monitor`.

Phone access:

```text
http://<this-mac-ip>:8767/
```

Example:

```text
http://192.168.0.193:8767/
```

Do not type `192.168.x.x`; that is only a placeholder. Use the exact IP shown by the SwiftBar menu or by macOS Wi-Fi settings.

Optional native Swift menu bar app:

```bash
./build-menubar-app.sh
open "/Users/linzezhang/Documents/Codex/2026-06-02/new-chat/outputs/codex-usage-monitor/macos/CodexUsageMenuBar.app"
```

This requires the local Swift toolchain to compile AppKit apps. On this machine, Swift compilation did not complete during verification, so xbar/SwiftBar is the currently verified menu-bar path.

Manual symlink option:

```bash
mkdir -p "$HOME/Library/Application Support/xbar/plugins"
rm -f "$HOME/Library/Application Support/xbar/plugins/codex-usage.5s.sh"
ln -sf "/Users/linzezhang/Documents/Codex/2026-06-02/new-chat/outputs/codex-usage-monitor/menubar/codex-usage.30s.sh" "$HOME/Library/Application Support/xbar/plugins/codex-usage.30s.sh"
```

The menu title shows the remaining 5-hour Codex window allowance, not the used percentage.

Dashboard pages auto-refresh every 1 minute on the next whole-minute boundary. Widget pages auto-refresh every 1 minute. The dashboard header also has a manual `Refresh` button.
Normal dashboard loads use 10 years of monitor history by default, with a server-side maximum of 10 years. Chart payloads remain capped to keep rendering bounded. The manual `Refresh` button still forces a log sync and can take longer on large local history.
SwiftBar uses a lightweight cache-only menu path with no monitor-history attachment, so the menu bar indicator does not repeatedly pull dashboard history.

Dashboard interface modes:

- `Business`: current standard dashboard content and layout.
- `Light`: reduced summary view with only core quota status, ETA, recommendations, usage-window trend, and alerts.
- `Pro`: full dashboard plus a professional analysis layer for quota posture, burn model, workload concentration, history depth, and action focus.

Dashboard metric definitions:

- `Last Turn Context Pressure`: latest turn token usage divided by the model context window. This is context pressure, not quota usage.
- `1h Avg Credit ETA`: same estimate, but fixed to the past 1-hour average burn rate so it is comparable across refreshes.
- `Custom Avg Burn`: average 5-hour primary-window slope over the dashboard's editable `Last N min` interval. Default is 60 minutes; changing the input refreshes the API with `avg_minutes=N`.
- `Total Token Used`: sum of each session's latest cumulative token count.
- `Past 24h Token Used` / `Past 7d Token Used`: aggregate token growth over rolling 24-hour and 7-day windows from the local token timeline. The card shows observed coverage when local history does not span the full interval.
- `Avg Burn by Time Window`: reset-aware averages for 1h, 5h, 10h, 1d, and 1w windows. This replaces peak-sensitive latest-sample slopes in user-facing views.
- `Usage Window Left Trend`: 5-hour and weekly usage-window remaining-percent trend. It reflects quota allowance left, not total token volume. The display keeps raw logs untouched, then buckets samples into 2-minute intervals and applies reset-aware smoothing so allowance generally falls within a window and jumps up only after an inferred reset. The `24h` view uses a fixed 24-hour time axis and shows observed coverage if the available data is shorter.
- `Usage Window Left Trend` controls: `24h`, custom day, custom week, plus comparison modes. `Previous` is period-over-period comparison; `Last year` is year-over-year when matching local history exists. The chart now includes direct end labels, inline legend, nearest-point hover/tap, click-to-lock detail, `Esc` to clear, a mobile-readable detail strip, and PNG export.
- `Token Used Trendline`: all-session token-used trend plus selectable top-session lines. It supports whole-chart show/hide, per-line selection for All sessions / Baseline / individual session lines, `24h`, custom day, custom week, previous-period comparison, and last-year comparison. Each individual session line is explicitly labeled with its project display name and keeps real path/name-source details in the tooltip. The `24h` view uses a fixed 24-hour time axis. Session labels use the same UI-only display-name rules as Project Ranking: custom alias first, synced chat title second, real path fallback. The chart also supports nearest-point hover/tap, click-to-lock detail, direct line-end labels, a mobile detail strip, and PNG export.
- `Historical Operating Rhythm`: persisted SQLite history from `monitor_samples`, with day/week/all-history views, previous/next controls, a draggable period slider, side-by-side Current/Baseline bars, and custom daily/weekly baseline selectors.
- `Trend Comparison`: token totals, rolling 24h/7d usage, daily/weekly averages, visual current-vs-baseline token comparison, and clickable percentage/number detail rows.
- `Reset countdown`: separate time-left lines for the 5-hour and weekly windows. These show time until reset, while the main bars show quota remaining.

## Data Source

Default paths:

- `/Users/linzezhang/.codex/sessions/**/*.jsonl`
- `/Users/linzezhang/.codex/archived_sessions/*.jsonl`

Useful fields:

- total/input/cached/output/reasoning token counts
- last-turn token count
- last-turn token pressure relative to context window
- primary 5-hour window used percent
- configurable average primary-window burn rate
- reset-aware 1h/5h/10h/1d/1w average burn-rate windows
- secondary weekly window used percent
- reset timestamps
- plan type
- rate-limit reached status

## Accuracy Limits

The monitor reports what Codex writes locally. If Codex does not write an absolute numeric quota, this tool will show percentage remaining rather than inventing an exact token limit. Data updates when Codex writes new `token_count` events.

Codex `total_token_usage` is cumulative per session and can exceed the model context window. For context pressure, this monitor uses `last_token_usage.total_tokens / model_context_window` as a conservative local proxy.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile codex_usage_monitor/*.py
```

## Current Dashboard Metrics

- 5-hour primary Codex window used percent and reset time
- Weekly/secondary Codex window used percent and reset time
- Last-turn context pressure
- 1h credit ETA, custom average burn rate, and reset-aware 1h/5h/10h/1d/1w burn-rate windows
- Total token used plus rolling 24h/7d token usage
- 24h/custom-day/custom-week usage-window left trend chart with fixed 24h time axis
- Optional 24h/custom-day/custom-week token-used trendline with selectable All sessions / Baseline / individual session lines, previous-period/year-over-year comparison, and per-session detail
- Historical operating rhythm with side-by-side current/baseline day and week comparison
- Trend comparison with token summary cards and current/baseline visualization
- recent session table
- project ranking
- daily operating summary with agents and visible-row total
- threshold alerts
