"""
baseline_regex.py — Baseline 2: Rule-Based Regex Extractor

Zero API calls. Pure Python regex + keyword matching.
Represents the traditional deterministic approach to config auditing.

Strengths: fast, free, 100% reproducible.
Weaknesses: fails on colloquial names, implicit ports, unknown packages.
This is exactly the gap our multi-agent system fills.
"""

import re
import json


# ── Known package vocabulary (what the regex can recognise) ──────────────────
KNOWN_PACKAGES = [
    "nginx", "apache2", "httpd", "postgresql", "postgres", "mysql",
    "redis", "redis-server", "mongodb", "sqlite", "elasticsearch",
    "nodejs", "node", "npm", "python3", "python", "pip",
    "java", "openjdk", "maven", "gradle",
    "docker", "docker-compose", "containerd",
    "git", "curl", "wget", "vim", "nano",
    "certbot", "openssl", "ufw", "fail2ban",
    "rabbitmq", "kafka", "zookeeper",
    "memcached", "haproxy", "varnish",
    "php", "php-fpm", "composer",
    "ruby", "rails", "bundler",
    "golang", "go", "supervisor", "pm2",
]

KNOWN_SERVICES = [
    "nginx", "apache2", "postgresql", "mysql", "redis-server", "redis",
    "mongodb", "elasticsearch", "rabbitmq", "kafka", "docker",
    "supervisor", "pm2", "php-fpm", "haproxy", "memcached", "zookeeper",
]


def extract_ports(text: str) -> list:
    patterns = [
        r'\bport[s]?\s*:?\s*(\d{2,5})\b',
        r'\blistening\s+on\s+(\d{2,5})\b',
        r'\brun[s]?\s+on\s+(\d{2,5})\b',
        r'\bbind[s]?\s+to\s+(\d{2,5})\b',
        r':(\d{2,5})\b(?!\.\d)',
        r'\bexpose[sd]?\s+(\d{2,5})\b',
    ]
    found = set()
    for p in patterns:
        for m in re.findall(p, text, re.IGNORECASE):
            n = int(m)
            if 80 <= n <= 65535:
                found.add(str(n))
    return sorted(found)


def extract_packages(text: str) -> list:
    lower = text.lower()
    return sorted({p for p in KNOWN_PACKAGES
                   if re.search(r'\b' + re.escape(p) + r'\b', lower)})


def extract_services(text: str) -> list:
    lower = text.lower()
    found = set()
    for s in KNOWN_SERVICES:
        if re.search(r'\b' + re.escape(s) + r'\b', lower):
            found.add(s)
    # Also catch "X container" / "X service" patterns
    for m in re.findall(r'\b(\w[\w-]+)\s+(?:container|service|daemon)\b', lower):
        if len(m) > 2:
            found.add(m)
    return sorted(found)


def extract_env_vars(text: str) -> list:
    found = set()
    false_positives = {
        "API", "URL", "HTTP", "HTTPS", "TCP", "UDP", "SQL", "JSON", "XML",
        "HTML", "CSS", "JWT", "SSH", "SSL", "TLS", "DNS", "IP", "OS",
        "CLI", "GUI", "SDK", "README", "NOTE", "TODO", "WARNING", "ERROR",
        "INFO", "DEBUG", "TRUE", "FALSE", "NULL", "NONE",
    }
    for m in re.findall(r'\b([A-Z][A-Z0-9_]{2,})\b', text):
        if m not in false_positives and "_" in m:
            found.add(m)
    return sorted(found)


def run_baseline_regex(doc_snippet: str, live_state: dict) -> dict:
    """
    Runs Baseline 2 on a single sample.
    Returns dict with: drift_detected, root_cause, extracted_intent,
                       discrepancies, error
    """
    # Extract from docs
    ports    = extract_ports(doc_snippet)
    packages = extract_packages(doc_snippet)
    services = extract_services(doc_snippet)
    env_vars = extract_env_vars(doc_snippet)

    extracted_intent = {
        "required_ports":    ports,
        "required_packages": packages,
        "required_services": services,
        "required_env_vars": [{"name": v, "value": "*"} for v in env_vars],
    }

    # Compare against live state
    live_ports    = live_state.get("active_ports", [])
    live_packages = [p.lower() for p in live_state.get("installed_packages", [])]
    live_services = [s.lower() for s in live_state.get("running_services", [])]
    live_evnames  = [ev["name"].upper() for ev in live_state.get("active_env_vars", [])]

    discrepancies = []
    for p in ports:
        if p not in live_ports:
            discrepancies.append({"field": "ports", "expected": p, "actual": "not found"})
    for p in packages:
        if p.lower() not in live_packages:
            discrepancies.append({"field": "packages", "expected": p, "actual": "not installed"})
    for s in services:
        if s.lower() not in live_services:
            discrepancies.append({"field": "services", "expected": s, "actual": "not running"})
    for v in env_vars:
        if v.upper() not in live_evnames:
            discrepancies.append({"field": "env_vars", "expected": v, "actual": "not set"})

    drift = len(discrepancies) > 0
    # Regex has no causal reasoning — always says SYSTEM_FAULT
    root_cause = "SYSTEM_FAULT" if drift else "IN_SYNC"

    return {
        "drift_detected":   drift,
        "root_cause":       root_cause,
        "extracted_intent": extracted_intent,
        "discrepancies":    discrepancies,
        "error":            False,
    }


if __name__ == "__main__":
    with open("Dataset/Doc2State.json") as f:
        data = json.load(f)

    seen = set()
    correct = 0
    for s in data:
        cat = s["category"]
        result = run_baseline_regex(s["doc_snippet"], s["simulated_live_state"])
        gt_drift = "no drift" not in s["expected_reconciliation"].lower()
        if result["drift_detected"] == gt_drift:
            correct += 1
        if cat not in seen:
            seen.add(cat)
            print(f"\n=== {cat} (ID {s['id']}) ===")
            print(f"Doc: {s['doc_snippet'][:100]}")
            print(f"Extracted: {result['extracted_intent']}")
            print(f"Drift: {result['drift_detected']} (GT={gt_drift})")

    print(f"\nRegex baseline drift accuracy on full dataset: {correct}/100 = {correct}%")
