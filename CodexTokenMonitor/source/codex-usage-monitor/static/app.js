const fmtPercent = (value, digits = 1) => value === null || value === undefined || Number.isNaN(Number(value)) ? "--" : `${Number(value).toFixed(digits)}%`;
const fmtTokens = (value) => {
  value = Number(value || 0);
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(value);
};
const fmtTime = (iso) => iso ? new Date(iso).toLocaleString() : "--";
const fmtSignedFixed = (value, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  const number = Number(value);
  const locale = currentLang === "zh" ? "zh-CN" : "en-US";
  return `${number >= 0 ? "+" : ""}${number.toLocaleString(locale, {minimumFractionDigits: digits, maximumFractionDigits: digits})}`;
};
const fmtDelta = (item, mode = "percent") => {
  if (!item) return "--";
  if (mode === "absolute") return fmtSignedFixed(item.absolute, 2);
  if (item.percent === null || item.percent === undefined || Number.isNaN(Number(item.percent))) return "--";
  const number = Number(item.percent);
  return `${number >= 0 ? "+" : ""}${number.toFixed(1)}%`;
};
const byId = (id) => document.getElementById(id);
const setText = (id, value) => {
  const el = byId(id);
  if (el) el.textContent = value;
};
const safe = (value, fallback = "--") => value === null || value === undefined ? fallback : value;
const escapeHtml = (value) => String(value ?? "--").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[ch]));
const remaining = (used) => used === null || used === undefined ? null : Math.max(0, 100 - Number(used));
const remainingColor = (value) => value === null ? "#98a2b3" : value > 50 ? "#00a3ff" : value >= 10 ? "#7c5cff" : "#ff3b30";
const usedColor = (value) => value >= 95 ? "#b42318" : value >= 85 ? "#d92d20" : "#22577a";
const REFRESH_INTERVAL_MS = 60000;
let refreshInFlight = false;
let latestSnapshot = null;
let intervalRefreshTimer = null;
let alignedRefreshTimer = null;
let currentLang = "en";
const INTERFACE_STYLE_STORAGE_KEY = "codexUsageInterfaceStyleV2";
let currentInterfaceStyle = normalizeInterfaceStyle(localStorage.getItem(INTERFACE_STYLE_STORAGE_KEY) || "business");
const COMPARISON_FORMAT_STORAGE_KEY = "codexUsageTrendComparisonFormatV1";
let comparisonFormat = localStorage.getItem(COMPARISON_FORMAT_STORAGE_KEY) === "absolute" ? "absolute" : "percent";
const OPERATING_RHYTHM_MODE_STORAGE_KEY = "codexUsageOperatingRhythmModeV1";
let operatingRhythmMode = localStorage.getItem(OPERATING_RHYTHM_MODE_STORAGE_KEY) || "day";
let operatingRhythmIndex = {day: null, week: null};
let operatingRhythmPinned = {day: false, week: false};
let operatingRhythmCompare = {day: null, week: null};
const WINDOW_TREND_MODE_STORAGE_KEY = "codexUsageWindowTrendModeV1";
const WINDOW_TREND_RANGE_END_STORAGE_KEY = "codexUsageWindowTrendRangeEndV1";
let windowTrendMode = normalizeWindowTrendMode(localStorage.getItem(WINDOW_TREND_MODE_STORAGE_KEY) || "fiveHour");
let windowTrendPeriod = {day: null, week: null};
let windowTrendRangeEnd = loadWindowTrendRangeEnd();
let windowTrendCompareMode = {fiveHour: "previous", day: "previous", week: "previous"};
const WINDOW_TREND_BUCKET_MS = 2 * 60 * 1000;
const WINDOW_TREND_RESET_DROP = {primary: 12, secondary: 30};
const TOKEN_TREND_MODE_STORAGE_KEY = "codexUsageTokenTrendModeV1";
let tokenTrendMode = localStorage.getItem(TOKEN_TREND_MODE_STORAGE_KEY) || "recent";
let tokenTrendPeriod = {day: null, week: null};
let tokenTrendCompareMode = {day: "previous", week: "previous"};
const TOKEN_TREND_VISIBLE_STORAGE_KEY = "codexUsageTokenTrendVisibleV1";
let tokenTrendVisible = localStorage.getItem(TOKEN_TREND_VISIBLE_STORAGE_KEY) !== "0";
const TOKEN_TREND_LINES_STORAGE_KEY = "codexUsageTokenTrendLinesV1";
let tokenTrendLineSelection = loadTokenTrendLineSelection();
const CHART_HIT_AREAS = new WeakMap();
let chartTooltipEl = null;
let pinnedChart = null;
const dashboardAccessToken = new URLSearchParams(window.location.search).get("token") || "";

function withAccessToken(params) {
  if (dashboardAccessToken) params.set("token", dashboardAccessToken);
  return params;
}

const I18N = {
  en: {
    title: "Codex Token Monitor",
    eyebrow: "Local Read-Only Monitor",
    appTitle: "Codex Token Monitor",
    refresh: "Refresh",
    refreshing: "Refreshing",
    waiting: "Waiting for data",
    noData: "No data found",
    plan: "Plan",
    updated: "Updated",
    rendered: "Rendered",
    dataRead: "Data read",
    latestEvent: "Latest event",
    syncing: "Syncing",
    left: "left",
    reset: "Reset",
    resetCountdown: "Reset countdown",
    timeLeft: "time left",
    primaryTitle: "5h Window Left",
    secondaryTitle: "Weekly Window Left",
    contextTitle: "Last Turn Context Pressure",
    estimatedTimeTitle: "Custom-Window Credit ETA",
    estimatedTimeStable: "Stable",
    estimatedTimeNow: "Now",
    estimatedTimeFoot: "Based on last {minutes} min average burn",
    oneHourCreditEtaTitle: "1h Avg Credit ETA",
    oneHourCreditEtaFoot: "Based on past 1h average burn",
    averageBurnTitle: "Custom Avg Burn",
    totalTokenUsed: "Total Token Used",
    pastDayTokenUsed: "Past 24h Token Used",
    pastWeekTokenUsed: "Past 7d Token Used",
    observedCoverage: "Observed coverage",
    burnWindowsTitle: "Avg Burn by Time Window",
    burnWindowsSubtitle: "1h / 5h / 10h / 1d / 1w",
    burnWindowDelta: "Delta",
    burnWindowCoverage: "Coverage",
    burnWindowSamples: "Samples",
    noBurnWindowData: "No burn-rate window data.",
    lastLabel: "Last",
    minutesShort: "min",
    trendComparison: "Trend Comparison",
    dodWow: "DoD / WoW",
    comparisonPercentMode: "Percent view",
    comparisonAbsoluteMode: "Number view",
    comparisonClickHint: "Click to switch format",
    behaviorAnalysis: "Behavior Pattern Analysis",
    localHistory: "Local history",
    recommendations: "Recommendations",
    operationalAdvice: "Operational advice",
    sessions: "Sessions",
    threadsWorking: "Threads Working",
    agentsActivated: "Agents Activated",
    projectsWorking: "Projects Working",
    activeThreads: "active threads",
    activeAgents: "active agents",
    activeProjects: "active projects",
    tokenEvents: "Token Events",
    parsedFromLogs: "Parsed from local Codex logs",
    uploadSum: "Upload Token Sum",
    downloadSum: "Download Token Sum",
    contextualSum: "Contextual Token Sum",
    reasoningSum: "Reasoning Token Sum",
    latestPerSession: "Latest per session",
    tokenMix: "Token Mix",
    windowTrend: "Usage Window Left Trend",
    windowTrendSubtitle: "5h / weekly left %",
    windowTrendQuality: "reset-aware smoothed",
    windowTrendModeFiveHour: "5h Window",
    windowTrendModeDayWindow: "24h Window",
    windowTrendEnd: "Window end",
    trendModeRecent: "24h",
    trendModeDay: "Day",
    trendModeWeek: "Week",
    trendPeriod: "Period",
    trendCompare: "Compare",
    trendCompareNone: "None",
    trendComparePrevious: "Previous",
    trendCompareYear: "Last year",
    trendCurrent: "Current",
    trendBaseline: "Baseline",
    tokenUsedTrend: "Token Used Trendline",
    tokenUsedTrendSubtitle: "All-session token total",
    showTokenTrend: "Show token trendline",
    tokenTrendLines: "Lines",
    aggregateLine: "All sessions",
    baselineLine: "Baseline",
    sessionLines: "Session lines",
    noLinesSelected: "No token lines selected.",
    downloadPng: "PNG",
    resetFocus: "Clear focus",
    chartInteractionHint: "Hover or tap for nearest point. Click/tap locks detail; Esc clears.",
    selectedPoint: "Selected point",
    fiveHourLine: "5h left",
    weeklyLine: "Weekly left",
    lineProject: "Project",
    tokenSessionBreakdown: "Session token detail",
    tokenTrendAllSessions: "All sessions",
    tokenTrendTopSessions: "Top sessions",
    tokenTrendNoSessionData: "No session token data in this period.",
    sessionLine: "Session line",
    last24h: "Last 24h",
    timeline: "Timeline",
    projectRanking: "Project Ranking",
    project: "Project",
    displayName: "Display Name",
    realPath: "Real Path",
    nameSource: "Name Source",
    syncedThreadNames: "Synced Chat Names",
    threads: "Threads",
    agents: "Agents",
    working: "Working",
    burnRate: "Token Burn / h",
    tokenUsed: "Token Used",
    active: "Active",
    tokens: "Tokens",
    dailySummary: "Daily Operating Summary",
    date: "Date",
    events: "Events",
    tokenSum: "Token Sum",
    total: "Total",
    dailyAvg: "Daily avg",
    weeklyAvg: "Weekly avg",
    past24h: "Past 24h",
    past7d: "Past 7d",
    recentSessions: "Recent Sessions",
    status: "Status",
    lastUpdate: "Last update",
    alerts: "Alerts",
    upload: "Upload",
    cachedUpload: "Cached Upload",
    download: "Download",
    contextual: "Contextual",
    reason: "Reasoning",
    dod: "DoD",
    wow: "WoW",
    window: "Window",
    activeLabel: "active",
    idleLabel: "idle",
    ok: "OK",
    noThresholdAlerts: "No threshold alerts.",
    dashboardError: "Dashboard error",
    noPatternData: "No pattern data",
    moreHistoryNeeded: "More history is needed.",
    noRecommendations: "No recommendations",
    usageStable: "Current usage looks stable.",
    languageLabel: "Language",
    styleBusiness: "Business",
    styleLight: "Light",
    stylePro: "Pro",
    proAnalysis: "Pro Analysis",
    proAnalysisSubtitle: "Quota, flow, concentration, history",
    proQuotaPosture: "Quota Posture",
    proBurnModel: "Burn Model",
    proWorkloadConcentration: "Workload Concentration",
    proHistoryDepth: "History Depth",
    proActionFocus: "Action Focus",
    activePressure: "Active Session Pressure",
    projectConcentration: "Project Concentration",
    uploadShare: "Upload Share",
    downloadShare: "Download Share",
    contextualShare: "Contextual Share",
    reasoningShare: "Reasoning Share",
    operatingRhythm: "Historical Operating Rhythm",
    last24hEvents: "Last 24h token events",
    historicalSamples: "Historical samples",
    monitorSamples: "Monitor samples",
    backfilledSamples: "Backfilled log samples",
    historySince: "Since",
    lastRecord: "Last record",
    historySource: "Persistent SQLite history",
    historyModeDay: "Day",
    historyModeWeek: "Week",
    historyModeAll: "All",
    previousPeriod: "Previous",
    nextPeriod: "Next",
    latestPeriod: "Latest",
    selectedPeriod: "Selected period",
    compareWith: "Baseline",
    currentPeriod: "Current period",
    comparisonPeriod: "Baseline period",
    dailyComparison: "Daily baseline",
    weeklyComparison: "Weekly baseline",
    hourDetails: "Hour details",
    sampleShare: "Share of period",
    hoverClickBar: "Hover or click a bar to inspect details",
    samplesDelta: "Sample delta",
    activeSamples: "Active samples",
    current: "Current",
    baseline: "Baseline",
    currentPeak: "Current peak",
    baselinePeak: "Baseline peak",
    noComparisonPeriod: "No comparison period",
    allHistory: "All history",
    peakHour: "Peak hour",
    pressureHigh: "High",
    pressureNormal: "Normal",
    largestProjectShare: "Largest project share",
    representativeTrafficMix: "Representative traffic mix",
  },
  zh: {
    title: "Codex Token Monitor",
    eyebrow: "本地只读监控",
    appTitle: "Codex Token Monitor",
    refresh: "刷新",
    refreshing: "刷新中",
    waiting: "等待数据",
    noData: "未找到数据",
    plan: "套餐",
    updated: "已更新",
    rendered: "已渲染",
    dataRead: "数据读取",
    latestEvent: "最新事件",
    syncing: "同步中",
    left: "剩余",
    reset: "重置",
    resetCountdown: "重置倒计时",
    timeLeft: "剩余时间",
    primaryTitle: "5小时窗口剩余",
    secondaryTitle: "每周窗口剩余",
    contextTitle: "最近一轮上下文压力",
    estimatedTimeTitle: "自定义均速额度预计",
    estimatedTimeStable: "稳定",
    estimatedTimeNow: "已耗尽",
    estimatedTimeFoot: "基于过去 {minutes} 分钟平均消耗",
    oneHourCreditEtaTitle: "1小时均速额度预计",
    oneHourCreditEtaFoot: "基于过去1小时平均消耗",
    averageBurnTitle: "自定义平均消耗",
    totalTokenUsed: "Token 总使用量",
    pastDayTokenUsed: "过去24小时 Token 使用量",
    pastWeekTokenUsed: "过去7天 Token 使用量",
    observedCoverage: "已观测覆盖",
    burnWindowsTitle: "分窗口平均消耗",
    burnWindowsSubtitle: "1小时 / 5小时 / 10小时 / 1天 / 1周",
    burnWindowDelta: "增量",
    burnWindowCoverage: "覆盖",
    burnWindowSamples: "样本",
    noBurnWindowData: "暂无多窗口消耗速率数据。",
    lastLabel: "过去",
    minutesShort: "分钟",
    trendComparison: "趋势对比",
    dodWow: "日环比 / 周环比",
    comparisonPercentMode: "百分比视图",
    comparisonAbsoluteMode: "数字视图",
    comparisonClickHint: "点击切换格式",
    behaviorAnalysis: "行为模式分析",
    localHistory: "本地历史",
    recommendations: "建议",
    operationalAdvice: "操作建议",
    sessions: "会话",
    threadsWorking: "运行中 Threads",
    agentsActivated: "已激活 Agents",
    projectsWorking: "运行中 Projects",
    activeThreads: "活跃 thread",
    activeAgents: "活跃 agent",
    activeProjects: "活跃 project",
    tokenEvents: "词元事件",
    parsedFromLogs: "从本地 Codex 日志解析",
    uploadSum: "上传 Token 合计",
    downloadSum: "下载 Token 合计",
    contextualSum: "上下文 Token 合计",
    reasoningSum: "推理 Token 合计",
    latestPerSession: "每个会话最新值",
    tokenMix: "词元结构",
    windowTrend: "用量窗口剩余趋势",
    windowTrendSubtitle: "5小时 / 每周剩余百分比",
    windowTrendQuality: "按 reset 逻辑平滑",
    windowTrendModeFiveHour: "5小时窗口",
    windowTrendModeDayWindow: "24小时窗口",
    windowTrendEnd: "窗口结束",
    trendModeRecent: "24小时",
    trendModeDay: "按日",
    trendModeWeek: "按周",
    trendPeriod: "区间",
    trendCompare: "对比",
    trendCompareNone: "无",
    trendComparePrevious: "环比",
    trendCompareYear: "同比",
    trendCurrent: "当前",
    trendBaseline: "基准",
    tokenUsedTrend: "Token 已用趋势线",
    tokenUsedTrendSubtitle: "全部会话 Token 合计",
    showTokenTrend: "显示 Token 趋势线",
    tokenTrendLines: "线条",
    aggregateLine: "全部会话",
    baselineLine: "基准线",
    sessionLines: "会话线",
    noLinesSelected: "未选择任何 Token 线条。",
    downloadPng: "PNG",
    resetFocus: "清除选中",
    chartInteractionHint: "悬停或轻点查看最近数据点。点击/轻点可锁定详情；Esc 清除。",
    selectedPoint: "选中数据点",
    fiveHourLine: "5小时剩余",
    weeklyLine: "每周剩余",
    lineProject: "项目",
    tokenSessionBreakdown: "会话 Token 明细",
    tokenTrendAllSessions: "全部会话",
    tokenTrendTopSessions: "Top 会话",
    tokenTrendNoSessionData: "当前区间没有会话 Token 数据。",
    sessionLine: "会话线",
    last24h: "过去24小时",
    timeline: "时间轴",
    projectRanking: "项目排行",
    project: "项目",
    displayName: "显示名",
    realPath: "真实路径",
    nameSource: "名称来源",
    syncedThreadNames: "同步聊天名",
    threads: "Threads",
    agents: "Agents",
    working: "运行中",
    burnRate: "Token 消耗/h",
    tokenUsed: "已用 Token",
    active: "活跃",
    tokens: "词元",
    dailySummary: "每日运行摘要",
    date: "日期",
    events: "事件",
    tokenSum: "词元合计",
    total: "总计",
    dailyAvg: "日均",
    weeklyAvg: "周均",
    past24h: "过去24小时",
    past7d: "过去7天",
    recentSessions: "最近会话",
    status: "状态",
    lastUpdate: "最后更新",
    alerts: "警报",
    upload: "上传",
    cachedUpload: "缓存上传",
    download: "下载",
    contextual: "上下文",
    reason: "推理",
    dod: "日环比",
    wow: "周环比",
    window: "窗口",
    activeLabel: "活跃",
    idleLabel: "空闲",
    ok: "正常",
    noThresholdAlerts: "没有阈值警报。",
    dashboardError: "仪表盘错误",
    noPatternData: "暂无模式数据",
    moreHistoryNeeded: "需要更多历史数据。",
    noRecommendations: "暂无建议",
    usageStable: "当前用量稳定。",
    languageLabel: "语言",
    styleBusiness: "商务",
    styleLight: "轻量",
    stylePro: "专业",
    proAnalysis: "专业分析",
    proAnalysisSubtitle: "额度、流量、集中度、历史",
    proQuotaPosture: "额度状态",
    proBurnModel: "消耗模型",
    proWorkloadConcentration: "工作负载集中度",
    proHistoryDepth: "历史深度",
    proActionFocus: "行动重点",
    activePressure: "活跃会话压力",
    projectConcentration: "项目集中度",
    uploadShare: "上传占比",
    downloadShare: "下载占比",
    contextualShare: "上下文占比",
    reasoningShare: "推理占比",
    operatingRhythm: "历史运行节奏",
    last24hEvents: "过去24小时词元事件",
    historicalSamples: "历史样本",
    monitorSamples: "监控样本",
    backfilledSamples: "日志回填样本",
    historySince: "开始于",
    lastRecord: "最后记录",
    historySource: "SQLite 持久化历史",
    historyModeDay: "按天",
    historyModeWeek: "按周",
    historyModeAll: "全部",
    previousPeriod: "上一段",
    nextPeriod: "下一段",
    latestPeriod: "最新",
    selectedPeriod: "当前区间",
    compareWith: "基准",
    currentPeriod: "当前区间",
    comparisonPeriod: "基准区间",
    dailyComparison: "每日基准",
    weeklyComparison: "每周基准",
    hourDetails: "小时详情",
    sampleShare: "区间占比",
    hoverClickBar: "鼠标悬停或点击柱子查看详情",
    samplesDelta: "样本变化",
    activeSamples: "活跃样本",
    current: "当前",
    baseline: "基准",
    currentPeak: "当前高峰",
    baselinePeak: "基准高峰",
    noComparisonPeriod: "没有可对比区间",
    allHistory: "全部历史",
    peakHour: "高峰时段",
    pressureHigh: "偏高",
    pressureNormal: "正常",
    largestProjectShare: "最大项目占比",
    representativeTrafficMix: "代表性流量结构",
  },
};

