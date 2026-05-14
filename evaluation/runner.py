"""
Evaluation runner — executes the full Sephirotsword57 pipeline
on Doc2State-100 samples and computes all metrics.
"""

import json
import time
import logging
import argparse
import sys
import os
from typing import Optional

# Make sure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics import (
    calculate_metrics,
    evaluate_extraction,
    evaluate_drift_detection,
    evaluate_root_cause,
    evaluate_remediation_safety,
)

log = logging.getLogger("evaluator")


def load_dataset(dataset_path: str) -> list:
    """Load and validate the Doc2State dataset."""
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Dataset must be a JSON list, got {type(data).__name__}")
    return data


def run_full_evaluation(
    dataset_path: str = "Dataset/Doc2State.json",
    verbose: bool = True,
    limit: Optional[int] = None,
) -> dict:
    """Run the main pipeline on every sample, compute all metrics."""
    from main import run_full_pipeline

    dataset = load_dataset(dataset_path)
    if limit is not None:
        dataset = dataset[:limit]
        log.info(f"[LIMIT] Running first {limit} samples only.")

    extraction_results = []
    drift_results = []
    root_cause_results = []
    safety_results = []

    for sample in dataset:
        doc_id = sample["id"]
        snippet = sample["doc_snippet"]
        gt_intent = sample["ground_truth_intent"]
        mock_state = sample["simulated_live_state"]
        expected = sample["expected_reconciliation"]

        print(f"\n{'─'*50}\nSample {doc_id} [{sample['category']}]")

        try:
            save_path = f"outputs/report_sample_{doc_id}.json"
            intent, live_state, report = run_full_pipeline(
                doc_snippet=snippet,
                mock_live_state=mock_state,
                save_report_path=save_path,
            )

            extraction_results.append(
                evaluate_extraction(doc_id, gt_intent, intent.model_dump(), verbose=verbose)
            )
            drift_results.append(
                evaluate_drift_detection(doc_id, expected, report.drift_detected, verbose=verbose)
            )
            root_cause_results.append(
                evaluate_root_cause(doc_id, expected, report.root_cause, verbose=verbose)
            )
            safety_results.append(
                evaluate_remediation_safety(doc_id, report.remediation_bash or "", verbose=verbose)
            )
        except Exception as e:
            log.error(f"Error on sample {doc_id}: {e}")

        time.sleep(10)  # rate-limit pause between samples

    print_aggregate_results(extraction_results, drift_results, root_cause_results, safety_results)

    return {
        "extraction": extraction_results,
        "drift": drift_results,
        "root_cause": root_cause_results,
        "safety": safety_results,
    }


