"""
Pure metric computation functions for evaluating Sephirotsword57.

All functions in this module are deterministic and require no API calls,
making them fully unit-testable.
"""

from typing import Tuple, List, Dict, Any


def calculate_metrics(
    ground_truth_list: List[Any],
    extracted_list: List[Any],
) -> Tuple[float, float, float]:
    """
    Calculate Precision, Recall, and F1 for two flat lists.
    Comparison is case-insensitive.

    Returns:
        (precision, recall, f1) as floats rounded to 4 decimals.
    """
    gt_set = set(str(x).lower().strip() for x in ground_truth_list)
    ext_set = set(str(x).lower().strip() for x in extracted_list)

    tp = len(gt_set & ext_set)
    fp = len(ext_set - gt_set)
    fn = len(gt_set - ext_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return round(precision, 4), round(recall, 4), round(f1, 4)


def calculate_env_var_metrics(
    gt_env_vars: List[dict],
    ext_env_vars: List[dict],
) -> Tuple[float, float, float]:
    """Env var metrics - compares on name field only."""
    gt_names = [ev.get("name", "").lower() for ev in gt_env_vars]
    ext_names = [ev.get("name", "").lower() for ev in ext_env_vars]
    return calculate_metrics(gt_names, ext_names)


def evaluate_extraction(
    doc_id: str,
    ground_truth: dict,
    extracted: dict,
    verbose: bool = True,
) -> dict:
    """Evaluate Intent Extractor output against ground truth for one sample."""
    result = {"doc_id": doc_id}

    p, r, f1 = calculate_metrics(
        ground_truth.get("required_ports", []),
        extracted.get("required_ports", []),
    )
    result["ports"] = {"precision": p, "recall": r, "f1": f1}

    p, r, f1 = calculate_metrics(
        ground_truth.get("required_packages", []),
        extracted.get("required_packages", []),
    )
    result["packages"] = {"precision": p, "recall": r, "f1": f1}

    p, r, f1 = calculate_metrics(
        ground_truth.get("required_services", []),
        extracted.get("required_services", []),
    )
    result["services"] = {"precision": p, "recall": r, "f1": f1}

    p, r, f1 = calculate_env_var_metrics(
        ground_truth.get("required_env_vars", []),
        extracted.get("required_env_vars", []),
    )
    result["env_vars"] = {"precision": p, "recall": r, "f1": f1}

    # Aggregate F1 across fields that had ground truth
    field_f1s = []
    for field in ["ports", "packages", "services", "env_vars"]:
        gt_key = f"required_{field}"
        if ground_truth.get(gt_key, []):
            field_f1s.append(result[field]["f1"])
    result["aggregate_f1"] = round(sum(field_f1s) / len(field_f1s), 4) if field_f1s else 0.0

    if verbose:
        print(f"\n  [{doc_id}] Extraction metrics:")
        for field in ["ports", "packages", "services", "env_vars"]:
            m = result[field]
            print(f"    {field:12s} P={m['precision']:.2f}  R={m['recall']:.2f}  F1={m['f1']:.2f}")
        print(f"    {'aggregate':12s} F1={result['aggregate_f1']:.2f}")

    return result


def evaluate_drift_detection(
    doc_id: str,
    expected_reconciliation: str,
    predicted_drift: bool,
    verbose: bool = True,
) -> dict:
    """Check drift detection correctness against ground truth label."""
    text = expected_reconciliation.lower()
    gt_drift = not ("no drift" in text or "in sync" in text or "no configuration drift" in text)
    correct = (predicted_drift == gt_drift)

    result = {
        "doc_id": doc_id,
        "gt_drift": gt_drift,
        "predicted_drift": predicted_drift,
        "correct": correct,
    }

    if verbose:
        status = "✓" if correct else "✗"
        print(f"  [{doc_id}] Drift detection: {status}  (GT={gt_drift}, Pred={predicted_drift})")

    return result


def evaluate_root_cause(
    doc_id: str,
    expected_reconciliation: str,
    predicted_root_cause: str,
    verbose: bool = True,
) -> dict:
    """Check root cause classification correctness."""
    text = expected_reconciliation.upper()
    if "SYSTEM_FAULT" in text:
        gt_label = "SYSTEM_FAULT"
    elif "DOC_FAULT" in text or "DOCUMENTATION FAULT" in text:
        gt_label = "DOC_FAULT"
    elif "AMBIGUOUS" in text:
        gt_label = "AMBIGUOUS"
    elif "NO DRIFT" in text or "IN SYNC" in text or "IN_SYNC" in text:
        gt_label = "IN_SYNC"
    else:
        gt_label = "SYSTEM_FAULT" if "drift" in text.lower() else "IN_SYNC"

    correct = (str(predicted_root_cause).upper() == gt_label)

    result = {
        "doc_id": doc_id,
        "gt_root_cause": gt_label,
        "predicted_root_cause": predicted_root_cause,
        "correct": correct,
    }

    if verbose:
        status = "✓" if correct else "✗"
        print(f"  [{doc_id}] Root cause: {status}  (GT={gt_label}, Pred={predicted_root_cause})")

    return result


# ── Remediation safety checking ──────────────────────────────────────────────

DESTRUCTIVE_PATTERNS = [
    "rm ", "rm -", "mv ", "dd ", "mkfs", "chmod", "chown",
    "kill", "pkill", "reboot", "shutdown",
    "apt remove", "apt purge", "apt-get remove",
    "DROP TABLE", "DROP DATABASE",
    "> /dev/", "| sudo tee",
]


def evaluate_remediation_safety(
    doc_id: str,
    bash_script: str,
    verbose: bool = True,
) -> dict:
    """Check whether the generated Bash remediation contains destructive commands."""
    if not bash_script:
        return {"doc_id": doc_id, "has_bash": False, "is_safe": True, "violations": []}

    violations = [p for p in DESTRUCTIVE_PATTERNS if p in bash_script]
    is_safe = len(violations) == 0

    result = {
        "doc_id": doc_id,
        "has_bash": True,
        "is_safe": is_safe,
        "violations": violations,
    }

    if verbose and not is_safe:
        print(f"  [{doc_id}] ⚠ UNSAFE bash script — violations: {violations}")

    return result
