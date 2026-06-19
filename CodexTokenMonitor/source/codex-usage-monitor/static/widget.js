const wp = (value) => value === null || value === undefined ? "--" : `${Number(value).toFixed(1)}%`;
const wt = (value) => {
  value = Number(value || 0);
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(value);
};
async function refreshWidget() {
  try {
    const params = new URLSearchParams({include_history: "0", force: "0"});
    const token = new URLSearchParams(window.location.search).get("token");
    if (token) params.set("token", token);
    const res = await fetch(`/api/snapshot?${params.toString()}`, {cache: "no-store"});
    if (!res.ok) throw new Error(`API ${res.status}`);
    const data = await res.json();
    const latest = data.latest_event;
    if (!latest) throw new Error("No data");
    const primary = latest.primary.used_percent || 0;
    document.getElementById("w-primary").textContent = `${wp(primary)} used`;
    document.getElementById("w-bar").style.width = `${Math.max(0, Math.min(100, primary))}%`;
    document.getElementById("w-weekly").textContent = `Weekly ${wp(latest.secondary.used_percent)}`;
    document.getElementById("w-reset").textContent = latest.primary.resets_at_iso ? new Date(latest.primary.resets_at_iso).toLocaleTimeString() : "Reset --";
    document.getElementById("w-tokens").textContent = `${wt(latest.total_usage.total_tokens)} tokens`;
    document.getElementById("w-status").textContent = data.alerts.length ? `${data.alerts.length} alert` : "OK";
  } catch (error) {
    document.getElementById("w-status").textContent = "Offline";
  }
}
refreshWidget();
setInterval(refreshWidget, 60000);
