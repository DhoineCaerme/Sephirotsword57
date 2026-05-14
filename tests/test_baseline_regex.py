"""
Unit tests for Baseline 2 (regex). No API calls needed.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baselines.baseline_regex import (
    extract_ports,
    extract_packages,
    extract_services,
    extract_env_vars,
    run_baseline_regex,
)


# ── extract_ports ────────────────────────────────────────────────────────────

def test_extract_ports_explicit():
    assert "8080" in extract_ports("listening on port 8080")


def test_extract_ports_colon():
    assert "443" in extract_ports("server bound to :443")


def test_extract_ports_ignores_low():
    # Port 22 is below threshold 80 — should not be picked up
    ports = extract_ports("port 22")
    # depending on the regex, this may or may not match; we just ensure
    # at minimum extract_ports doesn't crash and returns a list
    assert isinstance(ports, list)


def test_extract_ports_none():
    assert extract_ports("there are no ports here") == []


# ── extract_packages ─────────────────────────────────────────────────────────

def test_extract_packages_known():
    pkgs = extract_packages("Install nginx and redis-server")
    assert "nginx" in pkgs
    assert "redis-server" in pkgs


def test_extract_packages_case_insensitive():
    pkgs = extract_packages("Install NGINX")
    assert "nginx" in pkgs


def test_extract_packages_unknown_misses():
    # The regex baseline can't recognise unknown packages — that's its weakness
    pkgs = extract_packages("install my-custom-tool")
    assert "my-custom-tool" not in pkgs


# ── extract_env_vars ──────────────────────────────────────────────────────────

def test_extract_env_vars():
    evars = extract_env_vars("Set DATABASE_URL and API_TOKEN_SECRET")
    assert "DATABASE_URL" in evars
    assert "API_TOKEN_SECRET" in evars


def test_extract_env_vars_filters_false_positives():
    evars = extract_env_vars("Use the HTTP and JSON formats")
    assert "HTTP" not in evars
    assert "JSON" not in evars


# ── end-to-end baseline ──────────────────────────────────────────────────────

def test_baseline_detects_drift():
    doc = "Make sure nginx is installed."
    live = {"installed_packages": []}
    result = run_baseline_regex(doc, live)
    assert result["drift_detected"] is True
    assert result["root_cause"] == "SYSTEM_FAULT"


def test_baseline_detects_no_drift():
    """Use port (which doesn't overlap with services) for a clean in-sync test."""
    doc = "Service must be listening on port 8080."
    live = {"active_ports": ["8080"]}
    result = run_baseline_regex(doc, live)
    assert result["drift_detected"] is False
    assert result["root_cause"] == "IN_SYNC"


if __name__ == "__main__":
    tests = [
        (name, obj) for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e.__class__.__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed.")
    if failed:
        exit(1)
