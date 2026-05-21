import sys
import os
import json
import importlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── ANSI colours for terminal output ─────────────────────────────────────────
CYAN  = "\033[96m"
PINK  = "\033[95m"
GREEN = "\033[92m"
RED   = "\033[91m"
DIM   = "\033[90m"
RESET = "\033[0m"
BOLD  = "\033[1m"


def banner():
    print(f"\n{PINK}{BOLD}◢◤ SEPHIROTSWORD57 :: SETUP VALIDATOR ◢◤{RESET}")
    print(f"{DIM}// pre-flight checks before evaluation //{RESET}\n")


def check(label: str, ok: bool, detail: str = "") -> bool:
    """Print a check result and return its boolean."""
    status = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    print(f"  {status} {label:<45} {DIM}{detail}{RESET}")
    return ok


def main():
    banner()
    failures = []

    # ── 1. Python version ────────────────────────────────────────────────
    print(f"{CYAN}[ PYTHON ]{RESET}")
    py_ok = sys.version_info >= (3, 10)
    if not check(
        "Python >= 3.10",
        py_ok,
        f"current: {sys.version_info.major}.{sys.version_info.minor}",
    ):
        failures.append("Upgrade to Python 3.10 or later (3.11 recommended).")
    print()

    # ── 2. Required dependencies ─────────────────────────────────────────
    print(f"{CYAN}[ DEPENDENCIES ]{RESET}")
    required = [
        ("crewai", "agent orchestration"),
        ("pydantic", "data schemas"),
        ("dotenv", "environment loader"),
        ("streamlit", "web UI"),
        ("google.generativeai", "Gemini provider"),
        ("litellm", "Groq + multi-provider"),
    ]
    for mod, desc in required:
        try:
            importlib.import_module(mod)
            check(f"import {mod}", True, desc)
        except ImportError:
            check(f"import {mod}", False, f"MISSING — {desc}")
            failures.append(f"Run: pip install {mod.split('.')[0]}")
    print()

    # ── 3. .env file ─────────────────────────────────────────────────────
    print(f"{CYAN}[ CONFIG ]{RESET}")
    env_path = PROJECT_ROOT / ".env"
    env_exists = env_path.exists()
    check(".env file present", env_exists, str(env_path))
    if not env_exists:
        failures.append("Create a .env file in the project root.")
    else:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        provider = os.getenv("LLM_PROVIDER", "").lower().strip()
        check(
            "LLM_PROVIDER set",
            provider in {"gemini", "groq"},
            f"value: {provider!r}",
        )
        if provider == "gemini":
            ok = bool(os.getenv("GEMINI_API_KEY"))
            check("GEMINI_API_KEY set", ok)
            if not ok:
                failures.append("Add GEMINI_API_KEY=... to your .env file")
        elif provider == "groq":
            ok = bool(os.getenv("GROQ_API_KEY"))
            check("GROQ_API_KEY set", ok)
            if not ok:
                failures.append("Add GROQ_API_KEY=... to your .env file")
        else:
            failures.append("Set LLM_PROVIDER=gemini or LLM_PROVIDER=groq in .env")
    print()

    # ── 4. Dataset ────────────────────────────────────────────────────────
    print(f"{CYAN}[ DATASET ]{RESET}")
    ds_path = PROJECT_ROOT / "Dataset" / "Doc2State.json"
    if not check("Doc2State.json exists", ds_path.exists(), str(ds_path)):
        failures.append("The dataset file Doc2State.json is missing.")
    else:
        try:
            with open(ds_path, encoding="utf-8") as f:
                data = json.load(f)
            check(
                "Dataset is a JSON list",
                isinstance(data, list),
                f"{len(data) if isinstance(data, list) else 0} entries",
            )
            check(
                "Dataset has 100 samples",
                isinstance(data, list) and len(data) == 100,
                f"got {len(data) if isinstance(data, list) else 0}",
            )
            cats = {}
            for s in data:
                c = s.get("category", "?")
                cats[c] = cats.get(c, 0) + 1
            check(
                "Four drift categories present",
                len(cats) == 4,
                ", ".join(f"{k}:{v}" for k, v in cats.items()),
            )
        except json.JSONDecodeError as e:
            check("Dataset JSON valid", False, str(e))
            failures.append("Doc2State.json has invalid JSON.")
    print()

    # ── 5. Filesystem ────────────────────────────────────────────────────
    print(f"{CYAN}[ FILESYSTEM ]{RESET}")
    folders = ["agents", "evaluation", "sandbox", "baselines", "ui", "outputs"]
    for folder in folders:
        path = PROJECT_ROOT / folder
        check(f"{folder}/ directory", path.exists(), str(path))
        if folder == "outputs" and not path.exists():
            try:
                path.mkdir()
                check("created outputs/", True)
            except OSError as e:
                check("create outputs/", False, str(e))
                failures.append("Cannot create outputs/ folder.")
    print()

    # ── 6. Project modules import ────────────────────────────────────────
    print(f"{CYAN}[ PROJECT MODULES ]{RESET}")
    project_modules = [
        "agents.schemas",
        "sandbox.safe_bash_tool",
        "evaluation.metrics",
        "evaluation.results_loader",
        "baselines.baseline_regex",
    ]
    for mod in project_modules:
        try:
            importlib.import_module(mod)
            check(f"import {mod}", True)
        except Exception as e:
            check(f"import {mod}", False, f"{e.__class__.__name__}: {e}")
            failures.append(f"Module {mod} failed to import.")
    print()

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"{PINK}{'─' * 60}{RESET}")
    if not failures:
        print(f"{GREEN}{BOLD}  ALL CHECKS PASSED — system is ready.{RESET}")
        print(f"{DIM}  Next step: python main.py --demo  OR  streamlit run ui/app.py{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}  VALIDATION FAILED — {len(failures)} issue(s):{RESET}\n")
        for i, fail in enumerate(failures, 1):
            print(f"  {RED}{i}.{RESET} {fail}")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())