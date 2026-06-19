import Cocoa
import Foundation

let projectDir = "/Users/linzezhang/Documents/Codex/2026-06-02/new-chat/outputs/codex-usage-monitor"

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private let menu = NSMenu()
    private let primaryItem = NSMenuItem(title: "5h window: --", action: nil, keyEquivalent: "")
    private let weeklyItem = NSMenuItem(title: "Weekly: --", action: nil, keyEquivalent: "")
    private let tokensItem = NSMenuItem(title: "Tokens: --", action: nil, keyEquivalent: "")
    private let alertItem = NSMenuItem(title: "Alerts: --", action: nil, keyEquivalent: "")
    private let updatedItem = NSMenuItem(title: "Updated: --", action: nil, keyEquivalent: "")
    private var timer: Timer?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.title = "Codex --"

        menu.addItem(primaryItem)
        menu.addItem(weeklyItem)
        menu.addItem(tokensItem)
        menu.addItem(alertItem)
        menu.addItem(updatedItem)
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Open Dashboard", action: #selector(openDashboard), keyEquivalent: "d"))
        menu.addItem(NSMenuItem(title: "Refresh", action: #selector(refreshNow), keyEquivalent: "r"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q"))
        statusItem.menu = menu

        refreshNow()
        timer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] _ in
            self?.refreshNow()
        }
    }

    @objc private func openDashboard() {
        if let url = URL(string: "http://127.0.0.1:8766/") {
            NSWorkspace.shared.open(url)
        }
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }

    @objc private func refreshNow() {
        DispatchQueue.global(qos: .utility).async {
            let result = self.loadSnapshot()
            DispatchQueue.main.async {
                self.render(result)
            }
        }
    }

    private func loadSnapshot() -> [String: Any]? {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/bash")
        process.arguments = ["-lc", "cd \"\(projectDir)\" && ./codex-usage json"]
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = Pipe()
        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            return nil
        }
        guard process.terminationStatus == 0 else {
            return nil
        }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    }

    private func render(_ snapshot: [String: Any]?) {
        guard
            let snapshot,
            let latest = snapshot["latest_event"] as? [String: Any],
            let primary = latest["primary"] as? [String: Any],
            let secondary = latest["secondary"] as? [String: Any],
            let total = latest["total_usage"] as? [String: Any]
        else {
            statusItem.button?.title = "Codex --"
            primaryItem.title = "No data"
            return
        }

        let primaryPercent = number(primary["used_percent"])
        let weeklyPercent = number(secondary["used_percent"])
        let totalTokens = intValue(total["total_tokens"])
        let outputTokens = intValue(total["output_tokens"])
        let reasoningTokens = intValue(total["reasoning_output_tokens"])
        let alerts = snapshot["alerts"] as? [[String: Any]] ?? []

        statusItem.button?.title = "Codex \(pct(primaryPercent))" + (alerts.isEmpty ? "" : " !")
        primaryItem.title = "5h window: \(pct(primaryPercent)) used"
        weeklyItem.title = "Weekly: \(pct(weeklyPercent)) used"
        tokensItem.title = "Tokens: \(tokens(totalTokens)) | output \(tokens(outputTokens)) | reasoning \(tokens(reasoningTokens))"
        alertItem.title = alerts.isEmpty ? "Alerts: none" : "Alerts: \(alerts.count)"
        updatedItem.title = "Updated: \(shortTime(Date()))"
    }

    private func number(_ value: Any?) -> Double? {
        if let value = value as? Double { return value }
        if let value = value as? Int { return Double(value) }
        if let value = value as? String { return Double(value) }
        return nil
    }

    private func intValue(_ value: Any?) -> Int {
        if let value = value as? Int { return value }
        if let value = value as? Double { return Int(value) }
        if let value = value as? String { return Int(value) ?? 0 }
        return 0
    }

    private func pct(_ value: Double?) -> String {
        guard let value else { return "--" }
        return "\(Int(round(value)))%"
    }

    private func tokens(_ value: Int) -> String {
        if value >= 1_000_000 {
            return String(format: "%.1fM", Double(value) / 1_000_000)
        }
        if value >= 1_000 {
            return String(format: "%.0fk", Double(value) / 1_000)
        }
        return "\(value)"
    }

    private func shortTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .medium
        formatter.dateStyle = .none
        return formatter.string(from: date)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
