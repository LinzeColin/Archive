# HANDOFF

## Current Goal

Continue optimizing Codex Token Monitor dashboard options 2 and 3:
- Improve Historical Operating Rhythm visualization and comparisons.
- Rename confusing metrics so quota, token, context, and burn-rate concepts are easier to read.

## Current State

- Dashboard service is running on local port `8766`.
- Phone-access service is running on LAN port `8767`.
- Dashboard uses cached API refresh by default and force refresh only from the manual Refresh button.
- Dashboard/phone UI now defaults to 10 years of monitor history. Dashboard auto-refresh is scheduled on whole-minute boundaries, widget auto-refresh is 1 minute, and backend dashboard sync interval is 1 minute. Chart payload caps remain in place to keep rendering bounded.
- Behavior Pattern Analysis now filters out monitor history samples more than 5 minutes in the future, records the current dashboard sample before attaching history to the API response, and defaults Historical Operating Rhythm to the latest day/week unless the user manually pins an older period.
- PR review hardening pass completed after six parallel sub-agent reviews. Blocking issues fixed: full-retention monitor history aggregation, incremental log backfill, atomic same-minute sample de-duplication, LAN API token protection, dashboard `--db/--no-archived` propagation, and hermetic tests.
- LAN dashboard API now requires a generated token for non-local clients. The printed phone URL includes `?token=...`, and dashboard/widget JavaScript carries the token into API requests. Local `127.0.0.1` access remains token-free.
- Widget now calls compact `include_history=0` snapshot mode. Compact mode returns latest/cache/totals/alerts/burn-window fields only and does not record monitor samples or start sync/backfill.
- Monitor history loading streams and aggregates the full retention window; `recent` and `window_samples` remain bounded for rendering.
- Real-time monitor samples use `sample_bucket_at` with a unique `(source, sample_bucket_at)` index to prevent same-source duplicate samples in the same UTC minute.
- `codex_log_backfill` is now incremental instead of a one-time global backfill.
- SwiftBar menu is now lightweight: `--menu-limit 200 --no-history-log`, so menu refreshes no longer attach/load monitor history.
- Monitor history is persisted in SQLite `monitor_samples`; latest API verification found daily and weekly history available.
- SwiftBar menu is intentionally compact: it keeps only 5h reset, weekly left, token total, plan, dashboard open/refresh, phone URL, and stop services. Start actions appear only when the corresponding service is stopped.
- SwiftBar plugin home menu now shows `Quit SwiftBar`, which mirrors the SwiftBar app-level quit action and quits SwiftBar/xbar itself. The previous `Quit background monitor` and `Quit monitor app completely` entries are no longer shown in the plugin home menu.
- SwiftBar plugin home menu now also shows `Quit Completely`. It calls `quit-monitor-app.sh`, which writes the disabled marker, stops local dashboard and phone access, and quits SwiftBar/xbar.
- SwiftBar menu `Total Token Usage` now reads all-time total token usage from SQLite by summing the latest cumulative `total_tokens` per session across the full local history. It no longer uses the recent 200-event menu snapshot or the latest single event's `total_usage`.
- SwiftBar menu `Weekly left` now renders with two decimal places, e.g. `3.00%`, while the title keeps the compact whole-percent 5h remaining display.
- Runtime zero-model-token boundary is now documented and covered by a regression test: runtime sources must not introduce Codex/OpenAI/model API call sites. Local/LAN monitoring reads local logs/SQLite and serves local HTTP only.
- A double-click launcher app exists at `macos/Codex Token Monitor.app` and is symlinked into `~/Downloads`, `~/Desktop`, `~/Applications`, and `/Applications`. It resumes the monitor, starts local/LAN dashboards, opens SwiftBar in the background, and opens the local dashboard.
- User-facing product name is now `Codex Token Monitor`. Dashboard HTML, I18N title, CLI `now`, README, app bundle display name, and app launcher entries were renamed. Underlying project folder and `codex-usage` CLI name remain unchanged for script compatibility.
- App icon assets are now under `assets/icon/`: source PNG `codex-token-monitor-icon-1024.png`, generated `CodexTokenMonitor.icns`, and design note `ICON_DESIGN.md`. The launcher app uses `Contents/Resources/CodexTokenMonitor.icns`.
- Dashboard now has a separate optional `Token Used Trendline` chart. It uses `token_timeline_points[]`, including aggregate token total, per-session token values, real cwd, display name, display-name source, and synced thread name. It now has per-line selection for All sessions, Baseline, and individual top session lines. Individual session lines are explicitly labeled with `Project: <display name>` in the selector, session detail list, and hover tooltip.
- Main canvas charts now follow a more standard interactive chart pattern: inline legends, direct line-end labels, nearest-point hover/tap, click-to-lock details, `Esc` to clear, mobile-readable detail strips, and PNG export buttons. This was implemented without adding a chart library or increasing dashboard background polling.
- `Usage Window Trend` was renamed/reworked to `Usage Window Left Trend`. It now uses `monitor_history.window_samples` and plots remaining allowance, so 5h/weekly lines should generally fall as quota is consumed and rise after reset.
- `Usage Window Left Trend` now applies display-layer cleanup before rendering: 2-minute buckets, max-used aggregation inside each bucket, and reset-aware smoothing. Raw SQLite/log history is not rewritten. Within an inferred window cycle, used percent is made monotonic nondecreasing, so remaining percent no longer bounces upward unless a reset-sized drop is detected.
- `Usage Window Left Trend` now has custom fixed-length interval controls: `5h Window` selects any 5-hour interval by end time, and `24h Window` selects any 24-hour interval by end time. The old fixed latest-24h mode was replaced by custom 5h, and the old calendar-day mode was replaced by custom 24h.
- Layout order is now: Header, Top Metrics, Avg Burn by Time Window, Pro Analysis, Triage Grid, Compact Metrics, Charts, Workload, Lower Grid.
- Top Metrics now has equal 5h/weekly cards, a same-row Context / 1h ETA / Custom Avg Burn group, and total / rolling 24h / rolling 7d token usage cards.
- Interface modes are now semantic density modes: `Business` keeps the current standard content, `Light` keeps only essential summary sections, and `Pro` keeps the full dashboard plus deeper analysis.

