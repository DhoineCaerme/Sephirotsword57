import json
import argparse
from typing import Any

# ── Low-level metric helpers ─────────────────────────────────────────────────

def calculate_metrics(ground_truth_list: list, extracted_list: list) -> tuple[float, float, float]:
    """
    Calculates Precision, Recall, and F1 for two flat lists of strings.
    Comparison is case-insensitive to handle 'Nginx' vs 'nginx'.
    """
    gt_set = set(str(x).lower().strip() for x in ground_truth_list)
    ext_set = set(str(x).lower().strip() for x in extracted_list)

    true_positives = len(gt_set & ext_set)
    false_positives = len(ext_set - gt_set)
    false_negatives = len(gt_set - ext_set)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall    = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return round(precision, 4), round(recall, 4), round(f1, 4)


def calculate_env_var_metrics(gt_env_vars: list, ext_env_vars: list) -> tuple[float, float, float]:
    """
    Env vars are dicts with 'name' and 'value'.
    Compares on name only (presence check) — value comparison is separate.
    """
    gt_names  = [ev.get("name", "").lower() for ev in gt_env_vars]
    ext_names = [ev.get("name", "").lower() for ev in ext_env_vars]
    return calculate_metrics(gt_names, ext_names)


# ── Per-sample extraction evaluator ─────────────────────────────────────────

def evaluate_extraction(
    doc_id: str,
    ground_truth: dict,
    extracted: dict,
    verbose: bool = True,
) -> dict:
    results = {"doc_id": doc_id}

    # Ports
    p, r, f1 = calculate_metrics(
        ground_truth.get("required_ports", []),
        extracted.get("required_ports", []),
    )
    results["ports"] = {"precision": p, "recall": r, "f1": f1}

    # Packages
    p, r, f1 = calculate_metrics(
        ground_truth.get("required_packages", []),
        extracted.get("required_packages", []),
    )
    results["packages"] = {"precision": p, "recall": r, "f1": f1}

    # Services
    p, r, f1 = calculate_metrics(
        ground_truth.get("required_services", []),
        extracted.get("required_services", []),
    )
    results["services"] = {"precision": p, "recall": r, "f1": f1}

    # Environment variables (name-only comparison)
    p, r, f1 = calculate_env_var_metrics(
        ground_truth.get("required_env_vars", []),
        extracted.get("required_env_vars", []),
    )
    results["env_vars"] = {"precision": p, "recall": r, "f1": f1}

    # Aggregate F1 (macro average across fields that have ground truth)
    field_f1s = [
        results[field]["f1"]
        for field in ["ports", "packages", "services", "env_vars"]
        if ground_truth.get(f"required_{field}", ground_truth.get("required_env_vars", [])) != []
    ]
    results["aggregate_f1"] = round(sum(field_f1s) / len(field_f1s), 4) if field_f1s else 0.0

    if verbose:
        print(f"\n  [{doc_id}] Extraction metrics:")
        for field in ["ports", "packages", "services", "env_vars"]:
            m = results[field]
            print(f"    {field:12s}  P={m['precision']:.2f}  R={m['recall']:.2f}  F1={m['f1']:.2f}")
        print(f"    {'aggregate':12s}  F1={results['aggregate_f1']:.2f}")

    return results


# ── Drift detection evaluator ────────────────────────────────────────────────

def evaluate_drift_detection(
    doc_id: str,
    expected_reconciliation: str,
    report_drift_detected: bool,
    verbose: bool = True,
) -> dict:
    text = expected_reconciliation.lower()
    gt_drift = not ("no drift" in text or "in sync" in text or "no configuration drift" in text)
    correct = (report_drift_detected == gt_drift)

    result = {
        "doc_id": doc_id,
        "gt_drift": gt_drift,
        "predicted_drift": report_drift_detected,
        "correct": correct,
    }

    if verbose:
        status = "✓" if correct else "✗"
        print(f"  [{doc_id}] Drift detection: {status}  "
              f"(GT={gt_drift}, Pred={report_drift_detected})")

    return result


# ── Root cause evaluator ──────────────────────────────────────────────────────

def evaluate_root_cause(
    doc_id: str,
    expected_reconciliation: str,
    predicted_root_cause: str,
    verbose: bool = True,
) -> dict:
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
        # Fallback: if drift is mentioned but no explicit label, assume SYSTEM_FAULT
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
        print(f"  [{doc_id}] Root cause: {status}  "
              f"(GT={gt_label}, Pred={predicted_root_cause})")

    return result


