import json
import re
from pathlib import Path
from typing import Optional


def load_all_reports(outputs_dir: str = "outputs") -> list:
    out_path = Path(outputs_dir)
    if not out_path.exists():
        return []

    reports = []
    for f in sorted(out_path.glob("report_*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            # Extract sample_id from filename when possible
            m = re.match(r"report_sample_(\w+)\.json$", f.name)
            data["_filename"] = f.name
            data["_sample_id"] = m.group(1) if m else None
            data["_is_dataset_run"] = m is not None
            reports.append(data)
        except (json.JSONDecodeError, OSError):
            # Silently skip corrupted files
            continue
    return reports


def load_dataset(dataset_path: str = "Dataset/Doc2State.json") -> dict:
    p = Path(dataset_path)
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return {s["id"]: s for s in data}
    except (json.JSONDecodeError, OSError, KeyError):
        return {}


def compute_aggregate_stats(reports: list, dataset_index: dict) -> dict:

    if not reports:
        return {
            "total_reports": 0, "dataset_reports": 0,
            "drift_distribution": {}, "by_category": {},
            "drift_accuracy": 0.0, "root_cause_accuracy": 0.0,
            "extraction_stats": {}, "safety_rate": 0.0,
        }

    drift_dist = {}
    by_category = {}
    drift_correct, drift_total = 0, 0
    rc_correct, rc_total = 0, 0
    ext_stats = {
        f: {"tp": 0, "fp": 0, "fn": 0} for f in
        ["ports", "packages", "services", "env_vars"]
    }
    bash_total, bash_safe = 0, 0
    destructive_patterns = ["rm ", "rm -", "mv ", "dd ", "mkfs", "chmod", "chown",
                            "kill", "pkill", "reboot", "shutdown",
                            "apt remove", "apt purge", "DROP TABLE", "DROP DATABASE"]

    for r in reports:
        rr = r.get("reconciliation_report", {})
        root_cause = (rr.get("root_cause") or "UNKNOWN").upper()
        drift_dist[root_cause] = drift_dist.get(root_cause, 0) + 1

        # Bash safety
        bash = rr.get("remediation_bash") or ""
        if bash:
            bash_total += 1
            violations = [p for p in destructive_patterns if p in bash]
            if not violations:
                bash_safe += 1

        # Only compute accuracy for dataset-tagged runs (have ground truth)
        sid = r.get("_sample_id")
        if sid is None or sid not in dataset_index:
            continue

        gt = dataset_index[sid]
        expected_recon = gt.get("expected_reconciliation", "").lower()
        category = gt.get("category", "Unknown")

        # Initialise category bucket
        if category not in by_category:
            by_category[category] = {
                "total": 0, "predicted_drift": 0, "correct_drift": 0,
                "correct_rc": 0,
            }

        by_category[category]["total"] += 1

        # Drift detection accuracy
        gt_drift = not ("no drift" in expected_recon or "in sync" in expected_recon)
        pred_drift = bool(rr.get("drift_detected"))
        drift_total += 1
        if gt_drift == pred_drift:
            drift_correct += 1
            by_category[category]["correct_drift"] += 1
        if pred_drift:
            by_category[category]["predicted_drift"] += 1

        # Root cause accuracy
        gt_rc = _infer_gt_root_cause(expected_recon)
        rc_total += 1
        if root_cause == gt_rc:
            rc_correct += 1
            by_category[category]["correct_rc"] += 1

        # Extraction stats — per field
        gt_intent = gt.get("ground_truth_intent", {})
        ext_intent = r.get("extracted_intent", {})

        for field, gt_key, ext_key in [
            ("ports",    "required_ports",    "required_ports"),
            ("packages", "required_packages", "required_packages"),
            ("services", "required_services", "required_services"),
        ]:
            gt_set = {x.lower() for x in gt_intent.get(gt_key, [])}
            ext_set = {x.lower() for x in ext_intent.get(ext_key, [])}
            ext_stats[field]["tp"] += len(gt_set & ext_set)
            ext_stats[field]["fp"] += len(ext_set - gt_set)
            ext_stats[field]["fn"] += len(gt_set - ext_set)

        # Env vars (compare by name)
        gt_ev = {e["name"].lower() for e in gt_intent.get("required_env_vars", [])}
        ext_ev = {e["name"].lower() for e in ext_intent.get("required_env_vars", [])}
        ext_stats["env_vars"]["tp"] += len(gt_ev & ext_ev)
        ext_stats["env_vars"]["fp"] += len(ext_ev - gt_ev)
        ext_stats["env_vars"]["fn"] += len(gt_ev - ext_ev)

    # Compute P/R/F1 for each field
    for field, s in ext_stats.items():
        tp, fp, fn = s["tp"], s["fp"], s["fn"]
        s["precision"] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        s["recall"]    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        s["f1"]        = (2 * s["precision"] * s["recall"]
                          / (s["precision"] + s["recall"])
                          if (s["precision"] + s["recall"]) > 0 else 0.0)

    return {
        "total_reports": len(reports),
        "dataset_reports": drift_total,
        "drift_distribution": drift_dist,
        "by_category": by_category,
        "drift_accuracy": drift_correct / drift_total if drift_total > 0 else 0.0,
        "root_cause_accuracy": rc_correct / rc_total if rc_total > 0 else 0.0,
        "extraction_stats": ext_stats,
        "safety_rate": bash_safe / bash_total if bash_total > 0 else 1.0,
        "bash_scripts_generated": bash_total,
    }


def _infer_gt_root_cause(expected_recon_lower: str) -> str:
    """Derive ground-truth root cause label from the dataset's expected_reconciliation text."""
    text = expected_recon_lower.upper()
    if "SYSTEM_FAULT" in text:
        return "SYSTEM_FAULT"
    if "DOC_FAULT" in text or "DOCUMENTATION FAULT" in text:
        return "DOC_FAULT"
    if "AMBIGUOUS" in text:
        return "AMBIGUOUS"
    if "NO DRIFT" in text or "IN SYNC" in text or "IN_SYNC" in text:
        return "IN_SYNC"
    return "SYSTEM_FAULT" if "drift" in expected_recon_lower else "IN_SYNC"

if __name__ == "__main__":
    reports = load_all_reports()
    dataset = load_dataset()
    stats = compute_aggregate_stats(reports, dataset)
    print(f"Loaded {stats['total_reports']} reports "
          f"({stats['dataset_reports']} matched to dataset samples)")
    print(f"Drift detection accuracy : {stats['drift_accuracy']:.4f}")
    print(f"Root cause accuracy      : {stats['root_cause_accuracy']:.4f}")
    print(f"Bash safety rate         : {stats['safety_rate']:.4f}")
    print(f"Drift distribution       : {stats['drift_distribution']}")
    print()
    print("Per-field extraction:")
    for field, s in stats["extraction_stats"].items():
        print(f"  {field:10s} P={s['precision']:.3f} R={s['recall']:.3f} F1={s['f1']:.3f}")