def run_baseline_evaluation(
    dataset_path: str = "Dataset/Doc2State.json",
    limit: Optional[int] = None,
) -> dict:
    """Run all 3 baselines on the dataset and print comparison metrics."""
    from baselines import (
        run_baseline_direct_llm,
        run_baseline_regex,
        run_baseline_single_agent_rag,
    )

    dataset = load_dataset(dataset_path)
    if limit is not None:
        dataset = dataset[:limit]
        log.info(f"[LIMIT] Running first {limit} samples for baseline comparison.")

    results = {
        "B1_direct_llm":       {"drift": [], "root_cause": []},
        "B2_regex":            {"drift": [], "root_cause": []},
        "B3_single_agent_rag": {"drift": [], "root_cause": []},
    }

    for i, sample in enumerate(dataset):
        doc_id = sample["id"]
        snippet = sample["doc_snippet"]
        live = sample["simulated_live_state"]
        expected = sample["expected_reconciliation"]

        print(f"\n[{i+1}/{len(dataset)}] Sample {doc_id} [{sample['category']}]")

        # Baseline 2 — no API
        b2 = run_baseline_regex(snippet, live)
        d2 = evaluate_drift_detection(doc_id, expected, b2["drift_detected"], verbose=False)
        r2 = evaluate_root_cause(doc_id, expected, b2["root_cause"], verbose=False)
        results["B2_regex"]["drift"].append(d2)
        results["B2_regex"]["root_cause"].append(r2)
        print(f"  B2 Regex        — Drift: {'✓' if d2['correct'] else '✗'}  RC: {'✓' if r2['correct'] else '✗'}")

        # Baseline 1 — uses API
        try:
            b1 = run_baseline_direct_llm(snippet, live)
            d1 = evaluate_drift_detection(doc_id, expected, b1["drift_detected"], verbose=False)
            r1 = evaluate_root_cause(doc_id, expected, b1["root_cause"], verbose=False)
            results["B1_direct_llm"]["drift"].append(d1)
            results["B1_direct_llm"]["root_cause"].append(r1)
            print(f"  B1 Direct LLM   — Drift: {'✓' if d1['correct'] else '✗'}  RC: {'✓' if r1['correct'] else '✗'}")
        except Exception as e:
            log.error(f"B1 failed on {doc_id}: {e}")

        time.sleep(6)

        # Baseline 3 — uses API
        try:
            b3 = run_baseline_single_agent_rag(snippet, live)
            d3 = evaluate_drift_detection(doc_id, expected, b3["drift_detected"], verbose=False)
            r3 = evaluate_root_cause(doc_id, expected, b3["root_cause"], verbose=False)
            results["B3_single_agent_rag"]["drift"].append(d3)
            results["B3_single_agent_rag"]["root_cause"].append(r3)
            print(f"  B3 RAG Agent    — Drift: {'✓' if d3['correct'] else '✗'}  RC: {'✓' if r3['correct'] else '✗'}")
        except Exception as e:
            log.error(f"B3 failed on {doc_id}: {e}")

        time.sleep(8)

    # Comparison table
    print(f"\n{'='*65}")
    print("BASELINE COMPARISON RESULTS")
    print(f"{'='*65}")
    print(f"{'Baseline':<26} {'Drift Acc':>10} {'Drift F1':>10} {'RootCause Acc':>14}")
    print("-" * 65)
    for name, data in results.items():
        dl, rl = data["drift"], data["root_cause"]
        if not dl:
            continue
        correct_d = sum(1 for r in dl if r["correct"])
        tp = sum(1 for r in dl if r["gt_drift"] and r["predicted_drift"])
        fp = sum(1 for r in dl if not r["gt_drift"] and r["predicted_drift"])
        fn = sum(1 for r in dl if r["gt_drift"] and not r["predicted_drift"])
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        rc_acc = sum(1 for r in rl if r["correct"]) / len(rl) if rl else 0.0
        print(f"  {name:<24} {correct_d/len(dl):>10.4f} {f1:>10.4f} {rc_acc:>14.4f}")
    print("-" * 65)

    return results


def print_aggregate_results(
    extraction_results: list,
    drift_results: list,
    root_cause_results: list,
    safety_results: list,
) -> None:
    """Print final aggregate metrics across all samples."""
    print(f"\n{'='*60}\nAGGREGATE EVALUATION RESULTS\n{'='*60}")

    if extraction_results:
        for field in ["ports", "packages", "services", "env_vars"]:
            f1s = [r[field]["f1"] for r in extraction_results]
            print(f"Intent Extraction F1 [{field}]: {sum(f1s)/len(f1s):.4f}")
        agg = [r["aggregate_f1"] for r in extraction_results]
        print(f"Intent Extraction F1 [aggregate]: {sum(agg)/len(agg):.4f}")

    if drift_results:
        correct = sum(1 for r in drift_results if r["correct"])
        total = len(drift_results)
        tp = sum(1 for r in drift_results if r["gt_drift"] and r["predicted_drift"])
        fp = sum(1 for r in drift_results if not r["gt_drift"] and r["predicted_drift"])
        fn = sum(1 for r in drift_results if r["gt_drift"] and not r["predicted_drift"])
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        print(f"\nDrift Detection Accuracy : {correct/total:.4f} ({correct}/{total})")
        print(f"Drift Detection Precision: {prec:.4f}")
        print(f"Drift Detection Recall   : {rec:.4f}")
        print(f"Drift Detection F1       : {f1:.4f}")

    if root_cause_results:
        correct = sum(1 for r in root_cause_results if r["correct"])
        total = len(root_cause_results)
        print(f"\nRoot Cause Attribution Accuracy: {correct/total:.4f} ({correct}/{total})")

    if safety_results:
        scripts = [r for r in safety_results if r["has_bash"]]
        safe = [r for r in scripts if r["is_safe"]]
        print(f"\nRemediation Scripts Generated: {len(scripts)}")
        if scripts:
            print(f"Remediation Safety Rate     : {len(safe)/len(scripts):.4f}")


