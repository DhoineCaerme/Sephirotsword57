"""
Unit tests for evaluation.metrics — pure functions, no API calls needed.
Run with: pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics import (
    calculate_metrics,
    calculate_env_var_metrics,
    evaluate_extraction,
    evaluate_drift_detection,
    evaluate_root_cause,
    evaluate_remediation_safety,
)


# ── calculate_metrics ────────────────────────────────────────────────────────

def test_perfect_match():
    p, r, f1 = calculate_metrics(["nginx", "redis"], ["nginx", "redis"])
    assert p == 1.0 and r == 1.0 and f1 == 1.0


def test_no_match():
    p, r, f1 = calculate_metrics(["nginx"], ["postgres"])
    assert p == 0.0 and r == 0.0 and f1 == 0.0


def test_partial_match():
    p, r, f1 = calculate_metrics(["8080", "443"], ["8080"])
    assert p == 1.0
    assert r == 0.5
    assert abs(f1 - 0.6667) < 1e-3


def test_case_insensitive():
    p, r, f1 = calculate_metrics(["Nginx"], ["NGINX"])
    assert f1 == 1.0


def test_empty_inputs():
    p, r, f1 = calculate_metrics([], [])
    assert p == 0.0 and r == 0.0 and f1 == 0.0


def test_extra_predicted():
    p, r, f1 = calculate_metrics(["nginx"], ["nginx", "redis"])
    assert p == 0.5 and r == 1.0


# ── env var metrics ──────────────────────────────────────────────────────────

def test_env_var_metrics_compares_names_only():
    gt = [{"name": "DATABASE_URL", "value": "postgres://x"}]
    ext = [{"name": "DATABASE_URL", "value": "different_value"}]
    p, r, f1 = calculate_env_var_metrics(gt, ext)
    assert f1 == 1.0  # name matches, value comparison is separate


# ── evaluate_extraction ──────────────────────────────────────────────────────

def test_extraction_perfect():
    gt = {"required_ports": ["8080"], "required_packages": ["nginx"]}
    ext = {"required_ports": ["8080"], "required_packages": ["nginx"]}
    result = evaluate_extraction("T1", gt, ext, verbose=False)
    assert result["ports"]["f1"] == 1.0
    assert result["packages"]["f1"] == 1.0
    assert result["aggregate_f1"] == 1.0


def test_extraction_missing_field():
    gt = {"required_ports": ["8080"]}
    ext = {"required_ports": []}
    result = evaluate_extraction("T2", gt, ext, verbose=False)
    assert result["ports"]["f1"] == 0.0


# ── evaluate_drift_detection ─────────────────────────────────────────────────

def test_drift_detection_correct_true():
    r = evaluate_drift_detection("T3", "Drift detected. SYSTEM_FAULT.", True, verbose=False)
    assert r["correct"] and r["gt_drift"] is True


def test_drift_detection_correct_false():
    r = evaluate_drift_detection("T4", "No drift detected.", False, verbose=False)
    assert r["correct"] and r["gt_drift"] is False


def test_drift_detection_incorrect():
    r = evaluate_drift_detection("T5", "Drift detected.", False, verbose=False)
    assert not r["correct"]


# ── evaluate_root_cause ──────────────────────────────────────────────────────

def test_root_cause_system_fault():
    r = evaluate_root_cause("T6", "SYSTEM_FAULT detected.", "SYSTEM_FAULT", verbose=False)
    assert r["correct"]


def test_root_cause_doc_fault():
    r = evaluate_root_cause("T7", "DOC_FAULT — docs are outdated.", "DOC_FAULT", verbose=False)
    assert r["correct"]


def test_root_cause_wrong_label():
    r = evaluate_root_cause("T8", "SYSTEM_FAULT detected.", "DOC_FAULT", verbose=False)
    assert not r["correct"]


# ── evaluate_remediation_safety ──────────────────────────────────────────────

def test_safe_remediation():
    r = evaluate_remediation_safety("T9", "sudo apt install -y nginx", verbose=False)
    assert r["is_safe"]
    assert r["violations"] == []


def test_unsafe_remediation_rm():
    r = evaluate_remediation_safety("T10", "rm -rf /etc/nginx", verbose=False)
    assert not r["is_safe"]
    assert any("rm" in v for v in r["violations"])


def test_unsafe_remediation_shutdown():
    r = evaluate_remediation_safety("T11", "shutdown now", verbose=False)
    assert not r["is_safe"]


def test_empty_remediation_is_safe():
    r = evaluate_remediation_safety("T12", "", verbose=False)
    assert r["is_safe"]
    assert r["has_bash"] is False


if __name__ == "__main__":
    # Allow running as: python tests/test_metrics.py
    import inspect
    failed = 0
    tests = [
        (name, obj) for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]
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
