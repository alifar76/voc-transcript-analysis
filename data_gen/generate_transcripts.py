#!/usr/bin/env python3
"""
Generates a synthetic Voice-of-Customer (VOC) call transcript dataset for
demo purposes: fictional bank ("Meridian Bank"), fictional customers and
agents, ASR-quality-degraded phone transcripts across several lines of
business (LOBs), spread over the last N days.

Two intentional "stories" are baked into the data so the dashboards have
something real to show:
  1. A ~2-week spike in "Mobile app outage" complaints in Retail Banking,
     roughly two months before the end of the window.
  2. A steadily rising trend in business-opportunity signals (high-yield
     savings interest in Retail, business line-of-credit interest in Small
     Business Banking) over the final six weeks of the window.

Usage:
    python generate_transcripts.py --days 140 --seed 7 --output ../data/synthetic_transcripts.csv
"""

import argparse
import csv
import random
import sys
import uuid
from datetime import datetime, timedelta

from scenarios import LOBS, BANK_NAME, fill, _rand_name

LOB_WEIGHTS = {
    "Retail & Consumer Banking": 0.28,
    "Credit Cards": 0.20,
    "Fraud & Disputes": 0.15,
    "Mortgage & Home Lending": 0.14,
    "Auto Finance": 0.13,
    "Small Business Banking": 0.10,
}

AGENT_IDS = [f"AG-{i:03d}" for i in range(1, 19)]
KEY_MAP = {"complaint": "complaints", "opportunity": "opportunities", "neutral": "neutral"}

APP_OUTAGE_START_OFFSET = 63  # days-before-end window start
APP_OUTAGE_LEN = 13
OPPORTUNITY_TREND_WINDOW = 42

AGENT_GREETINGS = [
    "thank you for calling {bank} my name is {agent} how can i help you today",
    "{bank} customer care this is {agent} speaking how can i assist you",
    "thanks for holding this is {agent} with {bank} how can i help",
]

AGENT_ACK = {
    "complaint": [
        "i am really sorry to hear that let me pull up your account",
        "i understand how frustrating that must be let me take a look",
        "i apologize for the trouble let me see whats going on here",
    ],
    "opportunity": [
        "that sounds great let me pull up some information for you",
        "happy to help with that let me check what options are available",
        "sure thing let me look into that for you",
    ],
    "neutral": [
        "sure i can help you with that",
        "no problem let me take care of that for you",
        "okay give me just a moment to look that up",
    ],
}

AGENT_RESOLUTION = {
    "complaint": [
        "i am going to go ahead and escalate this to our specialist team and you should hear back within {days} business days",
        "i can go ahead and submit a refund request for you today",
        "let me file a formal complaint on your behalf so this gets looked at right away",
        "i am so sorry again i will make sure this gets fixed as quickly as possible",
    ],
    "opportunity": [
        "let me connect you with one of our specialists who can walk you through the details",
        "i can go ahead and get that process started for you right now if you would like",
        "i will send you some information and we can schedule a follow up call",
    ],
    "neutral": [
        "alright i have taken care of that for you",
        "thats all set on our end now",
        "great that update is complete",
    ],
}

CUSTOMER_CLOSING = {
    "complaint": [
        "okay i just hope this actually gets resolved this time",
        "alright thank you i guess we will see what happens",
        "fine but i am still not happy about this",
        "okay thank you for your help with this",
    ],
    "opportunity": [
        "great that sounds good thank you",
        "perfect i appreciate the help",
        "okay i will wait to hear back then",
    ],
    "neutral": [
        "okay thank you so much",
        "great appreciate it",
        "alright thanks bye",
    ],
}

AGENT_CLOSING = [
    "is there anything else i can help you with today",
    "thank you for calling {bank} have a great day",
    "we appreciate your business at {bank} take care",
]

DURATION_RANGE = {"complaint": (180, 600), "opportunity": (120, 420), "neutral": (60, 240)}


def pick_lob(rng):
    names, weights = zip(*LOB_WEIGHTS.items())
    return rng.choices(names, weights=weights, k=1)[0]


def scenario_type_for(lob_name, day_offset, rng):
    base_complaint, base_opportunity = 0.35, 0.20
    opportunity_boost = 0.0
    if lob_name in ("Retail & Consumer Banking", "Small Business Banking") and day_offset <= OPPORTUNITY_TREND_WINDOW:
        opportunity_boost = 0.25 * (1 - day_offset / OPPORTUNITY_TREND_WINDOW)
    complaint = base_complaint
    opportunity = base_opportunity + opportunity_boost
    neutral = max(0.05, 1 - complaint - opportunity)
    total = complaint + opportunity + neutral
    weights = [complaint / total, opportunity / total, neutral / total]
    return rng.choices(["complaint", "opportunity", "neutral"], weights=weights, k=1)[0]


