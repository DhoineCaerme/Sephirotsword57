import sys
import os
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


CYAN  = "\033[96m"
PINK  = "\033[95m"
GREEN = "\033[92m"
RED   = "\033[91m"
DIM   = "\033[90m"
RESET = "\033[0m"
BOLD  = "\033[1m"


# ── Curated sample IDs — one per category, chosen for reliable demo output ──
DEMO_SAMPLE_IDS = [
    "001",  # Port Drift
    "002",  # Package Drift
    "003",  # Service/Docker Drift
    "004",  # Environment Variable Drift
]


def banner():
    print(f"\n{PINK}{BOLD}◢◤ SEPHIROTSWORD57 :: QUICK DEMO ◢◤{RESET}")
    print(f"{DIM}// running 4 samples, one per drift category //{RESET}\n")


def main():
    banner()

    from main import run_full_pipeline

    dataset_path = PROJECT_ROOT / "Dataset" / "Doc2State.json"
    if not dataset_path.exists():
        print(f"{RED}Dataset not found at {dataset_path}{RESET}")
        return 1

    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)
    by_id = {s["id"]: s for s in dataset}

    results = []
    for i, sample_id in enumerate(DEMO_SAMPLE_IDS, 1):
        if sample_id not in by_id:
            print(f"{RED}Sample {sample_id} not found in dataset, skipping.{RESET}")
            continue

        sample = by_id[sample_id]
        cat = sample["category"]
        print(f"{PINK}[{i}/{len(DEMO_SAMPLE_IDS)}]{RESET} "
              f"{BOLD}Sample {sample_id}{RESET} {DIM}::{RESET} {CYAN}{cat}{RESET}")
        print(f"  {DIM}doc:{RESET} {sample['doc_snippet'][:80]}...")

        save_path = PROJECT_ROOT / "outputs" / f"report_sample_{sample_id}.json"
        try:
            t0 = time.time()
            intent, live_state, report = run_full_pipeline(
                sample["doc_snippet"],
                mock_live_state=sample["simulated_live_state"],
                save_report_path=str(save_path),
            )
            elapsed = time.time() - t0

            drift_color = RED if report.drift_detected else GREEN
            verdict = "DRIFT" if report.drift_detected else "SYNC"
            print(f"  {drift_color}{verdict}{RESET} {DIM}::{RESET} "
                  f"root_cause = {drift_color}{report.root_cause}{RESET} "
                  f"{DIM}({elapsed:.1f}s){RESET}")

            n_discrep = len(report.discrepancies or [])
            print(f"  {DIM}discrepancies:{RESET} {n_discrep}")
            print(f"  {DIM}saved to:{RESET} {save_path.relative_to(PROJECT_ROOT)}")
            print()

            results.append({
                "id": sample_id,
                "category": cat,
                "drift": report.drift_detected,
                "rc": report.root_cause,
                "elapsed": elapsed,
            })

            # Rate-limit pause between samples
            if i < len(DEMO_SAMPLE_IDS):
                pause = int(os.getenv("DEMO_PAUSE", "10"))
                if pause > 0:
                    print(f"  {DIM}pausing {pause}s for rate limit...{RESET}\n")
                    time.sleep(pause)

        except Exception as e:
            print(f"  {RED}FAIL :: {e.__class__.__name__}: {e}{RESET}\n")

    # Summary
    print(f"{PINK}{'─' * 60}{RESET}")
    print(f"{BOLD}DEMO SUMMARY{RESET}")
    for r in results:
        verdict_color = RED if r["drift"] else GREEN
        print(f"  {r['id']:>4} {DIM}::{RESET} {r['category']:<28} "
              f"{verdict_color}{r['rc']:<14}{RESET} {DIM}{r['elapsed']:.1f}s{RESET}")
    print()
    print(f"{DIM}// view the dashboard: streamlit run ui/app.py → DASHBOARD page{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())