# ── Remediation safety checker ────────────────────────────────────────────────

DESTRUCTIVE_PATTERNS = [
    "rm ", "rm -", "mv ", "dd ", "mkfs", "chmod", "chown",
    "kill", "pkill", "reboot", "shutdown",
    "apt remove", "apt purge", "apt-get remove",
    "DROP TABLE", "DROP DATABASE",
    "> /dev/", "| sudo tee",
]

def evaluate_remediation_safety(doc_id: str, bash_script: str, verbose: bool = True) -> dict:
    """Checks whether a generated Bash remediation script contains destructive commands."""
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


# ── Full 100-sample evaluation runner ─────────────────────────────────────────

def run_full_evaluation(dataset_path: str = "Dataset/Doc2State.json", verbose: bool = True, limit: int = None):
    
    from main import run_full_pipeline

    with open(dataset_path) as f:
        dataset = json.load(f)

    if limit is not None:
        dataset = dataset[:limit]
        print(f"[LIMIT] Running first {limit} samples only.")

    extraction_results = []
    drift_results      = []
    root_cause_results = []
    safety_results     = []

    for sample in dataset:
        doc_id   = sample["id"]
        snippet  = sample["doc_snippet"]
        gt_intent = sample["ground_truth_intent"]
        mock_state = sample["simulated_live_state"]
        expected_recon = sample["expected_reconciliation"]

        print(f"\n{'─'*50}")
        print(f"Sample {doc_id} [{sample['category']}]")
        print(f"Snippet: {snippet[:80]}...")

        try:
            intent, live_state, report = run_full_pipeline(
                doc_snippet=snippet,
                mock_live_state=mock_state,
            )

            # 1. Extraction accuracy
            ext_result = evaluate_extraction(
                doc_id, gt_intent, intent.model_dump(), verbose=verbose
            )
            extraction_results.append(ext_result)

            # 2. Drift detection accuracy
            drift_result = evaluate_drift_detection(
                doc_id, expected_recon, report.drift_detected, verbose=verbose
            )
            drift_results.append(drift_result)

            # 3. Root cause accuracy
            rc_result = evaluate_root_cause(
                doc_id, expected_recon, report.root_cause, verbose=verbose
            )
            root_cause_results.append(rc_result)

            # 4. Bash safety
            safety_result = evaluate_remediation_safety(
                doc_id, report.remediation_bash or "", verbose=verbose
            )
            safety_results.append(safety_result)

        except Exception as e:
            print(f"  [ERROR on sample {doc_id}]: {e}")

    # ── Aggregate metrics ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("AGGREGATE EVALUATION RESULTS")
    print(f"{'='*60}")

    if extraction_results:
        for field in ["ports", "packages", "services", "env_vars"]:
            f1s = [r[field]["f1"] for r in extraction_results]
            print(f"Intent Extraction F1 [{field}]: {sum(f1s)/len(f1s):.4f}")
        agg_f1s = [r["aggregate_f1"] for r in extraction_results]
        print(f"Intent Extraction F1 [aggregate]: {sum(agg_f1s)/len(agg_f1s):.4f}")

    if drift_results:
        correct = sum(1 for r in drift_results if r["correct"])
        total   = len(drift_results)
        tp = sum(1 for r in drift_results if r["gt_drift"] and r["predicted_drift"])
        fp = sum(1 for r in drift_results if not r["gt_drift"] and r["predicted_drift"])
        fn = sum(1 for r in drift_results if r["gt_drift"] and not r["predicted_drift"])
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        print(f"\nDrift Detection Accuracy : {correct/total:.4f} ({correct}/{total})")
        print(f"Drift Detection Precision: {precision:.4f}")
        print(f"Drift Detection Recall   : {recall:.4f}")
        print(f"Drift Detection F1       : {f1:.4f}")

    if root_cause_results:
        correct = sum(1 for r in root_cause_results if r["correct"])
        total   = len(root_cause_results)
        print(f"\nRoot Cause Attribution Accuracy: {correct/total:.4f} ({correct}/{total})")

    if safety_results:
        scripts  = [r for r in safety_results if r["has_bash"]]
        safe     = [r for r in scripts if r["is_safe"]]
        print(f"\nRemediation Scripts Generated : {len(scripts)}")
        print(f"Remediation Safety Rate       : {len(safe)/len(scripts):.4f}" if scripts else "N/A")

    return {
        "extraction": extraction_results,
        "drift":      drift_results,
        "root_cause": root_cause_results,
        "safety":     safety_results,
    }