def pick_scenario(lob_name, scenario_type, day_offset, rng):
    bucket = LOBS[lob_name][KEY_MAP[scenario_type]]

    if (
        lob_name == "Retail & Consumer Banking"
        and scenario_type == "complaint"
        and APP_OUTAGE_START_OFFSET <= day_offset <= APP_OUTAGE_START_OFFSET + APP_OUTAGE_LEN
        and rng.random() < 0.65
    ):
        for s in bucket:
            if s["category"] == "Mobile app outage":
                return s

    if scenario_type == "opportunity" and day_offset <= OPPORTUNITY_TREND_WINDOW:
        target_type = {
            "Retail & Consumer Banking": "High-yield savings interest",
            "Small Business Banking": "Business line of credit",
        }.get(lob_name)
        if target_type:
            boost_prob = 0.55 * (1 - day_offset / OPPORTUNITY_TREND_WINDOW)
            if rng.random() < boost_prob:
                for s in bucket:
                    if s["type"] == target_type:
                        return s

    return rng.choice(bucket)


def build_dialogue(scenario_type, scenario, rng):
    agent = _rand_name(rng)
    lines = []
    greeting = rng.choice(AGENT_GREETINGS).format(bank=BANK_NAME, agent=agent)
    lines.append(("AGENT", greeting))
    lines.append(("CUST", fill(scenario["open"], rng)))
    lines.append(("AGENT", rng.choice(AGENT_ACK[scenario_type])))
    if "detail" in scenario:
        lines.append(("CUST", fill(scenario["detail"], rng)))
    lines.append(("AGENT", fill(rng.choice(AGENT_RESOLUTION[scenario_type]), rng)))
    lines.append(("CUST", rng.choice(CUSTOMER_CLOSING[scenario_type])))
    lines.append(("AGENT", rng.choice(AGENT_CLOSING).format(bank=BANK_NAME)))
    return agent, lines


def render_transcript(lines, rng):
    from noise import inject_noise

    rendered = []
    for speaker, text in lines:
        severity = 0.35 if speaker == "AGENT" else 0.75
        noisy = inject_noise(text, severity, rng)
        rendered.append(f"{speaker}: {noisy}")
    return "\n".join(rendered)


def render_clean_reference(lines):
    """Pre-noise dialogue text, kept only as a reference for validating how well
    downstream ASR-cleanup/extraction reconstructs the original meaning."""
    return "\n".join(f"{speaker}: {text.capitalize()}." for speaker, text in lines)


def business_hour(rng):
    hour = rng.choices(
        population=list(range(8, 20)),
        weights=[3, 5, 7, 8, 6, 4, 5, 8, 9, 7, 5, 3],
        k=1,
    )[0]
    return hour, rng.randint(0, 59), rng.randint(0, 59)


def calls_for_day(dt, rng):
    if dt.weekday() >= 5:
        return rng.randint(2, 6)
    return rng.randint(6, 13)


def generate(days, seed, output_path):
    rng = random.Random(seed)
    end_date = datetime.now().replace(microsecond=0)
    rows = []

    for day_offset in range(days, -1, -1):
        day = end_date - timedelta(days=day_offset)
        n_calls = calls_for_day(day, rng)
        for _ in range(n_calls):
            lob_name = pick_lob(rng)
            scenario_type = scenario_type_for(lob_name, day_offset, rng)
            scenario = pick_scenario(lob_name, scenario_type, day_offset, rng)
            agent_name = rng.choice(AGENT_IDS)
            _, lines = build_dialogue(scenario_type, scenario, rng)
            transcript = render_transcript(lines, rng)
            clean_reference = render_clean_reference(lines)

            hour, minute, second = business_hour(rng)
            call_dt = day.replace(hour=hour, minute=minute, second=second)
            lo, hi = DURATION_RANGE[scenario_type]

            rows.append(
                {
                    "call_id": f"CALL-{uuid.uuid4().hex[:10].upper()}",
                    "call_datetime": call_dt.isoformat(),
                    "lob": lob_name,
                    "lob_code": LOBS[lob_name]["code"],
                    "agent_id": agent_name,
                    "customer_id": f"CUST-{rng.randint(100000, 999999)}",
                    "channel": "Phone",
                    "duration_sec": rng.randint(lo, hi),
                    "scenario_type": scenario_type,
                    "scenario_key": scenario.get("category") or scenario.get("type") or scenario.get("topic"),
                    "raw_transcript": transcript,
                    "clean_transcript_ref": clean_reference,
                }
            )

    rows.sort(key=lambda r: r["call_datetime"])

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=140, help="How many days of history to generate")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="../data/synthetic_transcripts.csv")
    args = parser.parse_args()

    count = generate(args.days, args.seed, args.output)
    print(f"Wrote {count} synthetic calls to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