const TOOLTIPS = {
  en: {
    plan: "The Codex plan type reported by local token_count events.",
    rendered: "When this dashboard view was rendered from the current snapshot.",
    dataRead: "When the dashboard last synchronized and read local Codex usage data.",
    latestEvent: "Timestamp of the latest token_count event found in local Codex logs.",
    primaryTitle: "Remaining capacity in the rolling 5-hour usage window. Higher remaining capacity is better.",
    secondaryTitle: "Remaining capacity in the weekly usage window.",
    contextTitle: "How much of the model context window the latest turn used.",
    estimatedTimeTitle: "Estimated time until the 5-hour window reaches 0 using the custom Last N min average burn rate.",
    oneHourCreditEtaTitle: "Estimated time until the 5-hour window reaches 0 using the fixed past-1-hour average burn rate.",
    averageBurnTitle: "Custom average 5-hour usage-window slope over the editable Last N min interval.",
    totalTokenUsed: "Sum of each session's latest cumulative token count.",
    pastDayTokenUsed: "Aggregate token growth over the latest rolling 24-hour interval from local token timeline data.",
    pastWeekTokenUsed: "Aggregate token growth over the latest rolling 7-day interval from local token timeline data.",
    burnWindowsTitle: "Reset-aware average burn rates across fixed lookback windows, measured as 5-hour window percent points per hour.",
    trendComparison: "Day-over-day and week-over-week changes in sessions, events, and token usage.",
    comparisonClickHint: "Click any comparison value to switch between percentage deltas and two-decimal absolute deltas.",
    behaviorAnalysis: "Visual summary of active work pressure, project concentration, token mix, and operating rhythm.",
    operatingRhythm: "Hourly historical operating rhythm from persisted monitor_samples history. Solid bars are the selected current period; outline bars are the selected baseline period. Monitor samples are real SwiftBar/dashboard heartbeats; backfilled samples come from existing Codex token logs.",
    recommendations: "Operational suggestions based on quota, burn rate, active sessions, and project concentration.",
    threadsWorking: "Codex threads with token events in the active-time window.",
    agentsActivated: "Local proxy for Codex agents. This monitor treats each session/thread as one agent because no separate agent_id is available in local logs.",
    projectsWorking: "Projects with at least one currently active Codex thread.",
    sessions: "Unique Codex session IDs observed in local logs.",
    tokenEvents: "Number of token_count events parsed from local Codex logs.",
    uploadSum: "Non-cached input tokens: new content uploaded or typed into Codex.",
    downloadSum: "Output tokens generated by Codex responses.",
    contextualSum: "Cached input tokens used as a local proxy for context/history reused by the model.",
    reasoningSum: "Reasoning output tokens reported by Codex usage events.",
    tokenMix: "Current representative session split by upload, download, contextual, and reasoning tokens.",
    windowTrend: "5-hour and weekly usage-window remaining-percent trend. The 5h mode lets you select any 5-hour interval by end time; the 24h mode lets you select any 24-hour interval. Remaining allowance falls as work consumes quota and rises again after reset. This is quota-window allowance, not token volume.",
    windowTrendSubtitle: "Solid lines show the selected interval. Dashed lines show the comparison baseline when enabled. The chart preserves raw logs but displays a bucketed, reset-aware series.",
    tokenUsedTrend: "All-session token-used trend. 24h uses a fixed 24-hour time axis; if data covers less, the observed coverage is shown instead of stretching the line.",
    tokenUsedTrendSubtitle: "The line uses the sum of each session's latest cumulative token count at that point in time.",
    showTokenTrend: "Show or hide the token-used chart without changing data collection.",
    projectRanking: "Per-project workload: threads, agent proxies, tokens, burn rate, and last update.",
    displayName: "Human-readable project name shown in the dashboard. It never changes the real cwd path.",
    realPath: "The real cwd path used by Codex and the local logs.",
    nameSource: "Where the display name came from: custom alias, Codex session index, or raw path fallback.",
    syncedThreadNames: "Thread names found in ~/.codex/session_index.jsonl for sessions in this project.",
    dailySummary: "Daily aggregation of sessions, token events, and latest token sums.",
    recentSessions: "Most recent Codex sessions and their active/idle state.",
    alerts: "Threshold warnings for quota, weekly window, context pressure, or rate limits.",
    threads: "Unique Codex session/thread count for the project.",
    agents: "Agent proxy count. One local thread/session is counted as one agent.",
    working: "Count currently active in the configured active-time window.",
    burnRate: "Recent token delta divided by the selected average-burn interval, shown as tokens per hour.",
    tokenUsed: "Latest cumulative token sum for the project.",
    upload: "New, non-cached input tokens.",
    download: "Output tokens generated by Codex.",
    contextual: "Cached input/context tokens reused by Codex.",
    reason: "Reasoning output tokens reported by Codex.",
    dod: "Day-over-day: current day compared with the previous day.",
    wow: "Week-over-week: latest 7 days compared with the previous 7 days.",
    refresh: "Force a synchronous read of local Codex logs and update the dashboard.",
    styleBusiness: "Switch to a compact business/professional interface style.",
    styleLight: "Switch to a reduced summary view that keeps only the highest-signal status, recommendations, alerts, and quota trend.",
    stylePro: "Switch to a detailed professional view with the full dashboard plus deeper operational analysis.",
    proAnalysis: "Professional analysis synthesized from quota state, burn-rate windows, active work, project concentration, and persisted history.",
  },
  zh: {
    plan: "本地 token_count 事件报告的 Codex 套餐类型。",
    rendered: "当前仪表盘页面从快照渲染出来的时间。",
    dataRead: "仪表盘最近一次同步并读取本地 Codex 用量数据的时间。",
    latestEvent: "本地 Codex 日志中最新 token_count 事件的时间。",
    primaryTitle: "滚动 5 小时用量窗口的剩余额度。剩余越高越安全。",
    secondaryTitle: "每周用量窗口的剩余额度。",
    contextTitle: "最近一轮使用了多少模型上下文窗口。",
    estimatedTimeTitle: "按你在 Last N min 中选择的平均消耗速率估算，5 小时窗口剩余额度多久会降到 0。",
    oneHourCreditEtaTitle: "使用固定的过去 1 小时平均消耗速率，估算 5 小时 credit usage 剩余额度还能使用多久。",
    averageBurnTitle: "在你选择的 Last N min 时间区间内，5 小时窗口的平均消耗斜率。",
    totalTokenUsed: "每个 session 最新累计 Token 的合计。",
    pastDayTokenUsed: "根据本地 Token 时间线计算的最近滚动 24 小时 Token 增量。",
    pastWeekTokenUsed: "根据本地 Token 时间线计算的最近滚动 7 天 Token 增量。",
    burnWindowsTitle: "固定回看窗口内、考虑 5 小时窗口 reset 后的平均消耗速率，单位是每小时百分点。",
    trendComparison: "会话、事件和 Token 用量的日环比与周环比变化。",
    comparisonClickHint: "点击任意趋势对比数值，在百分比变化和两位小数绝对变化之间切换。",
    behaviorAnalysis: "用图表展示活跃工作压力、项目集中度、Token 结构和运行节奏。",
    operatingRhythm: "从持久化 monitor_samples 历史表生成的小时历史运行节奏。实心柱是当前选择区间，描边柱是选择的基准区间。监控样本是真实 SwiftBar/dashboard 心跳；日志回填样本来自已有 Codex token 日志。",
    recommendations: "基于额度、消耗速率、活跃会话和项目集中度生成的操作建议。",
    threadsWorking: "活跃时间窗口内仍有 token 事件的 Codex thread。",
    agentsActivated: "Codex agent 的本地代理统计。由于本地日志没有独立 agent_id，这里按一个 session/thread 近似为一个 agent。",
    projectsWorking: "至少有一个活跃 Codex thread 的项目数量。",
    sessions: "本地日志中观察到的唯一 Codex session ID 数。",
    tokenEvents: "从本地 Codex 日志解析出的 token_count 事件数量。",
    uploadSum: "非缓存输入 Token，即本次真正新增上传或输入给 Codex 的内容。",
    downloadSum: "Codex 回复生成的输出 Token。",
    contextualSum: "缓存输入 Token，本地用作上下文/历史复用量的代理指标。",
    reasoningSum: "Codex 用量事件报告的推理输出 Token。",
    tokenMix: "代表性当前会话中上传、下载、上下文和推理 Token 的结构。",
    windowTrend: "5 小时和每周用量窗口的剩余百分比趋势。5 小时模式支持按结束时间选择任意 5 小时区间；24 小时模式支持选择任意 24 小时区间。剩余额度会随着工作消耗下降，并在 reset 后回升。这是额度窗口剩余，不是 Token 总量。",
    windowTrendSubtitle: "实线是当前选择区间；开启对比时，虚线是基准区间。图表保留原始日志，但展示为按时间桶聚合、按 reset 逻辑平滑后的序列。",
    tokenUsedTrend: "全部会话的 Token 已用趋势。24h 使用固定 24 小时时间轴；如果实际数据不足 24 小时，会显示观测覆盖范围，而不是把曲线拉满。",
    tokenUsedTrendSubtitle: "曲线使用每个时间点所有 session 的最新累计 Token 合计。",
    showTokenTrend: "显示或隐藏 Token 已用趋势图，不影响数据采集。",
    projectRanking: "按项目统计 thread、agent 代理、Token、消耗速率和最后更新时间。",
    displayName: "仪表盘显示的人类可读项目名，不会修改真实 cwd 路径。",
    realPath: "Codex 和本地日志实际使用的 cwd 路径。",
    nameSource: "显示名来源：自定义 alias、Codex session index，或原始路径兜底。",
    syncedThreadNames: "从 ~/.codex/session_index.jsonl 找到的该项目相关聊天名。",
    dailySummary: "按天汇总 sessions、token events 和最新 Token 合计。",
    recentSessions: "最近 Codex 会话及其活跃/空闲状态。",
    alerts: "额度、每周窗口、上下文压力或速率限制的阈值警报。",
    threads: "该项目下唯一 Codex session/thread 数。",
    agents: "Agent 代理数量。一个本地 thread/session 计为一个 agent。",
    working: "当前活跃时间窗口内仍在运行的数量。",
    burnRate: "最近 Token 增量除以你选择的平均消耗时间区间，单位为 token/h。",
    tokenUsed: "该项目最新累计 Token 合计。",
    upload: "新增、非缓存输入 Token。",
    download: "Codex 生成的输出 Token。",
    contextual: "Codex 复用的缓存输入/上下文 Token。",
    reason: "Codex 报告的推理输出 Token。",
    dod: "日环比：当前日期与前一日对比。",
    wow: "周环比：最近 7 天与前 7 天对比。",
    refresh: "强制同步读取本地 Codex 日志并更新仪表盘。",
    styleBusiness: "切换为紧凑、专业的商务界面风格。",
    styleLight: "切换为轻量摘要视图，只保留最高优先级状态、建议、警报和额度趋势。",
    stylePro: "切换为专业视图，保留完整仪表盘并增加更深入的运行分析。",
    proAnalysis: "基于额度状态、消耗窗口、活跃工作、项目集中度和持久化历史生成的专业分析。",
  },
};

const fmtRate = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  const number = Number(value);
  const abs = Math.abs(number);
  if (abs >= 1_000_000) return `${(number / 1_000_000).toFixed(2)}M%/h`;
  if (abs >= 10_000) return `${(number / 1_000).toFixed(1)}k%/h`;
  if (abs >= 1_000) return `${number.toFixed(0)}%/h`;
  return `${number.toFixed(2)}%/h`;
};
const fmtTokenRate = (value) => `${fmtTokens(Math.round(Number(value || 0)))}/h`;
const fmtPercentPoints = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return `${Number(value).toFixed(1)}pp`;
};
const fmtDurationHours = (hours) => {
  if (hours === null || hours === undefined || Number.isNaN(Number(hours))) return "--";
  const totalMinutes = Math.max(0, Math.round(Number(hours) * 60));
  if (totalMinutes <= 0) return `0 ${currentLang === "zh" ? "分钟" : "min"}`;
  if (totalMinutes < 60) return `${totalMinutes} ${currentLang === "zh" ? "分钟" : "min"}`;
  if (totalMinutes < 1440) {
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    if (currentLang === "zh") return m ? `${h}小时 ${m}分钟` : `${h}小时`;
    return m ? `${h}h ${m}m` : `${h}h`;
  }
  const days = Math.floor(totalMinutes / 1440);
  const h = Math.round((totalMinutes % 1440) / 60);
  if (currentLang === "zh") return h ? `${days}天 ${h}小时` : `${days}天`;
  return h ? `${days}d ${h}h` : `${days}d`;
};
const fmtDurationMinutes = (minutes) => fmtDurationHours(Number(minutes || 0) / 60);
const estimatePrimaryTimeLeftHours = (remainingPercent, burnRatePercentPerHour) => {
  if (remainingPercent === null || remainingPercent === undefined || Number.isNaN(Number(remainingPercent))) return null;
  const remainingValue = Math.max(0, Number(remainingPercent));
  if (remainingValue <= 0) return 0;
  if (burnRatePercentPerHour === null || burnRatePercentPerHour === undefined || Number.isNaN(Number(burnRatePercentPerHour))) return null;
  const burnValue = Number(burnRatePercentPerHour);
  if (burnValue <= 0) return Infinity;
  return remainingValue / burnValue;
};
const resetCountdown = (windowData) => {
  if (!windowData?.resets_at_iso || !windowData?.window_minutes) return null;
  const resetAt = new Date(windowData.resets_at_iso).getTime();
  if (!Number.isFinite(resetAt)) return null;
  const totalMs = Math.max(1, Number(windowData.window_minutes) * 60 * 1000);
  const remainingMs = Math.max(0, resetAt - Date.now());
  return {
    remainingMs,
    remainingMinutes: Math.ceil(remainingMs / 60000),
    remainingPercent: Math.max(0, Math.min(100, remainingMs * 100 / totalMs)),
  };
};
const burnRateWindow = (data, key) => (data?.burn_rate_windows || []).find(item => item.key === key) || null;
const t = (key) => I18N[currentLang]?.[key] || I18N.en[key] || key;
const tip = (key) => TOOLTIPS[currentLang]?.[key] || TOOLTIPS.en[key] || "";
const cssVar = (name, fallback) => getComputedStyle(document.body).getPropertyValue(name).trim() || fallback;

function comparisonFormatLabel() {
  return comparisonFormat === "absolute" ? t("comparisonAbsoluteMode") : t("comparisonPercentMode");
}

function comparisonValueTitle(item) {
  const percent = fmtDelta(item, "percent");
  const absolute = fmtDelta(item, "absolute");
  return `${tip("comparisonClickHint")}\n${t("comparisonPercentMode")}: ${percent}\n${t("comparisonAbsoluteMode")}: ${absolute}`;
}

function toggleComparisonFormat() {
  comparisonFormat = comparisonFormat === "percent" ? "absolute" : "percent";
  localStorage.setItem(COMPARISON_FORMAT_STORAGE_KEY, comparisonFormat);
  if (latestSnapshot) renderComparisons(latestSnapshot);
}

function normalizeWindowTrendMode(mode) {
  if (mode === "recent") return "fiveHour";
  return ["fiveHour", "day", "week"].includes(mode) ? mode : "fiveHour";
}

function loadWindowTrendRangeEnd() {
  try {
    const parsed = JSON.parse(localStorage.getItem(WINDOW_TREND_RANGE_END_STORAGE_KEY) || "{}");
    return {
      fiveHour: String(parsed.fiveHour || parsed.recent || ""),
      day: String(parsed.day || ""),
    };
  } catch {
    return {fiveHour: "", day: ""};
  }
}

function saveWindowTrendRangeEnd() {
  localStorage.setItem(WINDOW_TREND_RANGE_END_STORAGE_KEY, JSON.stringify({
    fiveHour: windowTrendRangeEnd.fiveHour || "",
    day: windowTrendRangeEnd.day || "",
  }));
}

function loadTokenTrendLineSelection() {
  try {
    const parsed = JSON.parse(localStorage.getItem(TOKEN_TREND_LINES_STORAGE_KEY) || "{}");
    return {
      aggregate: parsed.aggregate !== false,
      baseline: parsed.baseline !== false,
      sessions: parsed.sessions && typeof parsed.sessions === "object" ? parsed.sessions : {},
    };
  } catch {
    return {aggregate: true, baseline: true, sessions: {}};
  }
}

function saveTokenTrendLineSelection() {
  localStorage.setItem(TOKEN_TREND_LINES_STORAGE_KEY, JSON.stringify(tokenTrendLineSelection));
}

function tokenLineEnabled(kind, id, fallback = true) {
  if (kind === "aggregate") return tokenTrendLineSelection.aggregate !== false;
  if (kind === "baseline") return tokenTrendLineSelection.baseline !== false;
  if (kind === "session") {
    const value = tokenTrendLineSelection.sessions?.[id];
    return value === undefined ? fallback : value !== false;
  }
  return fallback;
}

function fmtTimeLocalized(iso) {
  if (!iso) return "--";
  return new Date(iso).toLocaleString(currentLang === "zh" ? "zh-CN" : "en-US");
}

function translateMetricLabel(label) {
  const labels = {
    Tokens: "tokens",
    Sessions: "sessions",
    Events: "events",
    Upload: "upload",
    Download: "download",
    Contextual: "contextual",
    Reasoning: "reasoningSum",
  };
  return labels[label] ? t(labels[label]) : label;
}

function translatePatternName(name) {
  if (currentLang !== "zh") return name;
  return {
    "Peak operating hour": "高峰使用时段",
    "Concurrent active work": "并发活跃工作",
    "Project concentration": "项目集中度",
    "Token traffic mix": "Token 流量结构",
  }[name] || name;
}

function translatePatternDetail(name, detail) {
  if (currentLang !== "zh") return detail;
  if (name === "Peak operating hour") {
    const count = detail.match(/\d+/)?.[0] || "--";
    return `本地该小时记录了 ${count} 条词元事件。`;
  }
  if (name === "Concurrent active work") return "过去20分钟内活跃的会话数量。";
  if (name === "Project concentration") return "最大项目占最新词元合计的比例。";
  if (name === "Token traffic mix") return "代表性最新会话中，上传、下载、上下文和推理 Token 占累计 Token 的比例。";
  return detail;
}

function translateRecommendationTitle(title) {
  if (currentLang !== "zh") return title;
  return {
    "No Codex token data": "没有 Codex Token 数据",
    "Protect the 5h window": "保护5小时窗口",
    "Watch short-window capacity": "关注短窗口容量",
    "5h capacity is healthy": "5小时容量健康",
    "Daily usage spike": "日用量突增",
    "High 5h burn rate": "5小时消耗速率偏高",
    "Too many active sessions": "活跃会话过多",
    "One project dominates usage": "单个项目占用过高",
  }[title] || title;
}

function translateRecommendationDetail(title, detail) {
  if (currentLang !== "zh") return detail;
  if (title === "No Codex token data") return "请确认 Codex 正在写入本地 token_count 事件。";
  if (title === "Protect the 5h window") return "暂停非关键任务，或把工作合并为更少、更短的提示。";
  if (title === "Watch short-window capacity") return "批处理低优先级任务，避免重置前并行运行长任务。";
  if (title === "5h capacity is healthy") return "当前短窗口额度充足；并行工作时继续观察消耗速率。";
  if (title === "Daily usage spike") {
    const percent = detail.match(/up ([\d.]+)%/)?.[1] || "--";
    return `词元合计较前一日上升 ${percent}%；请检查大型会话和重复重试。`;
  }
  if (title === "High 5h burn rate") {
    const rate = detail.match(/is ([\d.]+)%/)?.[1] || "--";
    return `当前主窗口消耗为每小时 ${rate}%；如果稍后还需要额度，请减少并发后台工作。`;
  }
  if (title === "Too many active sessions") {
    const count = detail.match(/^(\d+)/)?.[1] || "--";
    return `当前有 ${count} 个活跃会话；关闭或完成闲置工作以减少额度噪音。`;
  }
  if (title === "One project dominates usage") return "检查这是预期的持续工作，还是失控或重试过多的任务。";
  return detail;
}

function translateAlertMessage(message) {
  if (currentLang !== "zh") return message;
  const limit = message.match(/Rate limit reached: (.+)\./);
  if (limit) return `已触发速率限制：${limit[1]}。`;
  const threshold = message.match(/(.+) is at ([\d.]+)%\./);
  if (!threshold) return message;
  const label = {
    "5-hour window": "5小时窗口",
    "weekly window": "每周窗口",
    "last turn context pressure": "最近一轮上下文压力",
  }[threshold[1]] || threshold[1];
  return `${label} 已达到 ${threshold[2]}%。`;
}