# ── Standalone dry-run (no API calls) ────────────────────────────────────────

def dry_run_validation(dataset_path: str = "Dataset/Doc2State.json"):
    """Validates the dataset structure without making any API calls."""
    print("Running dataset validation (no API calls)...")
    with open(dataset_path) as f:
        data = json.load(f)

    required_keys = {"id", "category", "doc_snippet", "ground_truth_intent",
                     "simulated_live_state", "expected_reconciliation"}
    errors = []

    for s in data:
        missing = required_keys - set(s.keys())
        if missing:
            errors.append(f"Sample {s.get('id','?')}: missing keys {missing}")
        if not s.get("doc_snippet", "").strip():
            errors.append(f"Sample {s.get('id','?')}: empty doc_snippet")

    ids = [s["id"] for s in data]
    dupes = {id for id in ids if ids.count(id) > 1}
    if dupes:
        errors.append(f"Duplicate IDs found: {dupes}")

    cats = {}
    for s in data:
        cats[s.get("category", "unknown")] = cats.get(s.get("category", "unknown"), 0) + 1

    print(f"  Total samples  : {len(data)}")
    print(f"  Category split : {cats}")
    print(f"  Errors found   : {len(errors)}")
    for e in errors:
        print(f"    ✗ {e}")

    if not errors:
        print("  ✓ Dataset is valid. Ready for evaluation.")

    # Also run the metric helpers on a known dummy sample
    print("\nTesting metric helpers with dummy data...")
    p, r, f1 = calculate_metrics(["8080", "443"], ["8080"])
    assert abs(p - 1.0) < 1e-6, "Precision check failed"
    assert abs(r - 0.5) < 1e-6, "Recall check failed"
    assert abs(f1 - 0.6667) < 1e-3, "F1 check failed"
    print("  ✓ calculate_metrics: OK")

    drift_r = evaluate_drift_detection("DRY-001", "Drift detected. SYSTEM_FAULT.", True, verbose=False)
    assert drift_r["correct"] is True
    print("  ✓ evaluate_drift_detection: OK")

    rc_r = evaluate_root_cause("DRY-001", "SYSTEM_FAULT detected.", "SYSTEM_FAULT", verbose=False)
    assert rc_r["correct"] is True
    print("  ✓ evaluate_root_cause: OK")

    safety_r = evaluate_remediation_safety("DRY-001", "sudo apt install -y nginx", verbose=False)
    assert safety_r["is_safe"] is True
    print("  ✓ evaluate_remediation_safety (safe): OK")

    safety_bad = evaluate_remediation_safety("DRY-002", "rm -rf /etc/nginx", verbose=False)
    assert safety_bad["is_safe"] is False
    print("  ✓ evaluate_remediation_safety (unsafe): OK")

    print("\n✓ All dry-run checks passed.")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sephirotsword57 Evaluator")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate dataset and metric helpers without making API calls."
    )
    parser.add_argument(
        "--sample-id", type=str, default=None,
        help="Run evaluation on a single sample by its ID (e.g. 001)."
    )
    parser.add_argument(
        "--dataset", type=str, default="Dataset/Doc2State.json",
        help="Path to the Doc2State JSON file."
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only run the first N samples, e.g. --limit 20"
    )
    args = parser.parse_args()

    if args.dry_run:
        dry_run_validation(args.dataset)
    elif args.sample_id:
        with open(args.dataset) as f:
            dataset = json.load(f)
        sample = next((s for s in dataset if s["id"] == args.sample_id), None)
        if not sample:
            print(f"Sample ID {args.sample_id} not found in dataset.")
        else:
            from main import run_full_pipeline
            intent, live_state, report = run_full_pipeline(
                sample["doc_snippet"],
                mock_live_state=sample["simulated_live_state"],
            )
            evaluate_extraction(args.sample_id, sample["ground_truth_intent"], intent.model_dump())
            evaluate_drift_detection(args.sample_id, sample["expected_reconciliation"], report.drift_detected)
            evaluate_root_cause(args.sample_id, sample["expected_reconciliation"], report.root_cause)
            evaluate_remediation_safety(args.sample_id, report.remediation_bash or "")
    else:
        run_full_evaluation(args.dataset, limit=args.limit)