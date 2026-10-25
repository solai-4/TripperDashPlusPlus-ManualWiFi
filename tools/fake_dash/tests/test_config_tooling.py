"""Guards for repo tooling/config bugs that Linux CI can catch without Xcode."""

from __future__ import annotations

import importlib.util
import plistlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def _gpx_tool():
    spec = importlib.util.spec_from_file_location(
        "gpx_to_xcode_sim", REPO / "tools" / "gpx_to_xcode_sim.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_manual_wifi_build_does_not_require_wifi_entitlements():
    """Manual-Wi-Fi builds deliberately avoid paid hotspot entitlements."""
    with (REPO / "TripperDashPP" / "TripperDashPP.entitlements").open("rb") as f:
        ent = plistlib.load(f)
    assert "com.apple.developer.networking.wifi-info" not in ent
    assert "com.apple.developer.networking.HotspotConfiguration" not in ent


def test_manual_wifi_joiner_prompts_for_settings_join():
    """Manual-Wi-Fi build directs the rider to join from iOS Settings."""
    from tests.swift_source import strip_comments

    src = strip_comments(
        (REPO / "TripperDashPP" / "Tripper" / "WiFiJoiner.swift").read_text()
    )
    prompt = "Join the bike Wi-Fi manually in Settings → Wi-Fi, then retry."
    assert src.count(prompt) >= 2
    assert "func currentSSID() async -> String?" in src


def test_manual_wifi_connect_bypasses_in_app_join():
    """Connecting uses the already-joined Wi-Fi; no in-app join task is required."""
    from tests.swift_source import strip_comments

    src = strip_comments(
        (REPO / "TripperDashPP" / "App" / "AppStatus.swift").read_text()
    )
    start = src.index("func connect(to bike: SavedBike)")
    end = src.index("func addBike(name:", start)
    body = src[start:end]
    assert "bikeLink.connect()" in body
    assert "wifiJoiner.ensureJoined" not in body
    assert "joinTask = Task {" not in body



def test_connect_default_bike_shortcut_is_wired():
    """The App Intent must use the app's selected bike and existing connect path."""
    from tests.swift_source import strip_comments

    app_dir = REPO / "TripperDashPP" / "App"
    intent = strip_comments((app_dir / "ConnectBikeIntent.swift").read_text())
    app_entry = strip_comments((app_dir / "TripperDashPPApp.swift").read_text())
    settings = strip_comments((REPO / "TripperDashPP" / "UI" / "StreamingView.swift").read_text())
    project = (REPO / "TripperDashPP" / "TripperDashPP.xcodeproj" / "project.pbxproj").read_text()

    assert "struct ConnectDefaultBikeIntent: AppIntent" in intent
    assert "struct TripperDashShortcuts: AppShortcutsProvider" in intent
    assert "static let openAppWhenRun: Bool = true" in intent
    assert "status.savedBikes.selected" in intent
    assert "status.connect(to: bike)" in intent
    assert "ShortcutBridge.shared.register(status)" in app_entry
    assert "TripperDashShortcuts.updateAppShortcutParameters()" in app_entry
    assert "status.savedBikes.selectedID == bike.id" in settings
    assert "status.savedBikes.select(id: bike.id)" in settings
    assert "Set as default vehicle" in settings
    assert "ConnectBikeIntent.swift in Sources" in project
    assert project.count("ConnectBikeIntent.swift") >= 4


def test_gpx_poi_waypoints_are_not_spliced_into_track(tmp_path):
    gpx = tmp_path / "in.gpx"
    gpx.write_text(
        '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
        '<wpt lat="50.0" lon="15.0"><name>Fuel</name></wpt>'
        '<trk><trkseg><trkpt lat="49.0" lon="14.0"/><trkpt lat="49.001" lon="14.0"/>'
        "</trkseg></trk></gpx>"
    )
    assert _gpx_tool().read_points(gpx) == [(49.0, 14.0), (49.001, 14.0)]


def test_gpx_wpt_only_file_still_works(tmp_path):
    gpx = tmp_path / "in.gpx"
    gpx.write_text('<gpx><wpt lat="1" lon="2"/><wpt lat="1.001" lon="2"/></gpx>')
    assert _gpx_tool().read_points(gpx) == [(1.0, 2.0), (1.001, 2.0)]


def test_gpx_stamps_strictly_increase_and_keep_average_speed():
    """Xcode rejects equal/decreasing <time>; rounding per-gap (the old code)
    also drifted the overall speed."""
    import re
    from datetime import datetime, timezone

    m = _gpx_tool()
    # 3 m gaps at 50 km/h = 0.216 s each: many points fall in one second.
    pts = [(49.0 + i * 3 / 111_195, 14.0) for i in range(2000)]
    out = m.build(pts, 50.0, datetime(2026, 1, 1, tzinfo=timezone.utc))
    secs = [int(s[-2:]) + 60 * int(s[-5:-3]) + 3600 * int(s[-8:-6])
            for s in re.findall(r"<time>[^<]*?(\d\d:\d\d:\d\d)Z</time>", out)]
    assert all(b > a for a, b in zip(secs, secs[1:]))
    total_m = m.haversine(pts[0], pts[-1])
    assert abs(secs[-1] - secs[0] - total_m / (50 / 3.6)) <= 1


@pytest.mark.parametrize("kmh", ["0", "-5"])
def test_gpx_rejects_non_positive_speed(tmp_path, kmh):
    with pytest.raises(SystemExit):
        _gpx_tool().main([str(tmp_path / "a.gpx"), str(tmp_path / "b.gpx"), "--kmh", kmh])


def test_bare_cli_defaults_to_server(monkeypatch):
    """`fake-dash` with no subcommand used to crash with AttributeError
    (server options never parsed)."""
    from fake_dash import __main__ as cli

    seen = {}
    monkeypatch.setattr(cli, "_run_server", lambda args: seen.setdefault("a", args) and 0)
    cli.main([])
    assert seen["a"].command == "server"
    assert seen["a"].log_level