function applyStaticTranslations() {
  document.documentElement.lang = currentLang === "zh" ? "zh-CN" : "en";
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
    const description = tip(el.dataset.i18n);
    if (description) el.setAttribute("title", description);
  });
  byId("plan")?.setAttribute("title", tip("plan"));
  byId("updated")?.setAttribute("title", tip("rendered"));
  byId("data-read-at")?.setAttribute("title", tip("dataRead"));
  byId("latest-event-at")?.setAttribute("title", tip("latestEvent"));
  byId("average-burn-minutes")?.setAttribute("title", currentLang === "zh" ? "修改平均消耗速率的计算时间区间，单位分钟。" : "Change the interval used to calculate average burn rate, in minutes.");
  document.querySelector(".trend-visible-toggle")?.setAttribute("title", tip("showTokenTrend"));
  byId("lang-en")?.setAttribute("title", "Show the interface in English.");
  byId("lang-zh")?.setAttribute("title", "使用中文显示界面。");
  byId("lang-en")?.classList.toggle("active", currentLang === "en");
  byId("lang-zh")?.classList.toggle("active", currentLang === "zh");
  byId("lang-en")?.setAttribute("aria-pressed", String(currentLang === "en"));
  byId("lang-zh")?.setAttribute("aria-pressed", String(currentLang === "zh"));
}

function normalizeInterfaceStyle(style) {
  if (style === "cute") return "light";
  if (style === "engineering") return "pro";
  const allowed = new Set(["business", "light", "pro"]);
  return allowed.has(style) ? style : "business";
}

