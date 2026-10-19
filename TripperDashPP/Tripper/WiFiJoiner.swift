//
// WiFiJoiner.swift
// Manual-Wi-Fi test build.
//
// The app intentionally does not request or apply NEHotspotConfiguration.
// Join the Guerrilla 450 Tripper Wi-Fi in iOS Settings before tapping Connect.
//

import Foundation

enum WiFiJoinOutcome: Sendable, Equatable {
    case alreadyJoined
    case joined
    case failed(String)
}

@MainActor
final class WiFiJoiner {
    static let tripperPassphrase = "12345678"

    func register(ssid: String) async -> WiFiJoinOutcome {
        .failed("Join the bike Wi-Fi manually in Settings → Wi-Fi, then retry.")
    }

    func ensureJoined(ssid: String) async -> WiFiJoinOutcome {
        .failed("Join the bike Wi-Fi manually in Settings → Wi-Fi, then retry.")
    }

    func currentSSID() async -> String? {
        nil
    }

    func unregister(ssid: String) {
        // No Wi-Fi configuration was created by this app.
    }
}