## Decisions

- Removed user-facing realtime burn-rate wording because latest-sample slopes can spike and mislead.
- Kept internal realtime fields for compatibility, but CLI/dashboard documentation now emphasize:
  - `1h Avg Credit ETA`
  - `Custom-Window Credit ETA`
  - `Custom Avg Burn`
  - `Avg Burn by Time Window`
- Historical Operating Rhythm now distinguishes Current vs Baseline visually.
- SwiftBar no longer shows duplicate dashboard open/start items, output/reasoning subtotals, or a `No alerts` placeholder when there are no alerts.
- `Usage Window Left Trend` is quota allowance left only: 5h and weekly remaining percentages. It supports custom 5h, custom 24h, custom week, previous-period comparison, and last-year comparison when matching history exists. Custom 5h/24h modes use a fixed time axis and show observed coverage instead of stretching short data across the full chart.
- Window-trend smoothing is UI/display-only. Because `monitor_samples` does not persist per-sample reset timestamps, reset detection is inferred from significant used-percent drops. If audit-grade historical reset accuracy is needed, add `primary_resets_at` and `secondary_resets_at` to `monitor_samples` and backfill them from event rows.
- `Token Used Trendline` is token volume and is intentionally separate. It supports whole-chart show/hide, per-line selection, 24h, custom day, custom week, previous-period comparison, last-year comparison when matching history exists, and top-session detail. The 24h view also uses a fixed time axis.
- `Token Mix` chart was removed from the dashboard.
- Historical Operating Rhythm now renders Current and Baseline bars side by side rather than overlapping.
- Historical Operating Rhythm has a `Latest` control. Mode switching returns to latest automatically; previous/next/slider/baseline selection pins the selected historical period until `Latest` or mode switching resets it.
- Historical Operating Rhythm baseline selectors no longer switch the main day/week mode or pin the current period.
- Project Ranking now includes backend `latest_reasoning_tokens_sum`.
- Daily Operating Summary now includes an `agents` column and a visible-row total row.
- Legacy `cute` localStorage values map to `light`; legacy `engineering` values map to `pro`.
- Monitoring should not consume Codex model tokens directly; it reads local logs/SQLite. The user explicitly requested 10-year default history and 1-minute dashboard refresh, so this supersedes the previous lightweight 14-day/5-minute profile.
- Visualization interaction direction: preserve visible values without hover where possible, then use details-on-demand for exact values. Avoid adding heavy libraries unless the existing Canvas/DOM implementation becomes a blocker.