function applyInterfaceStyle() {
  currentInterfaceStyle = normalizeInterfaceStyle(currentInterfaceStyle);
  document.body.dataset.interfaceStyle = currentInterfaceStyle;
  localStorage.setItem(INTERFACE_STYLE_STORAGE_KEY, currentInterfaceStyle);
  document.querySelectorAll(".interface-button").forEach((button) => {
    const active = button.dataset.style === currentInterfaceStyle;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  renderCharts(latestSnapshot);
}

function setInterfaceStyle(style) {
  currentInterfaceStyle = normalizeInterfaceStyle(style);
  applyInterfaceStyle();
}

function setLanguage(lang) {
  currentLang = lang === "zh" ? "zh" : "en";
  applyStaticTranslations();
  if (latestSnapshot) renderSnapshot(latestSnapshot);
  else {
    setText("plan", `${t("plan")} --`);
    setText("updated", t("waiting"));
  }
}

function averageBurnMinutes() {
  const input = byId("average-burn-minutes");
  const value = Number(input?.value || 60);
  return Math.max(1, Math.min(1440, Number.isFinite(value) ? Math.round(value) : 60));
}

function setBar(id, value, mode = "used") {
  const el = byId(id);
  if (!el) return;
  const pct = Math.max(0, Math.min(100, Number(value || 0)));
  el.style.width = `${pct}%`;
  el.style.background = mode === "remaining" ? remainingColor(pct) : usedColor(pct);
}

function setCountdown(prefix, windowData) {
  const countdown = resetCountdown(windowData);
  const valueEl = byId(`${prefix}-countdown-value`);
  const barEl = byId(`${prefix}-countdown-bar`);
  if (!countdown) {
    if (valueEl) valueEl.textContent = "--";
    if (barEl) barEl.style.width = "0%";
    return;
  }
  if (valueEl) valueEl.textContent = `${fmtDurationMinutes(countdown.remainingMinutes)} ${t("timeLeft")}`;
  if (barEl) {
    barEl.style.width = `${countdown.remainingPercent}%`;
    barEl.style.background = remainingColor(countdown.remainingPercent);
  }
}

function prepareCanvas(canvas) {
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = Math.max(1, Math.round(rect.width || canvas.clientWidth || 1));
  const cssHeight = Math.max(160, Math.round(rect.height || canvas.clientHeight || 180));
  const width = cssWidth * dpr;
  const height = cssHeight * dpr;
  canvas.width = width;
  canvas.height = height;
  return { ctx: canvas.getContext("2d"), dpr, width, height };
}

function drawBarChart(canvas, values) {
  const prepared = prepareCanvas(canvas);
  if (!prepared) return;
  const { ctx, dpr, width, height } = prepared;
  ctx.clearRect(0, 0, width, height);
  const clean = values.filter(v => Number(v.value || 0) > 0);
  CHART_HIT_AREAS.set(canvas, []);
  if (!clean.length) return;
  const max = Math.max(...clean.map(v => Number(v.value || 0)), 1);
  const gap = 12 * dpr;
  const barW = Math.max(8 * dpr, (width - gap * (clean.length + 1)) / clean.length);
  const labelColor = cssVar("--chart-label", "#667085");
  const areas = [];
  clean.forEach((v, i) => {
    const h = (height - 36 * dpr) * Number(v.value || 0) / max;
    const x = gap + i * (barW + gap);
    const y = height - h - 24 * dpr;
    ctx.fillStyle = v.color;
    ctx.fillRect(x, y, barW, h);
    ctx.fillStyle = labelColor;
    ctx.font = `${11 * dpr}px system-ui`;
    ctx.fillText(v.label, x, height - 8 * dpr);
    areas.push({
      x: x / dpr,
      y: y / dpr,
      w: barW / dpr,
      h: h / dpr,
      text: `${v.label}: ${fmtTokens(v.value)} ${currentLang === "zh" ? "Token" : "tokens"}`,
    });
  });
  CHART_HIT_AREAS.set(canvas, areas);
}

function isoDateKey(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function weekStartKeyFromDate(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
  const local = new Date(date);
  local.setHours(0, 0, 0, 0);
  const offset = (local.getDay() + 6) % 7;
  local.setDate(local.getDate() - offset);
  return isoDateKey(local);
}

function dateFromKey(key) {
  if (!key) return null;
  const [year, month, day] = String(key).split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
}

function subtractYearKey(key, mode) {
  const date = dateFromKey(key);
  if (!date) return "";
  if (mode === "week") date.setDate(date.getDate() - 364);
  else date.setFullYear(date.getFullYear() - 1);
  return isoDateKey(date);
}

function periodRange(key, mode) {
  const start = dateFromKey(key);
  if (!start) return {start: null, end: null};
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + (mode === "week" ? 7 : 1));
  return {start, end};
}

function formatDateTimeLocalInput(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function parseDateTimeLocalInput(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function shiftDateByYears(date, years) {
  const shifted = new Date(date);
  shifted.setFullYear(shifted.getFullYear() + years);
  return shifted;
}

function rangeLabel(start, end) {
  if (!start || !end) return "--";
  return `${fmtTimeLocalized(start.toISOString())} - ${fmtTimeLocalized(end.toISOString())}`;
}

function downsampleSeries(points, maxPoints = 720) {
  if (!Array.isArray(points) || points.length <= maxPoints) return points || [];
  const step = Math.ceil(points.length / maxPoints);
  const sampled = points.filter((_, index) => index % step === 0);
  const last = points[points.length - 1];
  if (sampled[sampled.length - 1] !== last) sampled.push(last);
  return sampled;
}

function timeRangeCoverage(points, rangeStart, rangeEnd) {
  const times = (points || []).map(point => new Date(point.timestamp).getTime()).filter(Number.isFinite);
  if (!times.length || !rangeStart || !rangeEnd) return null;
  const observedStart = Math.min(...times);
  const observedEnd = Math.max(...times);
  const expectedMs = Math.max(1, new Date(rangeEnd).getTime() - new Date(rangeStart).getTime());
  const observedMs = Math.max(0, observedEnd - observedStart);
  return {
    percent: Math.min(100, observedMs * 100 / expectedMs),
    observedStart: new Date(observedStart),
    observedEnd: new Date(observedEnd),
  };
}

function coverageLabel(points, rangeStart, rangeEnd) {
  const coverage = timeRangeCoverage(points, rangeStart, rangeEnd);
  if (!coverage) return "";
  return `${t("observedCoverage")} ${fmtPercent(coverage.percent, 0)}`;
}

function chartDetailElementFor(canvas) {
  if (!canvas) return null;
  const id = canvas.id === "trend-chart" ? "trend-chart-detail" : canvas.id === "token-trend-chart" ? "token-trend-detail" : "";
  return id ? byId(id) : null;
}

function setChartDetail(canvas, hit = null, locked = false) {
  const el = chartDetailElementFor(canvas);
  if (!el) return;
  if (!hit) {
    el.textContent = t("chartInteractionHint");
    el.classList.remove("locked");
    return;
  }
  el.textContent = `${locked ? `${t("selectedPoint")} · ` : ""}${hit.summary || String(hit.text || "").split("\n").slice(0, 3).join(" · ")}`;
  el.classList.toggle("locked", Boolean(locked));
}

function nearestChartHit(canvas, x, y) {
  const areas = CHART_HIT_AREAS.get(canvas) || [];
  let direct = null;
  let nearest = null;
  let bestDistance = Infinity;
  areas.forEach((area) => {
    const inside = x >= area.x && x <= area.x + area.w && y >= area.y && y <= area.y + area.h;
    if (inside && !direct) direct = area;
    const cx = area.cx ?? area.x + area.w / 2;
    const cy = area.cy ?? area.y + area.h / 2;
    const distance = Math.hypot(x - cx, y - cy);
    const radius = Number(area.radius || 34);
    if (distance <= radius && distance < bestDistance) {
      nearest = area;
      bestDistance = distance;
    }
  });
  return direct || nearest;
}

function positionChartTooltip(tooltip, clientX, clientY) {
  const width = Math.min(300, Math.max(220, window.innerWidth - 24));
  tooltip.style.maxWidth = `${width}px`;
  tooltip.style.left = `${Math.max(8, Math.min(window.innerWidth - width - 8, clientX + 14))}px`;
  tooltip.style.top = `${Math.max(8, Math.min(window.innerHeight - 80, clientY + 14))}px`;
}

function showChartTooltip(canvas, hit, event, locked = false) {
  const tooltip = ensureChartTooltip();
  if (!hit) {
    if (!locked) tooltip.hidden = true;
    canvas.style.cursor = "default";
    setChartDetail(canvas, null);
    return;
  }
  tooltip.textContent = hit.text;
  tooltip.hidden = false;
  tooltip.classList.toggle("locked", Boolean(locked));
  positionChartTooltip(tooltip, event.clientX, event.clientY);
  canvas.style.cursor = "crosshair";
  setChartDetail(canvas, hit, locked);
}

function clearPinnedChart() {
  pinnedChart = null;
  const tooltip = ensureChartTooltip();
  tooltip.hidden = true;
  tooltip.classList.remove("locked");
  document.querySelectorAll(".chart-canvas").forEach((canvas) => {
    canvas.style.cursor = "default";
    setChartDetail(canvas, null);
  });
}

function downloadCanvasPng(canvasId) {
  const canvas = byId(canvasId);
  if (!canvas) return;
  const link = document.createElement("a");
  link.download = `${canvasId}-${new Date().toISOString().slice(0, 10)}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

function drawEndLabel(ctx, dpr, x, y, text, color, chartWidth, chartHeight) {
  if (!text) return;
  ctx.save();
  ctx.font = `${10 * dpr}px system-ui`;
  const paddingX = 6 * dpr;
  const paddingY = 4 * dpr;
  const textWidth = ctx.measureText(text).width;
  const boxW = textWidth + paddingX * 2;
  const boxH = 18 * dpr;
  const boxX = Math.max(4 * dpr, Math.min(chartWidth - boxW - 4 * dpr, x + 8 * dpr));
  const boxY = Math.max(4 * dpr, Math.min(chartHeight - boxH - 6 * dpr, y - boxH / 2));
  ctx.fillStyle = color;
  ctx.globalAlpha = 0.92;
  ctx.beginPath();
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(boxX, boxY, boxW, boxH, 6 * dpr);
  } else {
    ctx.rect(boxX, boxY, boxW, boxH);
  }
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(text, boxX + paddingX, boxY + boxH / 2);
  ctx.restore();
}

function timelineTicksForRange(start, end, count = 5) {
  const startMs = new Date(start).getTime();
  const endMs = new Date(end).getTime();
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) return [];
  const ticks = [];
  const wanted = Math.max(2, count);
  for (let index = 0; index < wanted; index += 1) {
    const ratio = wanted === 1 ? 0 : index / (wanted - 1);
    ticks.push({ratio, timestamp: new Date(startMs + (endMs - startMs) * ratio).toISOString()});
  }
  return ticks;
}

function tokenUsageSummary(data) {
  const points = allTokenSamples(data);
  const totals = data?.totals || {};
  const latest = points[points.length - 1] || null;
  const total = Number(totals.latest_total_tokens_sum ?? (latest ? tokenTrendValue(latest) : 0));
  const deltaForHours = (hours) => {
    if (!latest) return {delta: 0, coveragePercent: 0};
    const end = new Date(latest.timestamp).getTime();
    const cutoff = end - hours * 60 * 60 * 1000;
    let baseline = null;
    for (const point of points) {
      const time = new Date(point.timestamp).getTime();
      if (!Number.isFinite(time)) continue;
      if (time <= cutoff) baseline = point;
      else break;
    }
    if (!baseline) baseline = points[0];
    const observedStart = baseline ? new Date(baseline.timestamp).getTime() : end;
    const coveragePercent = Math.min(100, Math.max(0, (end - observedStart) * 100 / Math.max(1, hours * 60 * 60 * 1000)));
    return {
      delta: Math.max(0, tokenTrendValue(latest) - tokenTrendValue(baseline)),
      coveragePercent,
    };
  };
  const day = deltaForHours(24);
  const week = deltaForHours(24 * 7);
  return {
    total,
    pastDay: day.delta,
    pastWeek: week.delta,
    pastDayCoverage: day.coveragePercent,
    pastWeekCoverage: week.coveragePercent,
    dailyAvg: week.delta / 7,
    weeklyAvg: week.delta,
  };
}

function clampPercentValue(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Math.max(0, Math.min(100, number));
}

function windowTrendValue(sample, field) {
  const remainingKey = field === "secondary" ? "secondary_remaining_percent" : "primary_remaining_percent";
  const usedKey = field === "secondary" ? "secondary_used_percent" : "primary_used_percent";
  const remainingValue = clampPercentValue(sample?.[remainingKey]);
  if (remainingValue !== null) return remainingValue;
  const usedValue = clampPercentValue(sample?.[usedKey]);
  return usedValue === null ? null : 100 - usedValue;
}

function windowTrendUsedValue(sample, field) {
  const usedKey = field === "secondary" ? "secondary_used_percent" : "primary_used_percent";
  const usedValue = clampPercentValue(sample?.[usedKey]);
  if (usedValue !== null) return usedValue;
  const remainingValue = windowTrendValue(sample, field);
  return remainingValue === null ? null : 100 - remainingValue;
}

function compactWindowSample(sample) {
  const timestamp = sample?.sampled_at || sample?.timestamp;
  const primaryUsed = windowTrendUsedValue(sample, "primary");
  const secondaryUsed = windowTrendUsedValue(sample, "secondary");
  return {
    timestamp,
    primary_remaining_percent: primaryUsed === null ? windowTrendValue(sample, "primary") : 100 - primaryUsed,
    secondary_remaining_percent: secondaryUsed === null ? windowTrendValue(sample, "secondary") : 100 - secondaryUsed,
    primary_used_percent: primaryUsed,
    secondary_used_percent: secondaryUsed,
    token_used_total: Number(sample?.latest_total_tokens_sum ?? sample?.token_used_total ?? sample?.total_tokens ?? 0),
    source: sample?.source || "trend",
  };
}

function windowTrendBucketKey(timestamp) {
  const time = new Date(timestamp).getTime();
  if (!Number.isFinite(time)) return null;
  return new Date(Math.floor(time / WINDOW_TREND_BUCKET_MS) * WINDOW_TREND_BUCKET_MS).toISOString();
}

function mergeWindowBucket(existing, sample) {
  const next = {...existing};
  const sampleCount = Number(existing.sample_count || 1) + Number(sample.sample_count || 1);
  const sources = new Set([...(existing.sources || [existing.source]), ...(sample.sources || [sample.source])].filter(Boolean));
  next.sample_count = sampleCount;
  next.sources = Array.from(sources);
  next.source = next.sources.length === 1 ? next.sources[0] : "mixed";
  next.token_used_total = Math.max(Number(existing.token_used_total || 0), Number(sample.token_used_total || 0));
  ["primary", "secondary"].forEach((field) => {
    const usedKey = `${field}_used_percent`;
    const remainingKey = `${field}_remaining_percent`;
    const values = [existing[usedKey], sample[usedKey]].map(clampPercentValue).filter(value => value !== null);
    if (values.length) {
      const usedValue = Math.max(...values);
      next[usedKey] = usedValue;
      next[remainingKey] = 100 - usedValue;
    } else {
      const remainingValues = [existing[remainingKey], sample[remainingKey]].map(clampPercentValue).filter(value => value !== null);
      next[remainingKey] = remainingValues.length ? Math.min(...remainingValues) : null;
      next[usedKey] = next[remainingKey] === null ? null : 100 - next[remainingKey];
    }
  });
  return next;
}

function bucketWindowSamples(samples) {
  const buckets = new Map();
  samples.forEach((sample) => {
    const key = windowTrendBucketKey(sample.timestamp);
    if (!key) return;
    const normalized = {
      ...sample,
      timestamp: key,
      sample_count: Number(sample.sample_count || 1),
      sources: sample.sources || [sample.source || "trend"],
    };
    const existing = buckets.get(key);
    buckets.set(key, existing ? mergeWindowBucket(existing, normalized) : normalized);
  });
  return Array.from(buckets.values()).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
}

function canonicalizeWindowSeries(samples, field) {
  const usedKey = `${field}_used_percent`;
  const remainingKey = `${field}_remaining_percent`;
  const rawUsedKey = `raw_${usedKey}`;
  const rawRemainingKey = `raw_${remainingKey}`;
  const resetKey = `${field}_reset_inferred`;
  const adjustedKey = `${field}_noise_adjusted`;
  const cycleKey = `${field}_cycle_index`;
  const resetDrop = WINDOW_TREND_RESET_DROP[field] || 20;
  let cycleMaxUsed = null;
  let cycleIndex = 0;
  return samples.map((sample) => {
    const rawUsed = clampPercentValue(sample[usedKey]);
    if (rawUsed === null) return sample;
    let resetInferred = false;
    let noiseAdjusted = false;
    if (cycleMaxUsed === null) {
      cycleMaxUsed = rawUsed;
    } else if (cycleMaxUsed - rawUsed >= resetDrop) {
      cycleIndex += 1;
      cycleMaxUsed = rawUsed;
      resetInferred = true;
    } else if (rawUsed > cycleMaxUsed) {
      cycleMaxUsed = rawUsed;
    } else if (rawUsed < cycleMaxUsed) {
      noiseAdjusted = true;
    }
    const canonicalUsed = clampPercentValue(cycleMaxUsed);
    return {
      ...sample,
      [rawUsedKey]: rawUsed,
      [rawRemainingKey]: clampPercentValue(sample[remainingKey]),
      [usedKey]: canonicalUsed,
      [remainingKey]: canonicalUsed === null ? null : 100 - canonicalUsed,
      [resetKey]: resetInferred,
      [adjustedKey]: noiseAdjusted,
      [cycleKey]: cycleIndex,
    };
  });
}

function canonicalizeWindowSamples(samples) {
  return canonicalizeWindowSeries(canonicalizeWindowSeries(bucketWindowSamples(samples), "primary"), "secondary");
}

function allWindowSamples(data) {
  const historySamples = data?.monitor_history?.window_samples || [];
  const raw = historySamples.length ? historySamples : (data?.trend_points || []);
  const compact = raw
    .map(compactWindowSample)
    .filter(sample => sample.timestamp && sample.primary_remaining_percent !== null && sample.primary_remaining_percent !== undefined)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  return canonicalizeWindowSamples(compact);
}

function fixedWindowHoursForMode(mode) {
  if (mode === "fiveHour") return 5;
  if (mode === "day") return 24;
  return null;
}

function samplesInRange(samples, start, end) {
  const startMs = new Date(start).getTime();
  const endMs = new Date(end).getTime();
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) return [];
  return samples.filter(sample => {
    const time = new Date(sample.timestamp).getTime();
    return Number.isFinite(time) && time >= startMs && time <= endMs;
  });
}

function selectedFixedWindowTrendState(samples, mode) {
  const hours = fixedWindowHoursForMode(mode);
  const latest = new Date(samples[samples.length - 1]?.timestamp);
  const earliest = new Date(samples[0]?.timestamp);
  const requestedEnd = parseDateTimeLocalInput(windowTrendRangeEnd[mode]);
  const end = requestedEnd || latest;
  const start = new Date(end.getTime() - hours * 60 * 60 * 1000);
  const points = samplesInRange(samples, start, end);
  const compareMode = windowTrendCompareMode[mode] || "previous";
  let compareStart = null;
  let compareEnd = null;
  if (compareMode === "previous") {
    compareEnd = start;
    compareStart = new Date(start.getTime() - hours * 60 * 60 * 1000);
  } else if (compareMode === "year") {
    compareStart = shiftDateByYears(start, -1);
    compareEnd = shiftDateByYears(end, -1);
  }
  const comparePoints = compareStart && compareEnd ? samplesInRange(samples, compareStart, compareEnd) : [];
  return {
    mode,
    points,
    comparePoints,
    periods: [],
    selectedKey: formatDateTimeLocalInput(end),
    compareMode,
    label: rangeLabel(start, end),
    compareLabel: comparePoints.length ? rangeLabel(compareStart, compareEnd) : t("trendCompareNone"),
    rangeStart: start.toISOString(),
    rangeEnd: end.toISOString(),
    compareRangeStart: compareStart?.toISOString(),
    compareRangeEnd: compareEnd?.toISOString(),
    controlEndValue: formatDateTimeLocalInput(end),
    controlMinValue: formatDateTimeLocalInput(earliest),
    controlMaxValue: formatDateTimeLocalInput(latest),
    durationHours: hours,
  };
}

function windowTrendPeriods(data, mode) {
  if (mode === "day") {
    const fromHistory = (data?.monitor_history?.daily || []).map(item => String(item.date || "")).filter(Boolean);
    if (fromHistory.length) return fromHistory;
  }
  if (mode === "week") {
    const fromHistory = (data?.monitor_history?.weekly || []).map(item => String(item.week_start || "")).filter(Boolean);
    if (fromHistory.length) return fromHistory;
  }
  const keys = new Set();
  allWindowSamples(data).forEach(sample => {
    const date = new Date(sample.timestamp);
    keys.add(mode === "week" ? weekStartKeyFromDate(date) : isoDateKey(date));
  });
  return Array.from(keys).filter(Boolean).sort();
}

function periodLabelFromKey(key, mode) {
  if (!key) return "--";
  if (mode !== "week") return key;
  const start = dateFromKey(key);
  if (!start) return key;
  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  return `${key} - ${isoDateKey(end)}`;
}

function selectedWindowTrendState(data) {
  windowTrendMode = normalizeWindowTrendMode(windowTrendMode);
  const samples = allWindowSamples(data);
  if (!samples.length) return {mode: windowTrendMode, points: [], comparePoints: [], periods: [], label: "--", compareLabel: "--"};
  if (fixedWindowHoursForMode(windowTrendMode)) return selectedFixedWindowTrendState(samples, windowTrendMode);
  const mode = windowTrendMode;
  const periods = windowTrendPeriods(data, mode);
  let key = windowTrendPeriod[mode];
  if (!key || !periods.includes(key)) key = periods[periods.length - 1] || "";
  windowTrendPeriod[mode] = key;
  const periodMatch = (sample, wanted) => {
    const date = new Date(sample.timestamp);
    return (mode === "week" ? weekStartKeyFromDate(date) : isoDateKey(date)) === wanted;
  };
  const points = samples.filter(sample => periodMatch(sample, key));
  const range = periodRange(key, mode);
  const compareMode = windowTrendCompareMode[mode] || "previous";
  let compareKey = "";
  if (compareMode === "previous") {
    const index = periods.indexOf(key);
    compareKey = index > 0 ? periods[index - 1] : "";
  } else if (compareMode === "year") {
    const wanted = subtractYearKey(key, mode);
    compareKey = periods.includes(wanted) ? wanted : "";
  }
  const comparePoints = compareKey ? samples.filter(sample => periodMatch(sample, compareKey)) : [];
  const compareRange = compareKey ? periodRange(compareKey, mode) : {start: null, end: null};
  return {
    mode,
    points,
    comparePoints,
    periods,
    selectedKey: key,
    compareMode,
    label: periodLabelFromKey(key, mode),
    compareLabel: compareKey ? periodLabelFromKey(compareKey, mode) : t("trendCompareNone"),
    rangeStart: range.start?.toISOString(),
    rangeEnd: range.end?.toISOString(),
    compareRangeStart: compareRange.start?.toISOString(),
    compareRangeEnd: compareRange.end?.toISOString(),
  };
}

function renderWindowTrendControls(data, state) {
  const box = byId("window-trend-controls");
  if (!box) return;
  const mode = state.mode || windowTrendMode;
  const periods = mode === "week" ? state.periods || [] : [];
  const selectedKey = state.selectedKey || "";
  const coverage = coverageLabel(state.points, state.rangeStart, state.rangeEnd);
  const quality = t("windowTrendQuality");
  const modeLabel = mode === "fiveHour" ? t("windowTrendModeFiveHour") : mode === "day" ? t("windowTrendModeDayWindow") : t("trendModeWeek");
  setText(
    "window-trend-subtitle",
    `${state.label} · ${modeLabel} · ${quality}${coverage ? ` · ${coverage}` : ""}${state.comparePoints?.length ? ` · ${t("trendBaseline")} ${state.compareLabel}` : ""}`
  );
  box.innerHTML = `
    ${["fiveHour", "day", "week"].map(item => `
      <button class="chart-control-button ${mode === item ? "active" : ""}" type="button" data-window-trend-mode="${item}">
        ${item === "fiveHour" ? t("windowTrendModeFiveHour") : item === "day" ? t("windowTrendModeDayWindow") : t("trendModeWeek")}
      </button>
    `).join("")}
    ${fixedWindowHoursForMode(mode) ? `
      <label>
        <span>${t("windowTrendEnd")}</span>
        <input class="chart-control-input" type="datetime-local" step="60" data-window-trend-end="${mode}"
          value="${escapeHtml(state.controlEndValue || "")}"
          min="${escapeHtml(state.controlMinValue || "")}"
          max="${escapeHtml(state.controlMaxValue || "")}">
      </label>
    ` : ""}
    ${mode === "week" ? `
      <label>
        <span>${t("trendPeriod")}</span>
        <select class="chart-control-select" data-window-trend-period="${mode}">
          ${periods.map(key => `<option value="${escapeHtml(key)}" ${key === selectedKey ? "selected" : ""}>${escapeHtml(periodLabelFromKey(key, mode))}</option>`).join("")}
        </select>
      </label>
    ` : ""}
    ${mode === "fiveHour" || mode === "day" || mode === "week" ? `
      <label>
        <span>${t("trendCompare")}</span>
        <select class="chart-control-select" data-window-trend-compare="${mode}">
          <option value="none" ${state.compareMode === "none" ? "selected" : ""}>${t("trendCompareNone")}</option>
          <option value="previous" ${state.compareMode === "previous" ? "selected" : ""}>${t("trendComparePrevious")}</option>
          <option value="year" ${state.compareMode === "year" ? "selected" : ""}>${t("trendCompareYear")}</option>
        </select>
      </label>
    ` : ""}
    <button class="chart-control-button ghost" type="button" data-chart-download="trend-chart">${t("downloadPng")}</button>
    <button class="chart-control-button ghost" type="button" data-chart-clear-focus>${t("resetFocus")}</button>
    <div class="chart-legend" title="${escapeHtml(t("chartInteractionHint"))}">
      <span><i style="background:${escapeHtml(cssVar("--chart-line", "#22577a"))}"></i>${escapeHtml(t("fiveHourLine"))}</span>
      <span><i style="background:${escapeHtml(cssVar("--chart-reason", "#7a4d9f"))}"></i>${escapeHtml(t("weeklyLine"))}</span>
      ${state.comparePoints?.length ? `<span><i class="dashed" style="background:${escapeHtml(cssVar("--chart-line", "#22577a"))}"></i>${escapeHtml(t("trendBaseline"))}</span>` : ""}
    </div>
  `;
}

function drawTrend(canvas, state) {
  const prepared = prepareCanvas(canvas);
  if (!prepared) return;
  const { ctx, dpr, width, height } = prepared;
  ctx.clearRect(0, 0, width, height);
  const clean = downsampleSeries((state?.points || []).filter(p => p.primary_remaining_percent !== null && p.primary_remaining_percent !== undefined), 720);
  const compare = downsampleSeries((state?.comparePoints || []).filter(p => p.primary_remaining_percent !== null && p.primary_remaining_percent !== undefined), 720);
  CHART_HIT_AREAS.set(canvas, []);
  if (clean.length < 2) return;
  const leftPad = 34 * dpr;
  const rightPad = 12 * dpr;
  const topPad = 10 * dpr;
  const bottomPad = 34 * dpr;
  const plotWidth = Math.max(1, width - leftPad - rightPad);
  const plotHeight = Math.max(1, height - topPad - bottomPad);
  const rangeStart = new Date(state?.rangeStart || clean[0].timestamp).getTime();
  const rangeEnd = new Date(state?.rangeEnd || clean[clean.length - 1].timestamp).getTime();
  const compareRangeStart = new Date(state?.compareRangeStart || compare[0]?.timestamp || state?.rangeStart || clean[0].timestamp).getTime();
  const compareRangeEnd = new Date(state?.compareRangeEnd || compare[compare.length - 1]?.timestamp || state?.rangeEnd || clean[clean.length - 1].timestamp).getTime();
  const xForTime = (timestamp, start = rangeStart, end = rangeEnd) => {
    const value = new Date(timestamp).getTime();
    if (!Number.isFinite(value) || !Number.isFinite(start) || !Number.isFinite(end) || end <= start) return leftPad;
    return leftPad + Math.max(0, Math.min(1, (value - start) / (end - start))) * plotWidth;
  };
  const labelColor = cssVar("--chart-label", "#667085");
  ctx.strokeStyle = cssVar("--chart-grid", "#d7dee8");
  ctx.lineWidth = 1 * dpr;
  for (let i = 0; i <= 4; i += 1) {
    const y = topPad + plotHeight * i / 4;
    ctx.beginPath();
    ctx.moveTo(leftPad, y);
    ctx.lineTo(width - rightPad, y);
    ctx.stroke();
    const label = `${100 - i * 25}`;
    ctx.fillStyle = labelColor;
    ctx.font = `${10 * dpr}px system-ui`;
    ctx.textAlign = "right";
    ctx.fillText(label, leftPad - 6 * dpr, y + 3 * dpr);
  }
  const areas = [];
  const drawWindowLine = (series, key, color, dashed = false, widthScale = 1, start = rangeStart, end = rangeEnd) => {
    if (!series.length) return;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2 * dpr * widthScale;
    ctx.setLineDash(dashed ? [5 * dpr, 4 * dpr] : []);
    ctx.beginPath();
    series.forEach((p, i) => {
      const x = xForTime(p.timestamp, start, end);
      const y = topPad + plotHeight - plotHeight * Number(p[key] || 0) / 100;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.restore();
  };
  const primaryColor = cssVar("--chart-line", "#22577a");
  const secondaryColor = cssVar("--chart-reason", "#7a4d9f");
  drawWindowLine(compare, "primary_remaining_percent", primaryColor, true, .75, compareRangeStart, compareRangeEnd);
  drawWindowLine(compare, "secondary_remaining_percent", secondaryColor, true, .75, compareRangeStart, compareRangeEnd);
  drawWindowLine(clean, "primary_remaining_percent", primaryColor);
  drawWindowLine(clean, "secondary_remaining_percent", secondaryColor);
  const latest = clean[clean.length - 1];
  if (latest) {
    const latestX = xForTime(latest.timestamp);
    drawEndLabel(ctx, dpr, latestX, topPad + plotHeight - plotHeight * Number(latest.primary_remaining_percent || 0) / 100, `5h ${fmtPercent(latest.primary_remaining_percent, 0)}`, primaryColor, width, height);
    drawEndLabel(ctx, dpr, latestX, topPad + plotHeight - plotHeight * Number(latest.secondary_remaining_percent || 0) / 100, `${currentLang === "zh" ? "周" : "W"} ${fmtPercent(latest.secondary_remaining_percent, 0)}`, secondaryColor, width, height);
  }
  clean.forEach((p, i) => {
    const x = xForTime(p.timestamp);
    const y = topPad + plotHeight - plotHeight * Number(p.primary_remaining_percent) / 100;
    const compareIndex = compare.length ? Math.min(compare.length - 1, Math.round(i * (compare.length - 1) / Math.max(1, clean.length - 1))) : -1;
    const comparePoint = compareIndex >= 0 ? compare[compareIndex] : null;
    areas.push({
      x: x / dpr - 7,
      y: y / dpr - 7,
      cx: x / dpr,
      cy: y / dpr,
      w: 14,
      h: 14,
      radius: 38,
      summary: `${fmtTimeLocalized(p.timestamp)} · 5h ${fmtPercent(p.primary_remaining_percent)} · ${currentLang === "zh" ? "周" : "Weekly"} ${fmtPercent(p.secondary_remaining_percent)}`,
      text: [
        `${currentLang === "zh" ? "时间" : "Time"}: ${fmtTimeLocalized(p.timestamp)}`,
        `${t("trendCurrent")} 5h ${t("left")}: ${fmtPercent(p.primary_remaining_percent)}`,
        `${t("trendCurrent")} ${currentLang === "zh" ? "每周" : "Weekly"} ${t("left")}: ${fmtPercent(p.secondary_remaining_percent)}`,
        `${currentLang === "zh" ? "展示处理" : "Display"}: ${t("windowTrendQuality")}`,
        `${currentLang === "zh" ? "聚合样本" : "Bucket samples"}: ${p.sample_count || 1}${p.source ? ` (${p.source})` : ""}`,
        p.primary_reset_inferred || p.secondary_reset_inferred ? `${currentLang === "zh" ? "推断 reset" : "Inferred reset"}: yes` : null,
        comparePoint ? `${t("trendBaseline")} 5h ${t("left")}: ${fmtPercent(comparePoint.primary_remaining_percent)}` : null,
        comparePoint ? `${t("trendBaseline")} ${currentLang === "zh" ? "每周" : "Weekly"} ${t("left")}: ${fmtPercent(comparePoint.secondary_remaining_percent)}` : null,
        `${currentLang === "zh" ? "Token 合计" : "Token total"}: ${fmtTokens(p.token_used_total)}`,
      ].filter(Boolean).join("\n"),
    });
  });
  CHART_HIT_AREAS.set(canvas, areas);
  ctx.strokeStyle = cssVar("--chart-grid", "#d7dee8");
  ctx.lineWidth = 1 * dpr;
  ctx.beginPath();
  ctx.moveTo(leftPad, topPad + plotHeight);
  ctx.lineTo(width - rightPad, topPad + plotHeight);
  ctx.stroke();

  const ticks = timelineTicksForRange(state?.rangeStart || clean[0].timestamp, state?.rangeEnd || clean[clean.length - 1].timestamp, 5);
  ticks.forEach((tick) => {
    const x = leftPad + tick.ratio * plotWidth;
    ctx.strokeStyle = cssVar("--chart-grid", "#d7dee8");
    ctx.beginPath();
    ctx.moveTo(x, topPad + plotHeight);
    ctx.lineTo(x, topPad + plotHeight + 5 * dpr);
    ctx.stroke();
    ctx.fillStyle = labelColor;
    ctx.font = `${10 * dpr}px system-ui`;
    ctx.textAlign = tick.ratio === 0 ? "left" : tick.ratio === 1 ? "right" : "center";
    ctx.fillText(formatTimelineLabel(tick.timestamp), x, height - 10 * dpr);
  });
}

function tokenTrendValue(point) {
  return Number(point?.token_used_total ?? point?.total_tokens ?? 0);
}

function compactTokenPoint(point) {
  const totalTokens = Number(point?.total_tokens ?? 0);
  const aggregate = Number(point?.token_used_total ?? totalTokens);
  return {
    timestamp: point?.timestamp || point?.sampled_at,
    session_id: String(point?.session_id || ""),
    cwd: point?.cwd || point?.project || "",
    project: point?.project || point?.cwd || "",
    display_name: point?.display_name || point?.thread_name || point?.project || point?.cwd || point?.session_id || "--",
    display_name_source: point?.display_name_source || (point?.thread_name ? "thread_index" : "path"),
    thread_name: point?.thread_name || "",
    total_tokens: totalTokens,
    upload_tokens: Number(point?.upload_tokens ?? 0),
    output_tokens: Number(point?.output_tokens ?? 0),
    contextual_tokens: Number(point?.contextual_tokens ?? point?.cached_input_tokens ?? 0),
    reasoning_tokens: Number(point?.reasoning_tokens ?? point?.reasoning_output_tokens ?? 0),
    token_used_total: Number.isFinite(aggregate) ? aggregate : totalTokens,
  };
}

function allTokenSamples(data) {
  const raw = (data?.token_timeline_points || []).length ? data.token_timeline_points : (data?.trend_points || []);
  return raw
    .map(compactTokenPoint)
    .filter(point => point.timestamp && Number.isFinite(tokenTrendValue(point)) && tokenTrendValue(point) > 0)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
}

function tokenTrendPeriods(data, mode) {
  const keys = new Set();
  allTokenSamples(data).forEach(point => {
    const date = new Date(point.timestamp);
    keys.add(mode === "week" ? weekStartKeyFromDate(date) : isoDateKey(date));
  });
  return Array.from(keys).filter(Boolean).sort();
}

function selectedTokenTrendState(data) {
  const validModes = new Set(["recent", "day", "week"]);
  if (!validModes.has(tokenTrendMode)) tokenTrendMode = "recent";
  const samples = allTokenSamples(data);
  if (!samples.length) return {mode: tokenTrendMode, points: [], comparePoints: [], periods: [], label: "--", compareLabel: "--"};
  if (tokenTrendMode === "recent") {
    const lastDate = new Date(samples[samples.length - 1].timestamp);
    const cutoff = new Date(lastDate.getTime() - 24 * 60 * 60 * 1000);
    const points = samples.filter(point => new Date(point.timestamp) >= cutoff);
    return {
      mode: "recent",
      points,
      comparePoints: [],
      periods: [],
      label: t("last24h"),
      compareLabel: "",
      rangeStart: cutoff.toISOString(),
      rangeEnd: lastDate.toISOString(),
    };
  }
  const mode = tokenTrendMode;
  const periods = tokenTrendPeriods(data, mode);
  let key = tokenTrendPeriod[mode];
  if (!key || !periods.includes(key)) key = periods[periods.length - 1] || "";
  tokenTrendPeriod[mode] = key;
  const periodMatch = (point, wanted) => {
    const date = new Date(point.timestamp);
    return (mode === "week" ? weekStartKeyFromDate(date) : isoDateKey(date)) === wanted;
  };
  const points = samples.filter(point => periodMatch(point, key));
  const range = periodRange(key, mode);
  const compareMode = tokenTrendCompareMode[mode] || "previous";
  let compareKey = "";
  if (compareMode === "previous") {
    const index = periods.indexOf(key);
    compareKey = index > 0 ? periods[index - 1] : "";
  } else if (compareMode === "year") {
    const wanted = subtractYearKey(key, mode);
    compareKey = periods.includes(wanted) ? wanted : "";
  }
  const comparePoints = compareKey ? samples.filter(point => periodMatch(point, compareKey)) : [];
  const compareRange = compareKey ? periodRange(compareKey, mode) : {start: null, end: null};
  return {
    mode,
    points,
    comparePoints,
    periods,
    selectedKey: key,
    compareMode,
    label: periodLabelFromKey(key, mode),
    compareLabel: compareKey ? periodLabelFromKey(compareKey, mode) : t("trendCompareNone"),
    rangeStart: range.start?.toISOString(),
    rangeEnd: range.end?.toISOString(),
    compareRangeStart: compareRange.start?.toISOString(),
    compareRangeEnd: compareRange.end?.toISOString(),
  };
}

function renderTokenTrendControls(data, state) {
  const box = byId("token-trend-controls");
  if (!box) return;
  const mode = state.mode || tokenTrendMode;
  const periods = mode === "day" || mode === "week" ? state.periods || [] : [];
  const selectedKey = state.selectedKey || "";
  const coverage = mode === "recent" ? coverageLabel(state.points, state.rangeStart, state.rangeEnd) : "";
  setText("token-trend-subtitle", mode === "recent" ? `${t("tokenUsedTrendSubtitle")}${coverage ? ` · ${coverage}` : ""}` : `${state.label}${state.comparePoints?.length ? ` · ${t("trendBaseline")} ${state.compareLabel}` : ""}`);
  box.innerHTML = `
    ${["recent", "day", "week"].map(item => `
      <button class="chart-control-button ${mode === item ? "active" : ""}" type="button" data-token-trend-mode="${item}">
        ${item === "recent" ? t("trendModeRecent") : item === "day" ? t("trendModeDay") : t("trendModeWeek")}
      </button>
    `).join("")}
    ${mode === "day" || mode === "week" ? `
      <label>
        <span>${t("trendPeriod")}</span>
        <select class="chart-control-select" data-token-trend-period="${mode}">
          ${periods.map(key => `<option value="${escapeHtml(key)}" ${key === selectedKey ? "selected" : ""}>${escapeHtml(periodLabelFromKey(key, mode))}</option>`).join("")}
        </select>
      </label>
      <label>
        <span>${t("trendCompare")}</span>
        <select class="chart-control-select" data-token-trend-compare="${mode}">
          <option value="none" ${state.compareMode === "none" ? "selected" : ""}>${t("trendCompareNone")}</option>
          <option value="previous" ${state.compareMode === "previous" ? "selected" : ""}>${t("trendComparePrevious")}</option>
          <option value="year" ${state.compareMode === "year" ? "selected" : ""}>${t("trendCompareYear")}</option>
        </select>
      </label>
    ` : ""}
    <button class="chart-control-button ghost" type="button" data-chart-download="token-trend-chart">${t("downloadPng")}</button>
    <button class="chart-control-button ghost" type="button" data-chart-clear-focus>${t("resetFocus")}</button>
    <div class="chart-legend" title="${escapeHtml(t("chartInteractionHint"))}">
      <span><i style="background:${escapeHtml(cssVar("--chart-output", "#d92d20"))}"></i>${escapeHtml(t("aggregateLine"))}</span>
      ${state.comparePoints?.length ? `<span><i class="dashed" style="background:${escapeHtml(cssVar("--chart-output", "#d92d20"))}"></i>${escapeHtml(t("trendBaseline"))}</span>` : ""}
      <span><i style="background:${escapeHtml(cssVar("--chart-line", "#22577a"))}"></i>${escapeHtml(t("sessionLines"))}</span>
    </div>
  `;
}

function tokenSessionLabel(point, duplicateNames = null) {
  const base = displayProjectName({
    project: point.project || point.cwd,
    display_name: point.display_name,
    display_name_source: point.display_name_source,
  });
  const session = String(point.session_id || "");
  if (duplicateNames && duplicateNames.get(base) > 1 && session) return `${base} · ${session.slice(0, 8)}`;
  return base;
}

function tokenSessionGroups(points, limit = 8) {
  const grouped = new Map();
  points.forEach(point => {
    const sessionId = point.session_id || `${point.project || point.cwd || "unknown"}-${point.timestamp}`;
    if (!grouped.has(sessionId)) {
      grouped.set(sessionId, {
        session_id: sessionId,
        display_name: point.display_name,
        display_name_source: point.display_name_source,
        project: point.project,
        cwd: point.cwd,
        points: [],
        latest: point,
      });
    }
    const group = grouped.get(sessionId);
    group.points.push(point);
    if (new Date(point.timestamp) >= new Date(group.latest.timestamp)) group.latest = point;
  });
  const baseNameCounts = new Map();
  grouped.forEach(group => {
    const base = tokenSessionLabel(group.latest);
    baseNameCounts.set(base, (baseNameCounts.get(base) || 0) + 1);
  });
  const rows = Array.from(grouped.values()).map(group => {
    group.points.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    group.project_label = displayProjectName({
      project: group.latest?.project || group.latest?.cwd || group.project || group.cwd,
      display_name: group.latest?.display_name || group.display_name,
      display_name_source: group.latest?.display_name_source || group.display_name_source,
    });
    group.label = tokenSessionLabel(group.latest, baseNameCounts);
    group.latest_total_tokens = Number(group.latest?.total_tokens || 0);
    group.event_count = group.points.length;
    return group;
  });
  rows.sort((a, b) => b.latest_total_tokens - a.latest_total_tokens);
  return rows.slice(0, limit);
}

function tokenLineColors() {
  return [
    cssVar("--chart-line", "#22577a"),
    cssVar("--chart-reason", "#7a4d9f"),
    cssVar("--accent", "#116b5d"),
    cssVar("--chart-contextual", "#6c7a89"),
    "#00a3ff",
    "#7c5cff",
    cssVar("--chart-output", "#d92d20"),
    cssVar("--accent-2", "#22577a"),
  ];
}

function tokenVisibleSessionGroups(points, limit = 8) {
  return tokenSessionGroups(points, limit).filter(group => tokenLineEnabled("session", group.session_id, true));
}

function renderTokenLineSelector(state) {
  const el = byId("token-line-selector");
  if (!el) return;
  const groups = tokenSessionGroups((state?.points || []).filter(point => point.timestamp), 8);
  const colors = tokenLineColors();
  const hasBaseline = Boolean((state?.comparePoints || []).length);
  el.innerHTML = `
    <div class="token-line-selector-head">
      <strong>${escapeHtml(t("tokenTrendLines"))}</strong>
      <span>${escapeHtml(t("sessionLines"))}</span>
    </div>
    <div class="token-line-options">
      <label class="token-line-option" title="${escapeHtml(t("aggregateLine"))}">
        <input type="checkbox" data-token-line="aggregate" ${tokenLineEnabled("aggregate") ? "checked" : ""}>
        <i style="background:${escapeHtml(cssVar("--chart-output", "#d92d20"))}"></i>
        <span>${escapeHtml(t("aggregateLine"))}</span>
      </label>
      <label class="token-line-option ${hasBaseline ? "" : "disabled"}" title="${escapeHtml(t("baselineLine"))}">
        <input type="checkbox" data-token-line="baseline" ${tokenLineEnabled("baseline") ? "checked" : ""} ${hasBaseline ? "" : "disabled"}>
        <i class="dashed" style="background:${escapeHtml(cssVar("--chart-output", "#d92d20"))}"></i>
        <span>${escapeHtml(t("baselineLine"))}</span>
      </label>
      ${groups.map((group, index) => `
        <label class="token-line-option" title="${escapeHtml(`${t("lineProject")}: ${group.project_label}\n${t("sessionLine")}: ${group.label}\n${t("realPath")}: ${group.latest?.cwd || group.latest?.project || "--"}\n${t("nameSource")}: ${displayNameSourceLabel(group.latest?.display_name_source)}\n${t("tokens")}: ${fmtTokens(group.latest_total_tokens)}`)}">
          <input type="checkbox" data-token-line="session" data-token-line-id="${escapeHtml(group.session_id)}" ${tokenLineEnabled("session", group.session_id, true) ? "checked" : ""}>
          <i style="background:${escapeHtml(colors[index % colors.length])}"></i>
          <span class="token-line-text">
            <strong>${escapeHtml(`${t("lineProject")}: ${group.project_label}`)}</strong>
            <small>${escapeHtml(`${displayNameSourceLabel(group.latest?.display_name_source)}${group.label !== group.project_label ? ` · ${group.label}` : ""}`)}</small>
          </span>
        </label>
      `).join("")}
    </div>
  `;
}

function drawTokenTrend(canvas, state) {
  const prepared = prepareCanvas(canvas);
  if (!prepared) return;
  const { ctx, dpr, width, height } = prepared;
  ctx.clearRect(0, 0, width, height);
  const clean = downsampleSeries((state?.points || []).filter(p => p.timestamp && tokenTrendValue(p) > 0), 720);
  const compare = downsampleSeries((state?.comparePoints || []).filter(p => p.timestamp && tokenTrendValue(p) > 0), 720);
  const sessionGroups = tokenVisibleSessionGroups(clean, 8);
  const showAggregate = tokenLineEnabled("aggregate");
  const showBaseline = tokenLineEnabled("baseline") && compare.length > 1;
  CHART_HIT_AREAS.set(canvas, []);
  if (clean.length < 2) return;
  const leftPad = 46 * dpr;
  const rightPad = 12 * dpr;
  const topPad = 10 * dpr;
  const bottomPad = 34 * dpr;
  const plotWidth = Math.max(1, width - leftPad - rightPad);
  const plotHeight = Math.max(1, height - topPad - bottomPad);
  const values = [
    ...(showAggregate ? clean.map(tokenTrendValue) : []),
    ...(showBaseline ? compare.map(tokenTrendValue) : []),
    ...sessionGroups.flatMap(group => group.points.map(point => Number(point.total_tokens || 0))),
  ].filter(value => Number.isFinite(value) && value > 0);
  if (!values.length) {
    ctx.fillStyle = cssVar("--chart-label", "#667085");
    ctx.font = `${13 * dpr}px system-ui`;
    ctx.textAlign = "center";
    ctx.fillText(t("noLinesSelected"), width / 2, height / 2);
    return;
  }
  let minValue = Math.min(...values);
  let maxValue = Math.max(...values);
  if (maxValue === minValue) {
    minValue = Math.max(0, minValue * 0.98);
    maxValue = maxValue * 1.02 + 1;
  }
  const padding = Math.max(1, (maxValue - minValue) * 0.08);
  minValue = Math.max(0, minValue - padding);
  maxValue += padding;
  const yFor = (value) => topPad + plotHeight - plotHeight * (Number(value || 0) - minValue) / Math.max(1, maxValue - minValue);
  const cleanStart = new Date(state?.rangeStart || clean[0].timestamp).getTime();
  const cleanEnd = new Date(state?.rangeEnd || clean[clean.length - 1].timestamp).getTime();
  const xForTime = (timestamp) => {
    const tValue = new Date(timestamp).getTime();
    if (!Number.isFinite(tValue) || cleanEnd <= cleanStart) return leftPad;
    return leftPad + (tValue - cleanStart) * plotWidth / (cleanEnd - cleanStart);
  };
  const compareStart = new Date(state?.compareRangeStart || compare[0]?.timestamp || state?.rangeStart || clean[0].timestamp).getTime();
  const compareEnd = new Date(state?.compareRangeEnd || compare[compare.length - 1]?.timestamp || state?.rangeEnd || clean[clean.length - 1].timestamp).getTime();
  const xForCompareTime = (timestamp) => {
    const tValue = new Date(timestamp).getTime();
    if (!Number.isFinite(tValue) || compareEnd <= compareStart) return leftPad;
    return leftPad + (tValue - compareStart) * plotWidth / (compareEnd - compareStart);
  };
  const labelColor = cssVar("--chart-label", "#667085");
  ctx.strokeStyle = cssVar("--chart-grid", "#d7dee8");
  ctx.lineWidth = 1 * dpr;
  for (let i = 0; i <= 4; i += 1) {
    const y = topPad + plotHeight * i / 4;
    const value = maxValue - (maxValue - minValue) * i / 4;
    ctx.beginPath();
    ctx.moveTo(leftPad, y);
    ctx.lineTo(width - rightPad, y);
    ctx.stroke();
    ctx.fillStyle = labelColor;
    ctx.font = `${10 * dpr}px system-ui`;
    ctx.textAlign = "right";
    ctx.fillText(fmtTokens(value), leftPad - 6 * dpr, y + 3 * dpr);
  }
  const drawLine = (series, valueFn, color, dashed = false, widthScale = 1, xFn = xForTime) => {
    if (series.length < 2) return;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2 * dpr * widthScale;
    ctx.setLineDash(dashed ? [5 * dpr, 4 * dpr] : []);
    ctx.beginPath();
    series.forEach((point, index) => {
      const x = xFn(point.timestamp);
      const y = yFor(valueFn(point));
      if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.restore();
  };
  const aggregateColor = cssVar("--chart-output", "#d92d20");
  if (showBaseline) drawLine(compare, tokenTrendValue, aggregateColor, true, .8, xForCompareTime);
  const sessionColors = tokenLineColors();
  sessionGroups.forEach((group, index) => {
    drawLine(group.points, point => Number(point.total_tokens || 0), sessionColors[index % sessionColors.length], false, .62, xForTime);
  });
  if (showAggregate) drawLine(clean, tokenTrendValue, aggregateColor, false, 1.15, xForTime);
  if (showAggregate && clean.length) {
    const latest = clean[clean.length - 1];
    drawEndLabel(ctx, dpr, xForTime(latest.timestamp), yFor(tokenTrendValue(latest)), fmtTokens(tokenTrendValue(latest)), aggregateColor, width, height);
  }
  sessionGroups.slice(0, 4).forEach((group, index) => {
    const latest = group.points[group.points.length - 1];
    if (!latest) return;
    drawEndLabel(ctx, dpr, xForTime(latest.timestamp), yFor(Number(latest.total_tokens || 0)), group.project_label.slice(0, 18), sessionColors[index % sessionColors.length], width, height);
  });
  const areas = [];
  if (showAggregate) clean.forEach((p, i) => {
    const value = tokenTrendValue(p);
    const x = xForTime(p.timestamp);
    const y = yFor(value);
    const compareIndex = compare.length ? Math.min(compare.length - 1, Math.round(i * (compare.length - 1) / Math.max(1, clean.length - 1))) : -1;
    const comparePoint = compareIndex >= 0 ? compare[compareIndex] : null;
    areas.push({
      x: x / dpr - 7,
      y: y / dpr - 7,
      cx: x / dpr,
      cy: y / dpr,
      w: 14,
      h: 14,
      radius: 38,
      summary: `${fmtTimeLocalized(p.timestamp)} · ${t("tokenTrendAllSessions")} ${fmtTokens(value)}`,
      text: [
        `${currentLang === "zh" ? "时间" : "Time"}: ${fmtTimeLocalized(p.timestamp)}`,
        `${t("tokenTrendAllSessions")}: ${fmtTokens(value)}`,
        showBaseline && comparePoint ? `${t("trendBaseline")} ${t("tokenTrendAllSessions")}: ${fmtTokens(tokenTrendValue(comparePoint))}` : null,
        `${t("lineProject")}: ${tokenSessionLabel(p)}`,
        `${currentLang === "zh" ? "当前事件 Session Token" : "Current event session tokens"}: ${fmtTokens(p.total_tokens)}`,
        `${t("nameSource")}: ${displayNameSourceLabel(p.display_name_source)}`,
      ].filter(Boolean).join("\n"),
    });
  });
  sessionGroups.forEach((group, index) => {
    const colorLabel = `${t("sessionLine")}: ${group.label}`;
    group.points.forEach((p) => {
      const x = xForTime(p.timestamp);
      const y = yFor(Number(p.total_tokens || 0));
      areas.push({
        x: x / dpr - 6,
        y: y / dpr - 6,
        cx: x / dpr,
        cy: y / dpr,
        w: 12,
        h: 12,
        radius: 34,
        summary: `${fmtTimeLocalized(p.timestamp)} · ${group.project_label} · ${fmtTokens(p.total_tokens)}`,
        text: [
          `${currentLang === "zh" ? "时间" : "Time"}: ${fmtTimeLocalized(p.timestamp)}`,
          `${t("lineProject")}: ${group.project_label}`,
          colorLabel,
          `${t("realPath")}: ${p.cwd || p.project || "--"}`,
          `${t("tokens")}: ${fmtTokens(p.total_tokens)}`,
          `${t("upload")}: ${fmtTokens(p.upload_tokens)}`,
          `${t("download")}: ${fmtTokens(p.output_tokens)}`,
          `${t("contextual")}: ${fmtTokens(p.contextual_tokens)}`,
          `${t("reason")}: ${fmtTokens(p.reasoning_tokens)}`,
          `${t("nameSource")}: ${displayNameSourceLabel(p.display_name_source)}`,
        ].join("\n"),
      });
    });
  });
  CHART_HIT_AREAS.set(canvas, areas);
  ctx.strokeStyle = cssVar("--chart-grid", "#d7dee8");
  ctx.lineWidth = 1 * dpr;
  ctx.beginPath();
  ctx.moveTo(leftPad, topPad + plotHeight);
  ctx.lineTo(width - rightPad, topPad + plotHeight);
  ctx.stroke();

  const ticks = timelineTicksForRange(state?.rangeStart || clean[0].timestamp, state?.rangeEnd || clean[clean.length - 1].timestamp, 5);
  ticks.forEach((tick) => {
    const x = leftPad + tick.ratio * plotWidth;
    ctx.strokeStyle = cssVar("--chart-grid", "#d7dee8");
    ctx.beginPath();
    ctx.moveTo(x, topPad + plotHeight);
    ctx.lineTo(x, topPad + plotHeight + 5 * dpr);
    ctx.stroke();
    ctx.fillStyle = labelColor;
    ctx.font = `${10 * dpr}px system-ui`;
    ctx.textAlign = tick.ratio === 0 ? "left" : tick.ratio === 1 ? "right" : "center";
    ctx.fillText(formatTimelineLabel(tick.timestamp), x, height - 10 * dpr);
  });
}

function timelineTicks(points, count = 5) {
  const clean = points.filter(point => point.timestamp);
  if (!clean.length) return [];
  const lastIndex = clean.length - 1;
  const wanted = Math.max(2, Math.min(count, clean.length));
  const seen = new Set();
  const ticks = [];
  for (let i = 0; i < wanted; i += 1) {
    const index = Math.round(i * lastIndex / (wanted - 1));
    if (seen.has(index)) continue;
    seen.add(index);
    ticks.push({index, timestamp: clean[index].timestamp});
  }
  return ticks;
}

function formatTimelineLabel(iso) {
  if (!iso) return "--";
  const date = new Date(iso);
  return date.toLocaleTimeString(currentLang === "zh" ? "zh-CN" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderTrendTimeline(state) {
  const el = byId("trend-timeline");
  if (!el) return;
  const clean = (state?.points || []).filter(p => p.primary_remaining_percent !== null && p.primary_remaining_percent !== undefined && p.timestamp);
  if (clean.length < 2) {
    el.innerHTML = "";
    return;
  }
  const ticks = timelineTicksForRange(state?.rangeStart || clean[0].timestamp, state?.rangeEnd || clean[clean.length - 1].timestamp, 5);
  el.innerHTML = ticks.map((tick, index) => `
    <span class="timeline-tick ${index === 0 ? "start" : index === ticks.length - 1 ? "end" : ""}" title="${escapeHtml(`${t("timeline")}: ${fmtTimeLocalized(tick.timestamp)}`)}">
      <i></i>
      <b>${escapeHtml(formatTimelineLabel(tick.timestamp))}</b>
    </span>
  `).join("");
}

function renderTokenTrendTimeline(state) {
  const el = byId("token-trend-timeline");
  if (!el) return;
  const clean = (state?.points || []).filter(p => p.timestamp && tokenTrendValue(p) > 0);
  if (clean.length < 2) {
    el.innerHTML = "";
    return;
  }
  const ticks = timelineTicksForRange(state?.rangeStart || clean[0].timestamp, state?.rangeEnd || clean[clean.length - 1].timestamp, 5);
  el.innerHTML = ticks.map((tick, index) => `
    <span class="timeline-tick ${index === 0 ? "start" : index === ticks.length - 1 ? "end" : ""}" title="${escapeHtml(`${t("timeline")}: ${fmtTimeLocalized(tick.timestamp)}`)}">
      <i></i>
      <b>${escapeHtml(formatTimelineLabel(tick.timestamp))}</b>
    </span>
  `).join("");
}

function renderTokenSessionBreakdown(state) {
  const el = byId("token-session-breakdown");
  if (!el) return;
  const groups = tokenSessionGroups((state?.points || []).filter(point => point.timestamp), 8);
  if (!groups.length) {
    el.innerHTML = `<div class="empty-state">${escapeHtml(t("tokenTrendNoSessionData"))}</div>`;
    return;
  }
  const colors = [
    cssVar("--chart-line", "#22577a"),
    cssVar("--chart-reason", "#7a4d9f"),
    cssVar("--accent", "#116b5d"),
    cssVar("--chart-contextual", "#6c7a89"),
    "#00a3ff",
    "#7c5cff",
    cssVar("--chart-output", "#d92d20"),
    cssVar("--accent-2", "#22577a"),
  ];
  el.innerHTML = `
    <div class="token-session-head">
      <strong>${escapeHtml(t("tokenSessionBreakdown"))}</strong>
      <span>${escapeHtml(t("tokenTrendTopSessions"))}</span>
    </div>
    <div class="token-session-grid">
      ${groups.map((group, index) => {
        const latest = group.latest || {};
        const tooltip = [
          `${t("lineProject")}: ${group.project_label}`,
          `${t("sessionLine")}: ${group.label}`,
          `${t("nameSource")}: ${displayNameSourceLabel(latest.display_name_source)}`,
          `${t("realPath")}: ${latest.cwd || latest.project || "--"}`,
          `${t("tokens")}: ${fmtTokens(group.latest_total_tokens)}`,
          `${t("upload")}: ${fmtTokens(latest.upload_tokens)}`,
          `${t("download")}: ${fmtTokens(latest.output_tokens)}`,
          `${t("contextual")}: ${fmtTokens(latest.contextual_tokens)}`,
          `${t("reason")}: ${fmtTokens(latest.reasoning_tokens)}`,
          `${t("events")}: ${group.event_count}`,
          `${t("lastUpdate")}: ${fmtTimeLocalized(latest.timestamp)}`,
        ].join("\n");
        return `
          <div class="token-session-row" title="${escapeHtml(tooltip)}">
            <i style="background:${escapeHtml(colors[index % colors.length])}"></i>
            <div>
              <strong>${escapeHtml(`${t("lineProject")}: ${group.project_label}`)}</strong>
              <span>${escapeHtml(`${displayNameSourceLabel(latest.display_name_source)}${group.label !== group.project_label ? ` · ${group.label}` : ""} · ${fmtTimeLocalized(latest.timestamp)}`)}</span>
            </div>
            <b>${escapeHtml(fmtTokens(group.latest_total_tokens))}</b>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function ensureChartTooltip() {
  if (chartTooltipEl) return chartTooltipEl;
  chartTooltipEl = document.createElement("div");
  chartTooltipEl.className = "chart-tooltip";
  chartTooltipEl.hidden = true;
  document.body.appendChild(chartTooltipEl);
  return chartTooltipEl;
}

function setupChartTooltips() {
  document.querySelectorAll(".chart-canvas").forEach((canvas) => {
    canvas.setAttribute("title", t("chartInteractionHint"));
    canvas.setAttribute("tabindex", "0");
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", t("chartInteractionHint"));
    setChartDetail(canvas, null);
    if (canvas.dataset.tooltipReady === "1") return;
    canvas.dataset.tooltipReady = "1";
    const showTooltip = (event) => {
      if (pinnedChart?.canvas === canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      showChartTooltip(canvas, nearestChartHit(canvas, x, y), event);
    };
    const lockTooltip = (event) => {
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const hit = nearestChartHit(canvas, x, y);
      if (!hit) {
        clearPinnedChart();
        return;
      }
      pinnedChart = {canvas, hit};
      showChartTooltip(canvas, hit, event, true);
    };
    const hideTooltip = () => {
      if (pinnedChart?.canvas === canvas) return;
      ensureChartTooltip().hidden = true;
      canvas.style.cursor = "default";
      setChartDetail(canvas, null);
    };
    const focusLatest = () => {
      const areas = CHART_HIT_AREAS.get(canvas) || [];
      const hit = areas[areas.length - 1];
      if (hit) setChartDetail(canvas, hit, false);
    };
    canvas.addEventListener("pointermove", showTooltip);
    canvas.addEventListener("pointerdown", lockTooltip);
    canvas.addEventListener("pointerleave", hideTooltip);
    canvas.addEventListener("pointercancel", hideTooltip);
    canvas.addEventListener("focus", focusLatest);
    canvas.addEventListener("blur", hideTooltip);
  });
}

function applyTokenTrendVisibility() {
  const input = byId("token-trend-visible-toggle");
  const body = byId("token-trend-body");
  if (input) {
    input.checked = tokenTrendVisible;
    input.setAttribute("aria-pressed", String(tokenTrendVisible));
    input.setAttribute("title", tip("showTokenTrend"));
  }
  if (body) body.hidden = !tokenTrendVisible;
}

function renderCharts(data) {
  if (!data?.latest_event) return;
  const windowTrendState = selectedWindowTrendState(data);
  renderWindowTrendControls(data, windowTrendState);
  drawTrend(byId("trend-chart"), windowTrendState);
  renderTrendTimeline(windowTrendState);
  const tokenTrendState = selectedTokenTrendState(data);
  renderTokenTrendControls(data, tokenTrendState);
  applyTokenTrendVisibility();
  if (tokenTrendVisible) {
    renderTokenLineSelector(tokenTrendState);
    drawTokenTrend(byId("token-trend-chart"), tokenTrendState);
    renderTokenTrendTimeline(tokenTrendState);
    renderTokenSessionBreakdown(tokenTrendState);
  }
}

function uploadTokenCount(total) {
  return Math.max(0, Number(total?.input_tokens || 0) - Number(total?.cached_input_tokens || 0));
}

function contextualTokenCount(total) {
  return Math.max(0, Number(total?.cached_input_tokens || 0));
}

function renderComparisons(data) {
  const box = byId("comparisons");
  if (!box) return;
  box.dataset.format = comparisonFormat;
  box.setAttribute("title", tip("comparisonClickHint"));
  box.setAttribute("aria-label", `${t("trendComparison")}: ${comparisonFormatLabel()}`);
  const dod = data.period_comparisons?.day_over_day || {};
  const wow = data.period_comparisons?.week_over_week || {};
  const tokenSummary = tokenUsageSummary(data);
  const tokenCards = [
    [t("total"), tokenSummary.total, t("totalTokenUsed")],
    [t("past24h"), tokenSummary.pastDay, `${t("observedCoverage")} ${fmtPercent(tokenSummary.pastDayCoverage, 0)}`],
    [t("past7d"), tokenSummary.pastWeek, `${t("observedCoverage")} ${fmtPercent(tokenSummary.pastWeekCoverage, 0)}`],
    [t("dailyAvg"), tokenSummary.dailyAvg, t("past7d")],
    [t("weeklyAvg"), tokenSummary.weeklyAvg, t("past7d")],
  ];
  const rows = [
    ["Tokens", dod.tokens, wow.tokens],
    ["Sessions", dod.sessions, wow.sessions],
    ["Events", dod.events, wow.events],
    ["Upload", dod.input, wow.input],
    ["Download", dod.output, wow.output],
    ["Contextual", dod.contextual, wow.contextual],
    ["Reasoning", dod.reasoning, wow.reasoning],
  ];
  const detailRows = rows.map(([label, day, week]) => {
    const dayTitle = comparisonValueTitle(day);
    const weekTitle = comparisonValueTitle(week);
    return `
    <div class="comparison-row">
      <strong>${escapeHtml(translateMetricLabel(label))}</strong>
      <button class="comparison-value" type="button" data-comparison-value="1" title="${escapeHtml(dayTitle)}" aria-label="${escapeHtml(`${t("dod")} ${translateMetricLabel(label)} ${comparisonFormatLabel()}`)}">
        <span>${t("dod")}</span>
        <b>${fmtDelta(day, comparisonFormat)}</b>
      </button>
      <button class="comparison-value" type="button" data-comparison-value="1" title="${escapeHtml(weekTitle)}" aria-label="${escapeHtml(`${t("wow")} ${translateMetricLabel(label)} ${comparisonFormatLabel()}`)}">
        <span>${t("wow")}</span>
        <b>${fmtDelta(week, comparisonFormat)}</b>
      </button>
    </div>
  `;
  }).join("");
  box.innerHTML = `
    <div class="comparison-token-summary">
      ${tokenCards.map(([label, value, sub]) => `
        <div class="comparison-token-card" title="${escapeHtml(`${label}: ${fmtTokens(value)}\n${sub}`)}">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(fmtTokens(value))}</strong>
          <small>${escapeHtml(sub)}</small>
        </div>
      `).join("")}
    </div>
    <div class="comparison-viz-grid">
      ${comparisonVizCard(t("dod"), dod.tokens)}
      ${comparisonVizCard(t("wow"), wow.tokens)}
    </div>
    <div class="comparison-detail-grid">${detailRows}</div>
  `;
}

function comparisonVizCard(label, item) {
  item = item || {};
  const current = Number(item.current || 0);
  const previous = Number(item.previous || 0);
  const max = Math.max(current, previous, 1);
  const currentWidth = Math.max(2, current * 100 / max);
  const previousWidth = Math.max(2, previous * 100 / max);
  const tooltip = [
    `${label} ${t("tokenUsed")}`,
    `${t("current")}: ${fmtTokens(current)}`,
    `${t("baseline")}: ${fmtTokens(previous)}`,
    `${comparisonFormatLabel()}: ${fmtDelta(item, comparisonFormat)}`,
  ].join("\n");
  return `
    <div class="comparison-viz-card" title="${escapeHtml(tooltip)}">
      <div class="comparison-viz-head">
        <strong>${escapeHtml(label)}</strong>
        <span>${escapeHtml(fmtDelta(item, comparisonFormat))}</span>
      </div>
      <div class="comparison-bars">
        <span>${t("current")}</span>
        <i><b style="width:${currentWidth}%"></b></i>
        <em>${escapeHtml(fmtTokens(current))}</em>
        <span>${t("baseline")}</span>
        <i class="baseline"><b style="width:${previousWidth}%"></b></i>
        <em>${escapeHtml(fmtTokens(previous))}</em>
      </div>
    </div>
  `;
}

function setupComparisonFormatToggle() {
  const box = byId("comparisons");
  if (!box) return;
  box.addEventListener("click", (event) => {
    if (!event.target.closest("[data-comparison-value]")) return;
    toggleComparisonFormat();
  });
}

function renderPatterns(data) {
  const box = byId("patterns");
  if (!box) return;
  const patterns = data.behavior_patterns || [];
  if (!patterns.length) {
    box.innerHTML = `<div class="insight"><strong>${t("noPatternData")}</strong><span>${t("moreHistoryNeeded")}</span></div>`;
    return;
  }

  const patternByName = Object.fromEntries(patterns.map(item => [item.name, item]));
  const activeSessions = Number(patternByName["Concurrent active work"]?.value || 0);
  const projectShare = Number(String(patternByName["Project concentration"]?.value || "0").replace("%", "")) || 0;
  const mix = String(patternByName["Token traffic mix"]?.value || "0% / 0% / 0% / 0%")
    .split("/")
    .map(part => Number(part.replace("%", "").trim()) || 0);
  const uploadShare = mix[0] || 0;
  const downloadShare = mix[1] || 0;
  const contextualShare = mix[2] || 0;
  const reasoningShare = mix[3] || 0;
  const activePressure = Math.min(100, activeSessions * 20);
  const activeSeverity = activeSessions >= 5 ? "high" : "normal";
  const projectSeverity = projectShare >= 50 ? "high" : "normal";
  const history = data.monitor_history || {};
  const rhythm = selectedOperatingRhythm(history, data.trend_points || []);
  const hourly = rhythm.hourly;
  const rhythmCompare = rhythm.mode === "day" || rhythm.mode === "week" ? selectedComparePeriod(rhythm.mode, rhythm) : {period: null};
  const compareHourly = rhythmCompare.period ? periodHourly(rhythmCompare.period, rhythm.mode) : [];
  const compareByHour = Object.fromEntries(compareHourly.map(item => [item.hour, item]));
  const maxHourly = Math.max(...hourly.map(item => item.count), ...compareHourly.map(item => item.count), 1);
  const peak = hourly.reduce((best, item) => item.count > best.count ? item : best, hourly[0]);
  const historySamples = Number(history.sample_count || 0);
  const monitorSamples = Number(history.persisted_sample_count || 0);
  const backfillSamples = Number(history.backfill_sample_count || 0);
  const historyTitle = [
    `${t("historySource")}`,
    `${t("historicalSamples")}: ${historySamples}`,
    `${t("monitorSamples")}: ${monitorSamples}`,
    `${t("backfilledSamples")}: ${backfillSamples}`,
    `${t("historySince")}: ${fmtTimeLocalized(history.first_sample_at)}`,
    `${t("lastRecord")}: ${fmtTimeLocalized(history.last_sample_at)}`,
    `${t("selectedPeriod")}: ${rhythm.label}`,
  ].join("\n");

  box.innerHTML = `
    <div class="behavior-viz">
      <div class="activity-card">
        ${operatingRhythmControls(history, rhythm)}
        <div class="activity-legend" title="${escapeHtml(tip("operatingRhythm"))}">
          <span><i class="legend-current"></i>${t("current")}</span>
          <span><i class="legend-baseline"></i>${t("baseline")}</span>
        </div>
        <div class="activity-head" title="${escapeHtml(historyTitle)}">
          <strong>${t("operatingRhythm")}</strong>
          <span>${t("peakHour")} ${String(peak.hour).padStart(2, "0")}:00 · ${escapeHtml(rhythm.label)}</span>
        </div>
        <div class="activity-meta">
          <span>${t("historicalSamples")} ${historySamples}</span>
          <span>${t("monitorSamples")} ${monitorSamples}</span>
          <span>${t("backfilledSamples")} ${backfillSamples}</span>
          <span>${t("lastRecord")} ${fmtTimeLocalized(history.last_sample_at)}</span>
        </div>
        <div class="hour-bars" aria-label="${escapeHtml(t("operatingRhythm"))}" title="${escapeHtml(t("hoverClickBar"))}">
          ${hourly.map(item => {
            const compareItem = compareByHour[item.hour] || null;
            const detail = hourlyOperatingTitle(item, rhythm, compareItem);
            const currentHeight = Math.max(8, item.count / maxHourly * 100);
            const compareHeight = compareItem ? Math.max(8, compareItem.count / maxHourly * 100) : 0;
            return `
              <button
                class="hour-bar-wrap ${item.hour === peak.hour ? "peak" : ""}"
                type="button"
                data-rhythm-hour="${item.hour}"
                data-rhythm-detail="${escapeHtml(detail)}"
                title="${escapeHtml(detail)}"
                aria-label="${escapeHtml(detail)}"
              >
                <span class="hour-bar current" style="height:${currentHeight}%"></span>
                ${compareItem ? `<span class="hour-bar compare" style="height:${compareHeight}%"></span>` : ""}
              </button>
            `;
          }).join("")}
        </div>
        <div class="activity-axis">
          <span>00</span><span>06</span><span>12</span><span>18</span><span>23</span>
        </div>
        <div id="activity-hour-detail" class="activity-hour-detail">
          ${hourlyOperatingDetail(peak, rhythm, compareByHour[peak.hour] || null)}
        </div>
        ${operatingRhythmComparison(history, rhythm)}
      </div>
      <div class="behavior-score-grid">
        ${behaviorMeter({
          label: t("activePressure"),
          value: `${activeSessions}`,
          sub: activeSeverity === "high" ? t("pressureHigh") : t("pressureNormal"),
          pct: activePressure,
          severity: activeSeverity,
        })}
        ${behaviorMeter({
          label: t("projectConcentration"),
          value: `${projectShare.toFixed(1)}%`,
          sub: t("largestProjectShare"),
          pct: projectShare,
          severity: projectSeverity,
        })}
        ${behaviorMeter({
          label: t("uploadShare"),
          value: `${uploadShare.toFixed(2)}%`,
          sub: t("representativeTrafficMix"),
          pct: uploadShare,
          severity: "normal",
        })}
        ${behaviorMeter({
          label: t("downloadShare"),
          value: `${downloadShare.toFixed(2)}%`,
          sub: t("representativeTrafficMix"),
          pct: downloadShare,
          severity: "normal",
        })}
        ${behaviorMeter({
          label: t("contextualShare"),
          value: `${contextualShare.toFixed(2)}%`,
          sub: t("representativeTrafficMix"),
          pct: contextualShare,
          severity: "normal",
        })}
        ${behaviorMeter({
          label: t("reasoningShare"),
          value: `${reasoningShare.toFixed(2)}%`,
          sub: t("representativeTrafficMix"),
          pct: reasoningShare,
          severity: "normal",
        })}
      </div>
    </div>
  `;
}

function behaviorMeter({label, value, sub, pct, severity}) {
  const cleanPct = Math.max(0, Math.min(100, Number(pct || 0)));
  return `
    <div class="behavior-meter ${escapeHtml(severity)}" title="${escapeHtml(`${label}: ${value}\n${sub}`)}">
      <div class="behavior-meter-head">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
      <div class="behavior-meter-bar">
        <span style="width:${cleanPct}%"></span>
      </div>
      <small>${escapeHtml(sub)}</small>
    </div>
  `;
}

function hourlyEventCounts(points) {
  const counts = Array.from({length: 24}, (_, hour) => ({hour, count: 0}));
  for (const point of points) {
    if (!point.timestamp) continue;
    const hour = new Date(point.timestamp).getHours();
    if (Number.isInteger(hour) && hour >= 0 && hour < 24) counts[hour].count += 1;
  }
  return counts;
}

function operatingPeriods(history, mode) {
  if (mode === "week") return history?.weekly || [];
  if (mode === "day") return history?.daily || [];
  return [];
}

function periodKey(period, mode) {
  if (!period) return "";
  return mode === "week" ? String(period.week_start || "") : String(period.date || "");
}

function periodLabel(period, mode) {
  if (!period) return t("allHistory");
  if (mode === "week") return `${period.week_start || "--"} - ${period.week_end || "--"}`;
  return String(period.date || "--");
}

function periodHourly(period, mode = operatingRhythmMode) {
  const rows = period?.hourly || [];
  const label = periodLabel(period, mode);
  return Array.from({length: 24}, (_, hour) => {
    const row = rows.find(item => Number(item.hour) === hour) || {};
    return {
      hour,
      label,
      count: Number(row.samples || 0),
      monitorSamples: Number(row.monitor_samples || 0),
      backfillSamples: Number(row.backfill_samples || 0),
      activeSamples: Number(row.active_samples || 0),
      source: "monitor_history_period",
    };
  });
}

function selectedOperatingRhythm(history, fallbackPoints) {
  const validModes = new Set(["day", "week", "all"]);
  if (!validModes.has(operatingRhythmMode)) operatingRhythmMode = "day";
  let mode = operatingRhythmMode;
  let periods = operatingPeriods(history, mode);
  if (mode !== "all" && !periods.length) {
    mode = "all";
    periods = [];
  }
  if (mode === "all") {
    return {
      mode,
      periods,
      index: -1,
      period: null,
      label: t("allHistory"),
      hourly: hourlyOperatingCounts(history, fallbackPoints),
    };
  }
  const maxIndex = Math.max(0, periods.length - 1);
  let index = operatingRhythmPinned[mode] ? operatingRhythmIndex[mode] : maxIndex;
  if (index === null || index === undefined || !Number.isFinite(Number(index))) index = maxIndex;
  index = Math.max(0, Math.min(maxIndex, Number(index)));
  operatingRhythmIndex[mode] = index;
  const period = periods[index] || null;
  return {
    mode,
    periods,
    index,
    period,
    label: periodLabel(period, mode),
    hourly: periodHourly(period, mode),
  };
}

function operatingRhythmControls(history, rhythm) {
  const periods = rhythm.periods || [];
  const canMove = rhythm.mode !== "all" && periods.length > 1;
  const periodText = rhythm.mode === "all"
    ? `${t("selectedPeriod")}: ${t("allHistory")}`
    : `${t("selectedPeriod")}: ${rhythm.label} (${rhythm.index + 1}/${periods.length})`;
  return `
    <div class="activity-controls">
      <div class="activity-button-row" title="${escapeHtml(tip("operatingRhythm"))}">
        ${["day", "week", "all"].map(mode => `
          <button class="activity-button ${rhythm.mode === mode ? "active" : ""}" type="button" data-rhythm-mode="${mode}">
            ${mode === "day" ? t("historyModeDay") : mode === "week" ? t("historyModeWeek") : t("historyModeAll")}
          </button>
        `).join("")}
        <button class="activity-button" type="button" data-rhythm-move="-1" ${canMove && rhythm.index > 0 ? "" : "disabled"}>${t("previousPeriod")}</button>
        <button class="activity-button" type="button" data-rhythm-move="1" ${canMove && rhythm.index < periods.length - 1 ? "" : "disabled"}>${t("nextPeriod")}</button>
        <button class="activity-button" type="button" data-rhythm-latest="${rhythm.mode}" ${canMove && rhythm.index < periods.length - 1 ? "" : "disabled"}>${t("latestPeriod")}</button>
      </div>
      ${rhythm.mode !== "all" && periods.length ? `
        <input class="activity-slider" type="range" min="0" max="${periods.length - 1}" step="1" value="${rhythm.index}" data-rhythm-range="${rhythm.mode}" aria-label="${escapeHtml(t("selectedPeriod"))}">
      ` : ""}
      <div class="activity-period-label">${escapeHtml(periodText)}</div>
    </div>
  `;
}

function defaultCompareIndex(mode, index, periods) {
  if (!periods.length || index <= 0) return -1;
  if (mode === "day" && index >= 7) return index - 7;
  return index - 1;
}

function selectedComparePeriod(mode, rhythm) {
  const periods = rhythm.mode === mode ? rhythm.periods : operatingPeriods(latestSnapshot?.monitor_history || {}, mode);
  if (!periods.length) return {periods, period: null, index: -1};
  const currentKey = rhythm.mode === mode ? periodKey(rhythm.period, mode) : periodKey(periods[periods.length - 1], mode);
  const defaultIndex = rhythm.mode === mode ? defaultCompareIndex(mode, rhythm.index, periods) : Math.max(0, periods.length - 2);
  const selectedKey = operatingRhythmCompare[mode];
  let index = selectedKey ? periods.findIndex(period => periodKey(period, mode) === selectedKey) : defaultIndex;
  if (index < 0 || periodKey(periods[index], mode) === currentKey) index = defaultIndex;
  if (index < 0 || periodKey(periods[index], mode) === currentKey) return {periods, period: null, index: -1};
  return {periods, period: periods[index], index};
}

function comparisonOptions(mode, periods, selectedPeriod, currentPeriod) {
  return periods.map(period => {
    const key = periodKey(period, mode);
    const selected = selectedPeriod && key === periodKey(selectedPeriod, mode);
    const disabled = currentPeriod && key === periodKey(currentPeriod, mode);
    return `<option value="${escapeHtml(key)}" ${selected ? "selected" : ""} ${disabled ? "disabled" : ""}>${escapeHtml(periodLabel(period, mode))}</option>`;
  }).join("");
}

function comparisonDelta(current, previous, key) {
  const currentValue = Number(current?.[key] || 0);
  const previousValue = Number(previous?.[key] || 0);
  return comparisonDeltaValue(currentValue, previousValue);
}

function comparisonDeltaValue(currentValue, previousValue) {
  currentValue = Number(currentValue || 0);
  previousValue = Number(previousValue || 0);
  return fmtDelta({
    current: currentValue,
    previous: previousValue,
    absolute: currentValue - previousValue,
    percent: previousValue === 0 ? (currentValue === 0 ? null : 100) : (currentValue - previousValue) * 100 / previousValue,
  }, comparisonFormat);
}

function activeSampleTotal(period, mode) {
  return periodHourly(period, mode).reduce((sum, item) => sum + Number(item.activeSamples || 0), 0);
}

function peakHourFromHourly(rows) {
  const clean = rows || [];
  if (!clean.length) return null;
  return clean.reduce((best, item) => Number(item.count || 0) > Number(best.count || 0) ? item : best, clean[0]);
}

function peakHourText(item) {
  if (!item) return "--";
  return `${String(item.hour).padStart(2, "0")}:00 (${fmtTokens(item.count)})`;
}

function comparisonCard(title, current, previous, mode) {
  if (!current || !previous) {
    return `
      <div class="activity-compare-card">
        <strong>${escapeHtml(title)}</strong>
        <span>${t("noComparisonPeriod")}</span>
      </div>
    `;
  }
  const currentActiveSamples = activeSampleTotal(current, mode);
  const previousActiveSamples = activeSampleTotal(previous, mode);
  const currentPeak = peakHourFromHourly(periodHourly(current, mode));
  const previousPeak = peakHourFromHourly(periodHourly(previous, mode));
  const tooltip = [
    `${title}`,
    `${t("selectedPeriod")}: ${periodLabel(current, mode)}`,
    `${t("compareWith")}: ${periodLabel(previous, mode)}`,
    `${t("historicalSamples")}: ${safe(current.samples, 0)} vs ${safe(previous.samples, 0)}`,
    `${t("monitorSamples")}: ${safe(current.monitor_samples, 0)} vs ${safe(previous.monitor_samples, 0)}`,
    `${t("backfilledSamples")}: ${safe(current.backfill_samples, 0)} vs ${safe(previous.backfill_samples, 0)}`,
    `${t("activeSamples")}: ${currentActiveSamples} vs ${previousActiveSamples}`,
    `${t("currentPeak")}: ${peakHourText(currentPeak)}`,
    `${t("baselinePeak")}: ${peakHourText(previousPeak)}`,
  ].join("\n");
  return `
    <div class="activity-compare-card" title="${escapeHtml(tooltip)}">
      <strong>${escapeHtml(title)}</strong>
      <span>${t("samplesDelta")}: ${comparisonDelta(current, previous, "samples")}</span>
      <span>${t("activeSamples")}: ${comparisonDeltaValue(currentActiveSamples, previousActiveSamples)}</span>
      <span>${t("monitorSamples")}: ${comparisonDelta(current, previous, "monitor_samples")}</span>
      <span>${t("backfilledSamples")}: ${comparisonDelta(current, previous, "backfill_samples")}</span>
      <span>${t("currentPeak")}: ${peakHourText(currentPeak)}</span>
      <span>${t("baselinePeak")}: ${peakHourText(previousPeak)}</span>
    </div>
  `;
}

function operatingRhythmComparison(history, rhythm) {
  const dayPeriods = history?.daily || [];
  const weekPeriods = history?.weekly || [];
  const currentDay = rhythm.mode === "day" ? rhythm.period : dayPeriods[dayPeriods.length - 1];
  const currentWeek = rhythm.mode === "week" ? rhythm.period : weekPeriods[weekPeriods.length - 1];
  const dayCompare = selectedComparePeriod("day", rhythm);
  const weekCompare = selectedComparePeriod("week", rhythm);
  return `
    <div class="activity-comparison">
      <div class="activity-button-row">
        <label>
          <span class="muted">${t("dailyComparison")}</span>
          <select class="activity-select" data-rhythm-compare="day" ${dayPeriods.length ? "" : "disabled"}>
            ${comparisonOptions("day", dayPeriods, dayCompare.period, currentDay)}
          </select>
        </label>
        <label>
          <span class="muted">${t("weeklyComparison")}</span>
          <select class="activity-select" data-rhythm-compare="week" ${weekPeriods.length ? "" : "disabled"}>
            ${comparisonOptions("week", weekPeriods, weekCompare.period, currentWeek)}
          </select>
        </label>
      </div>
      <div class="activity-compare-grid">
        ${comparisonCard(t("dailyComparison"), currentDay, dayCompare.period, "day")}
        ${comparisonCard(t("weeklyComparison"), currentWeek, weekCompare.period, "week")}
      </div>
    </div>
  `;
}

function hourlyOperatingCounts(history, fallbackPoints) {
  const rows = history?.hourly || [];
  if (rows.length) {
    return Array.from({length: 24}, (_, hour) => {
      const row = rows.find(item => Number(item.hour) === hour) || {};
      const count = Number(row.samples || 0);
      return {
        hour,
        count,
        monitorSamples: Number(row.monitor_samples || 0),
        backfillSamples: Number(row.backfill_samples || 0),
        activeSamples: Number(row.active_samples || 0),
        source: "monitor_history",
      };
    });
  }
  return hourlyEventCounts(fallbackPoints).map(item => ({
    ...item,
    monitorSamples: 0,
    backfillSamples: item.count,
    activeSamples: 0,
    source: "trend_points_fallback",
  }));
}

function hourlyOperatingTitle(item, rhythm = null, compareItem = null) {
  const lines = [
    `${String(item.hour).padStart(2, "0")}:00`,
    rhythm ? `${t("currentPeriod")}: ${rhythm.label}` : null,
    `${t("historicalSamples")}: ${item.count}`,
    `${t("monitorSamples")}: ${item.monitorSamples}`,
    `${t("backfilledSamples")}: ${item.backfillSamples}`,
    `${t("active")}: ${item.activeSamples}`,
  ].filter(Boolean);
  if (compareItem) {
    lines.push(
      "---",
      `${t("comparisonPeriod")}: ${String(compareItem.label || "")}`,
      `${t("historicalSamples")}: ${compareItem.count}`,
      `${t("monitorSamples")}: ${compareItem.monitorSamples}`,
      `${t("backfilledSamples")}: ${compareItem.backfillSamples}`,
      `${t("active")}: ${compareItem.activeSamples}`,
    );
  }
  return lines.join("\n");
}

function hourlyOperatingDetail(item, rhythm, compareItem = null) {
  const total = (rhythm.hourly || []).reduce((sum, row) => sum + Number(row.count || 0), 0);
  const share = total ? Number(item.count || 0) * 100 / total : 0;
  const compareBlock = compareItem ? `
    <div class="activity-hour-compare">
      <strong>${t("comparisonPeriod")}</strong>
      <span>${escapeHtml(String(compareItem.label || ""))}</span>
      <span>${t("historicalSamples")}: ${fmtTokens(compareItem.count)}</span>
      <span>${t("monitorSamples")}: ${fmtTokens(compareItem.monitorSamples)}</span>
      <span>${t("backfilledSamples")}: ${fmtTokens(compareItem.backfillSamples)} · ${t("active")}: ${fmtTokens(compareItem.activeSamples)}</span>
    </div>
  ` : "";
  return `
    <div class="activity-hour-current">
      <strong>${t("hourDetails")} · ${String(item.hour).padStart(2, "0")}:00</strong>
      <span>${t("currentPeriod")}: ${escapeHtml(rhythm.label)}</span>
      <span>${t("historicalSamples")}: ${fmtTokens(item.count)} · ${t("sampleShare")}: ${fmtPercent(share)}</span>
      <span>${t("monitorSamples")}: ${fmtTokens(item.monitorSamples)} · ${t("backfilledSamples")}: ${fmtTokens(item.backfillSamples)} · ${t("active")}: ${fmtTokens(item.activeSamples)}</span>
    </div>
    ${compareBlock}
  `;
}

function renderRecommendations(data) {
  const box = byId("recommendations");
  if (!box) return;
  const items = data.recommendations || [];
  box.innerHTML = items.length ? items.map(item => `
    <div class="insight ${escapeHtml(item.priority)}" title="${escapeHtml(`${translateRecommendationTitle(item.title)}\n${translateRecommendationDetail(item.title, item.detail)}`)}">
      <strong>${escapeHtml(translateRecommendationTitle(item.title))}</strong>
      <span>${escapeHtml(translateRecommendationDetail(item.title, item.detail))}</span>
    </div>
  `).join("") : `<div class="insight"><strong>${t("noRecommendations")}</strong><span>${t("usageStable")}</span></div>`;
}

function renderBurnRateWindows(data) {
  const box = byId("burn-rate-windows");
  if (!box) return;
  const windows = data.burn_rate_windows || [];
  if (!windows.length) {
    box.innerHTML = `<div class="insight"><strong>${t("noBurnWindowData")}</strong><span>${t("moreHistoryNeeded")}</span></div>`;
    return;
  }
  const rates = windows
    .map(item => Number(item.percent_per_hour))
    .filter(value => Number.isFinite(value) && value > 0);
  const maxRate = Math.max(...rates, 1);
  box.innerHTML = windows.map((item) => {
    const rate = Number(item.percent_per_hour);
    const hasRate = Number.isFinite(rate);
    const width = hasRate ? Math.max(2, Math.min(100, rate * 100 / maxRate)) : 0;
    const coverage = Number(item.coverage_percent || 0);
    const tone = hasRate && rate >= 30 ? "high" : hasRate && rate >= 15 ? "medium" : "normal";
    const label = burnWindowLabel(item);
    const title = [
      `${label}: ${hasRate ? fmtRate(rate) : "--"}`,
      `${t("burnWindowDelta")}: ${fmtPercentPoints(item.percent_delta)}`,
      `${t("burnWindowCoverage")}: ${fmtPercent(coverage)}`,
      `${t("burnWindowSamples")}: ${safe(item.sample_count, 0)}`,
    ].join("\n");
    return `
      <div class="burn-window-card ${tone}" title="${escapeHtml(title)}">
        <div class="burn-window-head">
          <strong>${escapeHtml(label)}</strong>
          <span>${hasRate ? fmtRate(rate) : "--"}</span>
        </div>
        <div class="burn-window-bar" aria-hidden="true"><span style="width: ${width}%"></span></div>
        <div class="burn-window-meta">
          <span>${t("burnWindowDelta")} ${fmtPercentPoints(item.percent_delta)}</span>
          <span>${t("burnWindowCoverage")} ${fmtPercent(coverage, 0)}</span>
          <span>${t("burnWindowSamples")} ${safe(item.sample_count, 0)}</span>
        </div>
      </div>
    `;
  }).join("");
}

function burnWindowLabel(item) {
  const key = String(item?.key || item?.label || "");
  if (currentLang !== "zh") return item?.label || key || "--";
  return {
    "1h": "1小时",
    "5h": "5小时",
    "10h": "10小时",
    "1d": "1天",
    "1w": "1周",
  }[key] || item?.label || key || "--";
}

function proAnalysisCard({title, value, tone = "normal", rows = []}) {
  return `
    <div class="pro-analysis-card ${escapeHtml(tone)}" title="${escapeHtml([title, value, ...rows.map(row => `${row.label}: ${row.value}`)].join("\n"))}">
      <strong>${escapeHtml(title)}</strong>
      <b>${escapeHtml(value)}</b>
      <div>
        ${rows.map(row => `<span><em>${escapeHtml(row.label)}</em><i>${escapeHtml(row.value)}</i></span>`).join("")}
      </div>
    </div>
  `;
}

function renderProAnalysis(data) {
  const box = byId("pro-analysis");
  if (!box) return;
  const latest = data.latest_event || {};
  const primary = latest.primary || {};
  const secondary = latest.secondary || {};
  const primaryLeft = primary.remaining_percent ?? remaining(primary.used_percent);
  const secondaryLeft = secondary.remaining_percent ?? remaining(secondary.used_percent);
  const totals = data.totals || {};
  const oneHourWindow = burnRateWindow(data, "1h") || {};
  const fiveHourWindow = burnRateWindow(data, "5h") || {};
  const history = data.monitor_history || {};
  const projects = data.top_projects || [];
  const totalProjectTokens = projects.reduce((sum, item) => sum + Number(item.latest_total_tokens_sum || 0), 0);
  const topProject = projects[0] || {};
  const topProjectShare = totalProjectTokens ? Number(topProject.latest_total_tokens_sum || 0) * 100 / totalProjectTokens : 0;
  const activeThreads = Number(totals.threads_working || 0);
  const activeProjects = Number(totals.projects_working || 0);
  const recommendationText = (data.recommendations || [])
    .slice(0, 2)
    .map(item => translateRecommendationTitle(item.title))
    .join(" / ") || t("usageStable");
  const quotaTone = primaryLeft !== null && primaryLeft < 10 ? "critical" : primaryLeft !== null && primaryLeft < 50 ? "warning" : "normal";
  const concentrationTone = topProjectShare >= 55 ? "warning" : "normal";
  box.innerHTML = [
    proAnalysisCard({
      title: t("proQuotaPosture"),
      value: `${fmtPercent(primaryLeft)} ${t("left")}`,
      tone: quotaTone,
      rows: [
        {label: t("secondaryTitle"), value: `${fmtPercent(secondaryLeft)} ${t("left")}`},
        {label: t("reset"), value: fmtTimeLocalized(primary.resets_at_iso)},
        {label: t("contextTitle"), value: fmtPercent(latest.context_used_percent)},
      ],
    }),
    proAnalysisCard({
      title: t("proBurnModel"),
      value: fmtRate(data.average_burn_rate_primary_percent_per_hour),
      tone: Number(data.average_burn_rate_primary_percent_per_hour || 0) >= 15 ? "warning" : "normal",
      rows: [
        {label: t("oneHourCreditEtaTitle"), value: fmtRate(oneHourWindow.percent_per_hour)},
        {label: "5h avg", value: fmtRate(fiveHourWindow.percent_per_hour)},
        {label: t("burnWindowSamples"), value: String(oneHourWindow.sample_count ?? "--")},
      ],
    }),
    proAnalysisCard({
      title: t("proWorkloadConcentration"),
      value: `${fmtPercent(topProjectShare)}`,
      tone: concentrationTone,
      rows: [
        {label: t("project"), value: displayProjectName(topProject)},
        {label: t("threadsWorking"), value: String(activeThreads)},
        {label: t("projectsWorking"), value: String(activeProjects)},
      ],
    }),
    proAnalysisCard({
      title: t("proHistoryDepth"),
      value: fmtTokens(history.sample_count || 0),
      rows: [
        {label: t("monitorSamples"), value: fmtTokens(history.persisted_sample_count || 0)},
        {label: t("backfilledSamples"), value: fmtTokens(history.backfill_sample_count || 0)},
        {label: t("historySince"), value: fmtTimeLocalized(history.first_sample_at)},
      ],
    }),
    proAnalysisCard({
      title: t("proActionFocus"),
      value: recommendationText,
      tone: (data.alerts || []).length ? "warning" : "normal",
      rows: [
        {label: t("alerts"), value: String((data.alerts || []).length)},
        {label: t("tokenEvents"), value: fmtTokens(totals.token_count_events || 0)},
        {label: t("latestEvent"), value: fmtTimeLocalized(latest.timestamp)},
      ],
    }),
  ].join("");
}

function renderSnapshot(data) {
  latestSnapshot = data;
  const latest = data.latest_event;
  if (!latest) {
    setText("updated", t("noData"));
    setText("data-read-at", `${t("dataRead")} --`);
    setText("latest-event-at", `${t("latestEvent")} --`);
    return;
  }
  const primary = latest.primary || {};
  const secondary = latest.secondary || {};
  const total = latest.total_usage || {};
  const primaryLeft = primary.remaining_percent ?? remaining(primary.used_percent);
  const secondaryLeft = secondary.remaining_percent ?? remaining(secondary.used_percent);
  const cache = data.dashboard_cache || {};
  const syncSuffix = cache.sync_in_progress ? ` · ${t("syncing")}` : "";
  const averageBurnRate = data.average_burn_rate_primary_percent_per_hour;
  const estimatedHoursLeft = estimatePrimaryTimeLeftHours(primaryLeft, averageBurnRate);
  const estimatedTimeText = estimatedHoursLeft === Infinity
    ? t("estimatedTimeStable")
    : estimatedHoursLeft === 0
      ? t("estimatedTimeNow")
    : estimatedHoursLeft === null
      ? "--"
      : fmtDurationHours(estimatedHoursLeft);
  const oneHourBurnWindow = burnRateWindow(data, "1h");
  const oneHourBurnRate = oneHourBurnWindow?.percent_per_hour;
  const oneHourEtaHours = estimatePrimaryTimeLeftHours(primaryLeft, oneHourBurnRate);
  const oneHourEtaText = oneHourEtaHours === Infinity
    ? t("estimatedTimeStable")
    : oneHourEtaHours === 0
      ? t("estimatedTimeNow")
      : oneHourEtaHours === null
        ? "--"
        : fmtDurationHours(oneHourEtaHours);
  const tokenSummary = tokenUsageSummary(data);

  setText("plan", `${t("plan")} ${latest.plan_type || "--"}`);
  setText("updated", `${t("rendered")} ${fmtTimeLocalized(data.generated_at)}${syncSuffix}`);
  setText("data-read-at", `${t("dataRead")} ${fmtTimeLocalized(cache.data_read_at || cache.cached_at || data.generated_at)}`);
  setText("latest-event-at", `${t("latestEvent")} ${fmtTimeLocalized(cache.latest_event_at || latest.timestamp)}`);
  setText("primary-value", `${fmtPercent(primaryLeft)} ${t("left")}`);
  setText("secondary-value", `${fmtPercent(secondaryLeft)} ${t("left")}`);
  setText("context-value", fmtPercent(latest.context_used_percent));
  setText("primary-reset", `${t("reset")} ${fmtTimeLocalized(primary.resets_at_iso)}`);
  setText("secondary-reset", `${t("reset")} ${fmtTimeLocalized(secondary.resets_at_iso)}`);
  setText("context-detail", `${t("lastLabel")} ${fmtTokens(latest.last_usage?.total_tokens || 0)} / ${t("window")} ${fmtTokens(latest.model_context_window || 0)}`);
  setText("estimated-time-left", estimatedTimeText);
  setText("estimated-time-detail", `${t("estimatedTimeFoot").replace("{minutes}", String(averageBurnMinutes()))}: ${fmtRate(averageBurnRate)}`);
  setText("one-hour-credit-eta", oneHourEtaText);
  setText(
    "one-hour-credit-eta-detail",
    `${t("oneHourCreditEtaFoot")}: ${fmtRate(oneHourBurnRate)} · ${t("burnWindowCoverage")} ${fmtPercent(oneHourBurnWindow?.coverage_percent, 0)}`
  );
  setText("average-burn-rate", fmtRate(averageBurnRate));
  setText("token-total-used", fmtTokens(tokenSummary.total));
  setText("token-day-used", fmtTokens(tokenSummary.pastDay));
  setText("token-day-used-detail", `${t("observedCoverage")} ${fmtPercent(tokenSummary.pastDayCoverage, 0)}`);
  setText("token-week-used", fmtTokens(tokenSummary.pastWeek));
  setText("token-week-used-detail", `${t("observedCoverage")} ${fmtPercent(tokenSummary.pastWeekCoverage, 0)} · ${t("dailyAvg")} ${fmtTokens(tokenSummary.dailyAvg)}`);
  setText("total-sessions", data.totals?.sessions || 0);
  setText("active-sessions", `${t("active")} ${data.totals?.active_sessions || 0}`);
  setText("threads-working", data.totals?.threads_working || 0);
  setText("threads-working-foot", `${fmtTokens(data.totals?.threads_activated || 0)} ${t("threads").toLowerCase()} / ${fmtTokens(data.totals?.threads_working || 0)} ${t("working").toLowerCase()}`);
  setText("agents-activated", data.totals?.agents_activated || 0);
  setText("agents-activated-foot", `${fmtTokens(data.totals?.agents_working || 0)} ${t("activeAgents")}`);
  setText("projects-working", data.totals?.projects_working || 0);
  setText("projects-working-foot", `${fmtTokens(data.totals?.projects_activated || 0)} ${t("project").toLowerCase()} / ${fmtTokens(data.totals?.projects_working || 0)} ${t("working").toLowerCase()}`);
  setText("event-count", fmtTokens(data.totals?.token_count_events || 0));
  setText("upload-sum", fmtTokens(data.totals?.latest_upload_tokens_sum || 0));
  setText("download-sum", fmtTokens(data.totals?.latest_output_tokens_sum || 0));
  setText("contextual-sum", fmtTokens(data.totals?.latest_contextual_tokens_sum || 0));
  setText("reasoning-sum", fmtTokens(data.totals?.latest_reasoning_tokens_sum || 0));
  setBar("primary-bar", primaryLeft, "remaining");
  setBar("secondary-bar", secondaryLeft, "remaining");
  setBar("context-bar", latest.context_used_percent);
  setCountdown("primary", primary);
  setCountdown("secondary", secondary);

  renderCharts(data);
  renderComparisons(data);
  renderPatterns(data);
  renderRecommendations(data);
  renderBurnRateWindows(data);
  renderProAnalysis(data);

  const projects = byId("projects");
  if (projects) projects.innerHTML = (data.top_projects || []).slice(0, 12).map(p => `
    <tr title="${escapeHtml(projectTooltip(p))}">
      <td data-label="${escapeHtml(t("project"))}" title="${escapeHtml(projectTooltip(p))}">
        <strong class="project-display-name">${escapeHtml(displayProjectName(p))}</strong>
        <small>${escapeHtml(displayNameSourceLabel(p.display_name_source))}</small>
      </td>
      <td data-label="${escapeHtml(t("threads"))}" title="${escapeHtml(tip("threads"))}">${safe(p.threads, p.sessions || 0)}</td>
      <td data-label="${escapeHtml(t("working"))}" title="${escapeHtml(tip("working"))}">${safe(p.working_threads, p.active_sessions || 0)}</td>
      <td data-label="${escapeHtml(t("agents"))}" title="${escapeHtml(tip("agents"))}">${safe(p.agents, p.sessions || 0)}</td>
      <td data-label="${escapeHtml(t("active"))}" title="${escapeHtml(tip("active"))}">${safe(p.working_agents, p.active_sessions || 0)}</td>
      <td data-label="${escapeHtml(t("tokenUsed"))}" title="${escapeHtml(tip("tokenUsed"))}">${fmtTokens(p.latest_total_tokens_sum)}</td>
      <td data-label="${escapeHtml(t("upload"))}" title="${escapeHtml(tip("upload"))}">${fmtTokens(p.latest_upload_tokens_sum)}</td>
      <td data-label="${escapeHtml(t("download"))}" title="${escapeHtml(tip("download"))}">${fmtTokens(p.latest_output_tokens_sum)}</td>
      <td data-label="${escapeHtml(t("contextual"))}" title="${escapeHtml(tip("contextual"))}">${fmtTokens(p.latest_contextual_tokens_sum)}</td>
      <td data-label="${escapeHtml(t("reason"))}" title="${escapeHtml(tip("reason"))}">${fmtTokens(p.latest_reasoning_tokens_sum)}</td>
      <td data-label="${escapeHtml(t("burnRate"))}" title="${escapeHtml(tip("burnRate"))}">${fmtTokenRate(p.token_burn_rate_per_hour)}</td>
      <td data-label="${escapeHtml(t("lastUpdate"))}" title="${escapeHtml(tip("lastUpdate"))}">${fmtTimeLocalized(p.last_update)}</td>
    </tr>
  `).join("");

  const daily = byId("daily");
  const visibleDailyRows = (data.daily || []).slice(-8).reverse();
  if (daily) daily.innerHTML = visibleDailyRows.map(row => `
    <tr title="${escapeHtml(`${row.date}\n${t("sessions")}: ${safe(row.sessions, 0)}\n${t("agents")}: ${safe(row.agents, row.sessions || 0)}\n${t("events")}: ${fmtTokens(row.events)}\n${t("tokenSum")}: ${fmtTokens(row.latest_total_tokens_sum)}`)}">
      <td data-label="${escapeHtml(t("date"))}">${escapeHtml(row.date)}</td>
      <td data-label="${escapeHtml(t("sessions"))}">${safe(row.sessions, 0)}</td>
      <td data-label="${escapeHtml(t("agents"))}">${safe(row.agents, row.sessions || 0)}</td>
      <td data-label="${escapeHtml(t("events"))}">${fmtTokens(row.events)}</td>
      <td data-label="${escapeHtml(t("tokenSum"))}">${fmtTokens(row.latest_total_tokens_sum)}</td>
    </tr>
  `).join("");
  const dailyTotal = byId("daily-total");
  if (dailyTotal) {
    const totals = visibleDailyRows.reduce((acc, row) => {
      acc.sessions += Number(row.sessions || 0);
      acc.agents += Number(row.agents ?? row.sessions ?? 0);
      acc.events += Number(row.events || 0);
      acc.tokens += Number(row.latest_total_tokens_sum || 0);
      return acc;
    }, {sessions: 0, agents: 0, events: 0, tokens: 0});
    dailyTotal.innerHTML = `
      <tr title="${escapeHtml(`${t("total")}\n${t("sessions")}: ${totals.sessions}\n${t("agents")}: ${totals.agents}\n${t("events")}: ${fmtTokens(totals.events)}\n${t("tokenSum")}: ${fmtTokens(totals.tokens)}`)}">
        <td data-label="${escapeHtml(t("date"))}">${t("total")}</td>
        <td data-label="${escapeHtml(t("sessions"))}">${fmtTokens(totals.sessions)}</td>
        <td data-label="${escapeHtml(t("agents"))}">${fmtTokens(totals.agents)}</td>
        <td data-label="${escapeHtml(t("events"))}">${fmtTokens(totals.events)}</td>
        <td data-label="${escapeHtml(t("tokenSum"))}">${fmtTokens(totals.tokens)}</td>
      </tr>
    `;
  }

  setText("session-count", `${(data.sessions || []).length} ${t("sessions").toLowerCase()}`);
  const sessions = byId("sessions");
  if (sessions) sessions.innerHTML = (data.sessions || []).slice(0, 10).map(s => `
    <tr title="${escapeHtml(sessionTooltip(s))}">
      <td data-label="${escapeHtml(t("status"))}"><span class="badge ${s.active ? "" : "idle"}" title="${escapeHtml(s.active ? t("activeLabel") : t("idleLabel"))}">${s.active ? t("activeLabel") : t("idleLabel")}</span></td>
      <td data-label="${escapeHtml(t("project"))}" title="${escapeHtml(s.cwd || "--")}">${escapeHtml((s.cwd || "--").split("/").slice(-2).join("/"))}</td>
      <td data-label="${escapeHtml(t("lastUpdate"))}" title="${escapeHtml(tip("lastUpdate"))}">${fmtTimeLocalized(s.last_update)}</td>
      <td data-label="${escapeHtml(t("tokens"))}" title="${escapeHtml(tip("tokens"))}">${fmtTokens(s.latest_total_tokens)}</td>
    </tr>
  `).join("");

  setText("alert-count", `${(data.alerts || []).length} ${t("alerts").toLowerCase()}`);
  const alerts = byId("alerts");
  if (alerts) alerts.innerHTML = (data.alerts || []).length ? data.alerts.map(a => `
    <div class="alert ${escapeHtml(a.severity)}" title="${escapeHtml(translateAlertMessage(a.message))}"><strong>${escapeHtml(currentLang === "zh" ? translateAlertSeverity(a.severity) : String(a.severity).toUpperCase())}</strong><br>${escapeHtml(translateAlertMessage(a.message))}</div>
  `).join("") : `<div class="alert"><strong>${t("ok")}</strong><br>${t("noThresholdAlerts")}</div>`;
}

function projectTooltip(project) {
  return [
    `${t("displayName")}: ${displayProjectName(project)}`,
    `${t("realPath")}: ${project.project || "--"}`,
    `${t("nameSource")}: ${displayNameSourceLabel(project.display_name_source)}`,
    `${t("syncedThreadNames")}: ${(project.thread_names || []).join(", ") || "--"}`,
    `${t("threads")}: ${safe(project.threads, project.sessions || 0)}`,
    `${t("working")}: ${safe(project.working_threads, project.active_sessions || 0)}`,
    `${t("agents")}: ${safe(project.agents, project.sessions || 0)}`,
    `${t("tokenUsed")}: ${fmtTokens(project.latest_total_tokens_sum)}`,
    `${t("upload")}: ${fmtTokens(project.latest_upload_tokens_sum)}`,
    `${t("download")}: ${fmtTokens(project.latest_output_tokens_sum)}`,
    `${t("contextual")}: ${fmtTokens(project.latest_contextual_tokens_sum)}`,
    `${t("reason")}: ${fmtTokens(project.latest_reasoning_tokens_sum)}`,
    `${t("burnRate")}: ${fmtTokenRate(project.token_burn_rate_per_hour)}`,
  ].join("\n");
}

function displayProjectName(project) {
  if (project.display_name && project.display_name_source !== "path") return project.display_name;
  return (project.project || "--").split("/").slice(-3).join("/");
}

function displayNameSourceLabel(source) {
  const labels = currentLang === "zh" ? {
    alias: "自定义 alias",
    thread_index: "聊天框同步",
    path: "真实路径",
  } : {
    alias: "Custom alias",
    thread_index: "Chat title sync",
    path: "Real path",
  };
  return labels[source] || labels.path;
}

function sessionTooltip(session) {
  return [
    `${t("status")}: ${session.active ? t("activeLabel") : t("idleLabel")}`,
    `${t("project")}: ${session.cwd || "--"}`,
    `${t("lastUpdate")}: ${fmtTimeLocalized(session.last_update)}`,
    `${t("tokens")}: ${fmtTokens(session.latest_total_tokens)}`,
    `${t("upload")}: ${fmtTokens(session.latest_upload_tokens)}`,
    `${t("download")}: ${fmtTokens(session.latest_output_tokens)}`,
    `${t("contextual")}: ${fmtTokens(session.latest_contextual_tokens)}`,
    `${t("reason")}: ${fmtTokens(session.latest_reasoning_tokens)}`,
  ].join("\n");
}

function translateAlertSeverity(severity) {
  return {
    notice: "注意",
    warning: "警告",
    critical: "严重",
  }[String(severity).toLowerCase()] || severity;
}

async function refresh(manual = false) {
  if (refreshInFlight) return;
  refreshInFlight = true;
  const button = byId("refresh-button");
  if (button) {
    button.disabled = true;
    button.textContent = manual ? t("refreshing") : t("refresh");
  }
  try {
    if (manual) setText("updated", t("refreshing"));
    const params = withAccessToken(new URLSearchParams({
      avg_minutes: String(averageBurnMinutes()),
      history_days: "3650",
      force: manual ? "1" : "0",
    }));
    const res = await fetch(`/api/snapshot?${params.toString()}`, {cache: "no-store"});
    if (!res.ok) throw new Error(`API ${res.status}`);
    const data = await res.json();
    renderSnapshot(data);
  } catch (error) {
    setText("updated", `${t("dashboardError")}: ${error.message}`);
    console.error(error);
  } finally {
    refreshInFlight = false;
    if (button) {
      button.disabled = false;
      button.textContent = t("refresh");
    }
  }
}

function msUntilNextWholeMinute() {
  const now = new Date();
  const elapsed = now.getSeconds() * 1000 + now.getMilliseconds();
  return Math.max(1000, REFRESH_INTERVAL_MS - elapsed);
}

function scheduleAlignedRefresh() {
  if (alignedRefreshTimer) clearTimeout(alignedRefreshTimer);
  alignedRefreshTimer = setTimeout(async () => {
    await refresh(false);
    scheduleAlignedRefresh();
  }, msUntilNextWholeMinute());
}

applyStaticTranslations();
setupComparisonFormatToggle();
setupChartTooltips();
applyInterfaceStyle();
refresh();
scheduleAlignedRefresh();
byId("refresh-button")?.addEventListener("click", () => refresh(true));
byId("lang-en")?.addEventListener("click", () => setLanguage("en"));
byId("lang-zh")?.addEventListener("click", () => setLanguage("zh"));
document.querySelectorAll(".interface-button").forEach((button) => {
  button.addEventListener("click", () => setInterfaceStyle(button.dataset.style || "business"));
});
byId("average-burn-minutes")?.addEventListener("change", () => refresh(false));
byId("average-burn-minutes")?.addEventListener("input", () => {
  clearTimeout(intervalRefreshTimer);
  intervalRefreshTimer = setTimeout(() => refresh(false), 450);
});
byId("token-trend-visible-toggle")?.addEventListener("change", (event) => {
  tokenTrendVisible = Boolean(event.target.checked);
  localStorage.setItem(TOKEN_TREND_VISIBLE_STORAGE_KEY, tokenTrendVisible ? "1" : "0");
  if (latestSnapshot) renderCharts(latestSnapshot);
});
document.addEventListener("click", (event) => {
  const downloadButton = event.target.closest("[data-chart-download]");
  if (downloadButton) {
    downloadCanvasPng(downloadButton.dataset.chartDownload);
    return;
  }
  if (event.target.closest("[data-chart-clear-focus]")) {
    clearPinnedChart();
    return;
  }
  const windowTrendButton = event.target.closest("[data-window-trend-mode]");
  if (windowTrendButton) {
    windowTrendMode = normalizeWindowTrendMode(windowTrendButton.dataset.windowTrendMode || "fiveHour");
    localStorage.setItem(WINDOW_TREND_MODE_STORAGE_KEY, windowTrendMode);
    if (latestSnapshot) renderCharts(latestSnapshot);
    return;
  }
  const tokenTrendButton = event.target.closest("[data-token-trend-mode]");
  if (tokenTrendButton) {
    tokenTrendMode = tokenTrendButton.dataset.tokenTrendMode || "recent";
    localStorage.setItem(TOKEN_TREND_MODE_STORAGE_KEY, tokenTrendMode);
    if (latestSnapshot) renderCharts(latestSnapshot);
    return;
  }
  const hourBar = event.target.closest("[data-rhythm-hour]");
  if (hourBar) {
    const detail = hourBar.dataset.rhythmDetail || "";
    const detailBox = byId("activity-hour-detail");
    if (detailBox) detailBox.innerHTML = `<pre>${escapeHtml(detail)}</pre>`;
    return;
  }
  const modeButton = event.target.closest("[data-rhythm-mode]");
  if (modeButton) {
    operatingRhythmMode = modeButton.dataset.rhythmMode || "day";
    localStorage.setItem(OPERATING_RHYTHM_MODE_STORAGE_KEY, operatingRhythmMode);
    if (operatingRhythmMode === "day" || operatingRhythmMode === "week") {
      operatingRhythmPinned[operatingRhythmMode] = false;
      operatingRhythmIndex[operatingRhythmMode] = null;
    }
    if (latestSnapshot) renderPatterns(latestSnapshot);
    return;
  }
  const latestButton = event.target.closest("[data-rhythm-latest]");
  if (latestButton) {
    const mode = latestButton.dataset.rhythmLatest || operatingRhythmMode;
    if (mode === "day" || mode === "week") {
      operatingRhythmPinned[mode] = false;
      operatingRhythmIndex[mode] = null;
      operatingRhythmMode = mode;
      localStorage.setItem(OPERATING_RHYTHM_MODE_STORAGE_KEY, operatingRhythmMode);
    }
    if (latestSnapshot) renderPatterns(latestSnapshot);
    return;
  }
  const moveButton = event.target.closest("[data-rhythm-move]");
  if (moveButton && latestSnapshot) {
    const direction = Number(moveButton.dataset.rhythmMove || 0);
    const history = latestSnapshot.monitor_history || {};
    const periods = operatingPeriods(history, operatingRhythmMode);
    if (periods.length) {
      const current = operatingRhythmIndex[operatingRhythmMode] ?? periods.length - 1;
      operatingRhythmIndex[operatingRhythmMode] = Math.max(0, Math.min(periods.length - 1, Number(current) + direction));
      operatingRhythmPinned[operatingRhythmMode] = true;
      renderPatterns(latestSnapshot);
    }
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") clearPinnedChart();
});
document.addEventListener("input", (event) => {
  const range = event.target.closest("[data-rhythm-range]");
  if (!range) return;
  const mode = range.dataset.rhythmRange || operatingRhythmMode;
  operatingRhythmIndex[mode] = Number(range.value || 0);
  operatingRhythmPinned[mode] = true;
  if (latestSnapshot) renderPatterns(latestSnapshot);
});
document.addEventListener("change", (event) => {
  const tokenLine = event.target.closest("[data-token-line]");
  if (tokenLine) {
    const kind = tokenLine.dataset.tokenLine;
    const checked = Boolean(tokenLine.checked);
    if (kind === "aggregate") tokenTrendLineSelection.aggregate = checked;
    else if (kind === "baseline") tokenTrendLineSelection.baseline = checked;
    else if (kind === "session") {
      const id = tokenLine.dataset.tokenLineId || "";
      if (id) tokenTrendLineSelection.sessions[id] = checked;
    }
    saveTokenTrendLineSelection();
    if (latestSnapshot) renderCharts(latestSnapshot);
    return;
  }
  const trendEnd = event.target.closest("[data-window-trend-end]");
  if (trendEnd) {
    const mode = normalizeWindowTrendMode(trendEnd.dataset.windowTrendEnd || windowTrendMode);
    if (fixedWindowHoursForMode(mode)) {
      windowTrendRangeEnd[mode] = trendEnd.value;
      saveWindowTrendRangeEnd();
      windowTrendMode = mode;
      localStorage.setItem(WINDOW_TREND_MODE_STORAGE_KEY, windowTrendMode);
    }
    if (latestSnapshot) renderCharts(latestSnapshot);
    return;
  }
  const trendPeriod = event.target.closest("[data-window-trend-period]");
  if (trendPeriod) {
    const mode = normalizeWindowTrendMode(trendPeriod.dataset.windowTrendPeriod);
    if (mode) {
      windowTrendPeriod[mode] = trendPeriod.value;
      windowTrendMode = mode;
      localStorage.setItem(WINDOW_TREND_MODE_STORAGE_KEY, windowTrendMode);
    }
    if (latestSnapshot) renderCharts(latestSnapshot);
    return;
  }
  const trendCompare = event.target.closest("[data-window-trend-compare]");
  if (trendCompare) {
    const mode = normalizeWindowTrendMode(trendCompare.dataset.windowTrendCompare);
    if (mode) {
      windowTrendCompareMode[mode] = trendCompare.value;
      windowTrendMode = mode;
      localStorage.setItem(WINDOW_TREND_MODE_STORAGE_KEY, windowTrendMode);
    }
    if (latestSnapshot) renderCharts(latestSnapshot);
    return;
  }
  const tokenPeriod = event.target.closest("[data-token-trend-period]");
  if (tokenPeriod) {
    const mode = tokenPeriod.dataset.tokenTrendPeriod;
    if (mode) {
      tokenTrendPeriod[mode] = tokenPeriod.value;
      tokenTrendMode = mode;
      localStorage.setItem(TOKEN_TREND_MODE_STORAGE_KEY, tokenTrendMode);
    }
    if (latestSnapshot) renderCharts(latestSnapshot);
    return;
  }
  const tokenCompare = event.target.closest("[data-token-trend-compare]");
  if (tokenCompare) {
    const mode = tokenCompare.dataset.tokenTrendCompare;
    if (mode) {
      tokenTrendCompareMode[mode] = tokenCompare.value;
      tokenTrendMode = mode;
      localStorage.setItem(TOKEN_TREND_MODE_STORAGE_KEY, tokenTrendMode);
    }
    if (latestSnapshot) renderCharts(latestSnapshot);
    return;
  }
  const compare = event.target.closest("[data-rhythm-compare]");
  if (!compare) return;
  const mode = compare.dataset.rhythmCompare;
  if (mode) {
    operatingRhythmCompare[mode] = compare.value;
  }
  if (latestSnapshot) renderPatterns(latestSnapshot);
});
document.addEventListener("pointermove", (event) => {
  const hourBar = event.target.closest("[data-rhythm-hour]");
  if (!hourBar) return;
  const detail = hourBar.dataset.rhythmDetail || "";
  const tooltip = ensureChartTooltip();
  tooltip.textContent = detail;
  tooltip.hidden = false;
  tooltip.style.left = `${Math.min(window.innerWidth - 260, event.clientX + 14)}px`;
  tooltip.style.top = `${Math.max(8, event.clientY + 14)}px`;
});
document.addEventListener("pointerout", (event) => {
  const hourBar = event.target.closest("[data-rhythm-hour]");
  if (!hourBar) return;
  const related = event.relatedTarget;
  if (related && hourBar.contains(related)) return;
  ensureChartTooltip().hidden = true;
});

if ("ResizeObserver" in window) {
  const observer = new ResizeObserver(() => renderCharts(latestSnapshot));
  document.querySelectorAll(".chart-canvas").forEach(canvas => observer.observe(canvas));
} else {
  window.addEventListener("resize", () => renderCharts(latestSnapshot));
}
