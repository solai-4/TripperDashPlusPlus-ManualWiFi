//
//  ConnectBikeIntent.swift
//  TripperDashPP
//
//  Shortcuts action for connecting to the currently selected (default) bike.
//

import AppIntents
import Foundation

enum ShortcutConnectOutcome: Equatable, Sendable {
    case started(bikeName: String)
    case alreadyConnected(bikeName: String?)
    case inProgress
    case noBikeSaved
    case appNotReady

    var message: String {
        switch self {
        case .started(let name):
            return "Connecting to \(name)."
        case .alreadyConnected(let name):
            return name.map { "Already connected to \($0)." } ?? "Already connected."
        case .inProgress:
            return "Already connecting to your bike."
        case .noBikeSaved:
            return "No bike saved yet. Add one in TripperDash++ Test first."
        case .appNotReady:
            return "TripperDash++ Test wasn't ready. Open the app and try again."
        }
    }
}

/// Bridges an App Intent invocation to the live AppStatus created by SwiftUI.
/// Intent execution can begin during a cold launch, before the scene's .task.
@MainActor
final class ShortcutBridge {
    static let shared = ShortcutBridge()
    private init() {}

    private weak var status: AppStatus?

    func register(_ status: AppStatus) {
        self.status = status
    }

    func connectDefaultBike() async -> ShortcutConnectOutcome {
        var waited = 0.0
        while status == nil && waited < 8.0 {
            try? await Task.sleep(for: .milliseconds(100))
            waited += 0.1
        }
        guard let status else { return .appNotReady }

        // SavedBikesStore.selected is the persistent bike selected in the app;
        // it is also the bike targeted by the app's normal Connect action.
        let bike = status.savedBikes.selected

        // Demo mode has no physical vehicle to select.
        if status.bikeLink.demoMode {
            switch status.connectionState {
            case .connected, .streaming:
                return .alreadyConnected(bikeName: nil)
            default:
                status.bikeLink.connect()
                return .started(bikeName: "demo bike")
            }
        }

        guard let bike else { return .noBikeSaved }

        switch status.connectionState {
        case .connected, .streaming:
            return .alreadyConnected(bikeName: bike.displayName)
        case .wifiJoining, .handshaking:
            return .inProgress
        case .disconnected, .reconnecting, .error:
            // Reuse AppStatus's established manual-Wi-Fi connection path.
            // The phone must already be joined to the vehicle's Wi-Fi.
            status.connect(to: bike)
            return .started(bikeName: bike.displayName)
        }
    }
}

struct ConnectDefaultBikeIntent: AppIntent {
    static let title: LocalizedStringResource = "Connect to default bike"
    static let description = IntentDescription(
        "Opens TripperDash++ Test and connects to the bike currently selected in the app."
    )

    // Supported by the project's Xcode 16.4 / iOS 18.6 build SDK.
    static let openAppWhenRun: Bool = true

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let outcome = await ShortcutBridge.shared.connectDefaultBike()
        return .result(dialog: IntentDialog(stringLiteral: outcome.message))
    }
}

/// Makes the action available in Shortcuts and to Siri without manual setup.
struct TripperDashShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: ConnectDefaultBikeIntent(),
            phrases: [
                "Connect \(.applicationName) to my bike",
                "Connect my bike with \(.applicationName)"
            ],
            shortTitle: "Connect default bike",
            systemImageName: "bolt.horizontal.circle"
        )
    }
}