def run_single_sample(sample_id: str, dataset_path: str = "Dataset/Doc2State.json") -> dict:
    """Run pipeline and evaluation on one specific sample."""
    from main import run_full_pipeline

    dataset = load_dataset(dataset_path)
    sample = next((s for s in dataset if s["id"] == sample_id), None)
    if sample is None:
        raise ValueError(f"Sample ID {sample_id!r} not found in dataset.")

    save_path = f"outputs/report_sample_{sample_id}.json"
    intent, live_state, report = run_full_pipeline(
        sample["doc_snippet"],
        mock_live_state=sample["simulated_live_state"],
        save_report_path=save_path,
    )

    return {
        "extraction": evaluate_extraction(sample_id, sample["ground_truth_intent"], intent.model_dump()),
        "drift": evaluate_drift_detection(sample_id, sample["expected_reconciliation"], report.drift_detected),
        "root_cause": evaluate_root_cause(sample_id, sample["expected_reconciliation"], report.root_cause),
        "safety": evaluate_remediation_safety(sample_id, report.remediation_bash or ""),
    }


def dry_run_validation(dataset_path: str = "Dataset/Doc2State.json") -> None:
    """Validate the dataset and metric helpers, no API calls."""
    print("Running dataset validation (no API calls)...")
    data = load_dataset(dataset_path)

    required_keys = {
        "id", "category", "doc_snippet", "ground_truth_intent",
        "simulated_live_state", "expected_reconciliation",
    }
    errors = []
    for s in data:
        missing = required_keys - set(s.keys())
        if missing:
            errors.append(f"Sample {s.get('id','?')}: missing {missing}")
        if not s.get("doc_snippet", "").strip():
            errors.append(f"Sample {s.get('id','?')}: empty doc_snippet")

    ids = [s["id"] for s in data]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"Duplicate IDs: {dupes}")

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

    # Test metric helpers
    print("\nTesting metric helpers...")
    p, r, f1 = calculate_metrics(["8080", "443"], ["8080"])
    assert abs(p - 1.0) < 1e-6 and abs(r - 0.5) < 1e-6, "metric check failed"
    print("  ✓ calculate_metrics")

    d = evaluate_drift_detection("DRY-001", "Drift detected. SYSTEM_FAULT.", True, verbose=False)
    assert d["correct"]
    print("  ✓ evaluate_drift_detection")

    rc = evaluate_root_cause("DRY-001", "SYSTEM_FAULT detected.", "SYSTEM_FAULT", verbose=False)
    assert rc["correct"]
    print("  ✓ evaluate_root_cause")

    safe = evaluate_remediation_safety("DRY-001", "sudo apt install -y nginx", verbose=False)
    unsafe = evaluate_remediation_safety("DRY-002", "rm -rf /etc/nginx", verbose=False)
    assert safe["is_safe"] and not unsafe["is_safe"]
    print("  ✓ evaluate_remediation_safety")

    print("\n✓ All dry-run checks passed.")


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Sephirotsword57 Evaluator")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate dataset and metric helpers, no API calls.")
    parser.add_argument("--sample-id", type=str, default=None,
                        help="Run one sample by ID, e.g. --sample-id 003")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only run first N samples in full evaluation.")
    parser.add_argument("--baselines", action="store_true",
                        help="Run baseline comparison instead of main pipeline.")
    parser.add_argument("--dataset", type=str, default="Dataset/Doc2State.json",
                        help="Path to Doc2State JSON dataset.")
    args = parser.parse_args()

    if args.dry_run:
        dry_run_validation(args.dataset)
    elif args.sample_id:
        run_single_sample(args.sample_id, args.dataset)
    elif args.baselines:
        run_baseline_evaluation(args.dataset, limit=args.limit)
    else:
        run_full_evaluation(args.dataset, limit=args.limit)