## Files Changed

- `static/app.js`
- `static/styles.css`
- `static/index.html`
- `static/widget.js`
- `static/widget.html`
- `codex_usage_monitor/cli.py`
- `codex_usage_monitor/storage.py`
- `tests/test_parser_metrics.py`
- `README.md`
- `menubar/codex-usage.30s.sh`
- `quit-background-monitor.sh`
- `quit-monitor-app.sh`
- `quit-swiftbar.sh`
- `resume-background-monitor.sh`
- `install-menubar.sh`
- `install-app-entry.sh`
- `macos/Codex Token Monitor.app`
- `assets/icon/ICON_DESIGN.md`
- `assets/icon/codex-token-monitor-icon-1024.png`
- `assets/icon/CodexTokenMonitor.icns`
- `codex_usage_monitor/metrics.py`
- `codex_usage_monitor/models.py`

## Verification

- `node --check static/app.js`: passed after the Behavior Pattern Analysis update.
- `node --check static/widget.js`: passed.
- `python3 -m py_compile codex_usage_monitor/*.py`: passed.
- `python3 -m unittest tests/test_parser_metrics.py`: 12 tests passed after PR review hardening.
- Live API verification after dashboard restart: `monitor_history.last_sample_at` updated to the current read window, latest daily row is `2026-06-05`, and `history_days=3650` still works.
- Headless Chrome page verification using local Google Chrome: dashboard loaded without console errors, Behavior Pattern Analysis rendered, `Latest` button exists, and `Last record` showed the current local evening timestamp.
- Static cache-buster updated and verified: dashboard serves `app.js?v=20260605p`; widget serves `widget.js?v=20260605c`.
- LAN auth smoke passed: LAN API without token returned `403`; LAN API with generated token returned `200`.
- Compact API smoke passed: `include_history=0` returned about 3KB, did not include `monitor_history` or `sessions`, and exposed only latest/cache/totals/alerts/burn-window fields.
- Full API smoke passed after hardening: `history_days=3650` returned `200`, `monitor_history.last_sample_at` current to the live run, `window_samples=5000`, `token_timeline_points=5000`, and daily history present.
- Dashboard services restarted successfully: local `127.0.0.1:8766` and LAN `0.0.0.0:8767` are listening; current phone URL is `http://192.168.0.193:8767/?token=<local-token>`.
- API snapshot returned latest event, daily history, weekly history, and burn windows `1h,5h,10h,1d,1w`.
- `./codex-usage now` output no longer shows `Realtime burn rate`; it shows `1h average burn rate` and `Custom average burn rate`.
- `menubar/codex-usage.30s.sh` syntax check passed and sample menu output showed the compact structure.
- `Token Used Trendline` resource/version check passed. API returned 19534 `token_timeline_points` after dashboard restart, and static HTML contains the token trend show/hide toggle.
- `Usage Window Left Trend` resource/version check passed, and API returned `monitor_history.window_samples` with 16047 samples after dashboard restart.
- `Usage Window Left Trend` smoothing check on live snapshot: raw 16243 window samples bucketed to 1184 chart points. 5h upward jumps >1pp dropped from 3740 raw jumps to 18 clean jumps, corresponding to inferred resets. Weekly upward jumps >1pp dropped from 980 raw jumps to 2 clean jumps. Downward moves are retained because they represent quota consumption.
- Browser background check loaded the dashboard title and new app script without a dashboard error. Waiting for the async subtitle update timed out because the full API snapshot can still take around 15-45 seconds when history is large.
- Interface mode/resource check passed: running dashboard HTML contains token trend controls/session breakdown/line selector, `Business`, `Light`, `Pro`, and `Token Mix` is absent.
- API verification confirmed `daily[].agents` is present; latest checked row had `agents=8`.
- Current 10-year profile target: `history_days=3650`, server-side maximum `3650`, backend refresh interval `60` seconds, frontend dashboard refresh aligned to whole-minute boundaries.
- Current 10-year profile verification passed: API request with `history_days=3650` returned `retention_days=3650`, `refresh_interval_seconds=60`, `window_samples=5000`, and `token_timeline_points=5000` in about 23.7 seconds.
- Dashboard frontend requests `history_days=3650` and schedules aligned whole-minute refreshes.
- SwiftBar menu lightweight command `./codex-usage menu --menu-limit 200 --no-history-log` completed in about 0.9 seconds and did not attach monitor history.
- Usage Window custom interval update verification passed: `node --check static/app.js`, `node --check static/widget.js`, `python3 -m py_compile codex_usage_monitor/*.py`, and `python3 -m unittest tests/test_parser_metrics.py` passed. API snapshot returned `200` in about 1.9s; latest 5h interval had 318 window samples and latest 24h interval had 5000 available samples.
- Background quit menu update verification passed: `bash -n menubar/codex-usage.30s.sh quit-background-monitor.sh resume-background-monitor.sh install-menubar.sh stop-dashboard.sh start-dashboard.sh start-dashboard-lan.sh`, `python3 -m unittest tests/test_parser_metrics.py`, and `python3 -m py_compile codex_usage_monitor/*.py` passed. Test runs used high unused ports and did not stop the real services.
- SwiftBar quit menu update verification passed: normal and disabled menu outputs include `Quit SwiftBar`, and no longer include `Quit background monitor` or `Quit monitor app completely`. SwiftBar was restarted to reload the plugin; local `8766` and LAN `8767` services remained listening afterward.
- Complete quit and all-time menu token update verification passed: normal and disabled menu outputs include `Quit Completely` and `Quit SwiftBar`; home menu no longer exposes `Quit background monitor`; `./codex-usage menu --menu-limit 200 --no-history-log` shows `Total Token Usage: 3.84B`; 13 unit tests, Python compile, and shell syntax checks passed. SwiftBar was restarted to reload the plugin, and 8766/8767 remained listening.
- Rename/icon verification passed: dashboard serves `Codex Token Monitor` and `app.js?v=20260607a`; `./codex-usage now` prints `Codex Token Monitor`; `plutil -lint` passed; iconset extraction from `CodexTokenMonitor.icns` produced expected files; app symlinks exist in Downloads, Desktop, user Applications, and `/Applications`; `node --check static/app.js`, `node --check static/widget.js`, `python3 -m py_compile codex_usage_monitor/*.py`, and 12 unit tests passed.
- Weekly precision and zero-token boundary verification passed: `./codex-usage menu --menu-limit 200 --no-history-log` showed `Weekly left: 3.00%` and `Total Token Usage: 3.84B`; `python3 -m unittest tests/test_parser_metrics.py` ran 14 tests OK, including the no-model-API runtime boundary test; `python3 -m py_compile codex_usage_monitor/*.py`, `node --check static/app.js`, `node --check static/widget.js`, and shell syntax checks passed. SwiftBar plugin was reinstalled/touched, and ports `8766`/`8767` remained listening.

## Open Issues

- Bundled Playwright package was present but its managed browser binary was not installed. Verification used local Google Chrome headless instead, without installing new packages.
- Dashboard API/full snapshot is still heavy with the current 20k token timeline plus 16k window samples. CLI cache-only JSON took about 15.7 seconds in the latest check, and browser waiting can time out before async data rendering. Consider adding a lighter dashboard API payload or lazy-loading heavy chart histories.
- With 10-year default history restored, dashboard snapshots can be heavy again. Chart payload caps remain, but manual Refresh and first load can still be slow on very large local history.
- Latest API check for chart-interaction work timed out before valid JSON at a 20-second cap, so this round relied on static resource verification, JS syntax checks, Python compile, and unit tests. The endpoint and services remained listening.
- No Git repository exists in this output directory, so changes are tracked by file list rather than git diff.

## Next Steps

- Re-check the dashboard visually in the normal browser after refresh.
- If needed, add a lightweight test harness that renders the dashboard with mocked API data rather than using live Chrome `--dump-dom`.
- Continue refining mobile layout only after visual inspection shows a concrete issue.

## Boundaries

- Do not rename real Codex workspace folders.
- Do not modify archived session logs.
- Display names are UI-only; real paths remain the source of truth for Codex runtime stability.
