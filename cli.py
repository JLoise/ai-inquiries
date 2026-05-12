#!/usr/bin/env python3
"""
cli.py — Command-line interface for the SMC Enquiry Processor.

Usage:
    python cli.py                        # interactive prompt
    python cli.py "Your enquiry text"    # single enquiry from argument
    echo "enquiry text" | python cli.py  # pipe from stdin
"""

import sys
import json
from app import analyse_enquiry

PRIORITY_COLOURS = {
    "urgent": "\033[91m",   # red
    "high":   "\033[93m",   # yellow
    "medium": "\033[94m",   # blue
    "low":    "\033[92m",   # green
}
RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"


def print_result(r: dict) -> None:
    prio  = r.get("priority", "low")
    colour = PRIORITY_COLOURS.get(prio, "")
    conf  = int(r.get("confidence", 0) * 100)

    print()
    print("=" * 64)
    print(f"{BOLD}  SMC Enquiry Analysis{RESET}")
    print("=" * 64)
    print(f"  Category  : {BOLD}{r.get('category_label','?')}{RESET}")
    print(f"  Priority  : {colour}{BOLD}{prio.upper()}{RESET}")
    print(f"  Confidence: {conf}%  — {DIM}{r.get('confidence_reason','')}{RESET}")
    print(f"  Sentiment : {r.get('sentiment','?')}")
    print(f"  Route to  : {r.get('team','?')}  (SLA: {r.get('sla','?')})")
    print(f"  Timestamp : {r.get('timestamp','?')}")

    if r.get("error"):
        print(f"\n  ⚠  Error: {r['error']}")

    print()
    print(f"  {BOLD}Summary{RESET}")
    print(f"  {r.get('summary','—')}")

    kp = r.get("key_points", [])
    if kp:
        print()
        print(f"  {BOLD}Key Points{RESET}")
        for pt in kp:
            print(f"    ▸ {pt}")

    print()
    print(f"  {BOLD}Recommended Action{RESET}")
    print(f"  → {r.get('recommended_action','—')}")

    if r.get("escalate"):
        print()
        print(f"  🚨 {BOLD}ESCALATION FLAGGED{RESET}: {r.get('escalation_reason','')}")

    print()
    print(f"  {BOLD}Draft Response{RESET}")
    print("-" * 64)
    for line in r.get("suggested_response", "").split("\n"):
        print(f"  {line}")
    print("-" * 64)
    print()


def main():
    # 1) argument supplied directly
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        result = analyse_enquiry(text)
        print_result(result)
        return

    # 2) piped via stdin
    if not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        result = analyse_enquiry(text)
        print_result(result)
        return

    # 3) interactive mode
    print(f"\n{BOLD}SMC Enquiry Processor — Interactive Mode{RESET}")
    print("Type your enquiry and press Enter twice to submit. Ctrl-C to quit.\n")

    while True:
        lines = []
        try:
            print("Enquiry:")
            while True:
                line = input()
                if line == "" and lines:
                    break
                lines.append(line)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        text = "\n".join(lines).strip()
        if not text:
            continue

        result = analyse_enquiry(text)
        print_result(result)


if __name__ == "__main__":
    main()
