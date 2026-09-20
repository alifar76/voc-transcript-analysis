import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data_gen"))

import generate_transcripts as gt  # noqa: E402


def test_generate_produces_expected_columns(tmp_path):
    out = tmp_path / "calls.csv"
    count = gt.generate(days=20, seed=1, output_path=str(out))

    import csv

    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == count
    assert count > 0
    expected_cols = {
        "call_id",
        "call_datetime",
        "lob",
        "lob_code",
        "agent_id",
        "customer_id",
        "channel",
        "duration_sec",
        "scenario_type",
        "scenario_key",
        "raw_transcript",
        "clean_transcript_ref",
    }
    assert expected_cols.issubset(rows[0].keys())
    assert all(r["scenario_type"] in {"complaint", "opportunity", "neutral"} for r in rows)
    assert all(r["lob"] in gt.LOB_WEIGHTS for r in rows)


def test_generate_is_deterministic_for_a_given_seed(tmp_path):
    # call_id is a fresh uuid4 each run by design (not derived from the seeded
    # rng), so determinism is checked on everything else.
    import csv

    out1 = tmp_path / "a.csv"
    out2 = tmp_path / "b.csv"
    gt.generate(days=10, seed=42, output_path=str(out1))
    gt.generate(days=10, seed=42, output_path=str(out2))

    def rows_without_call_id(path):
        with open(path, newline="", encoding="utf-8") as f:
            return [{k: v for k, v in row.items() if k != "call_id"} for row in csv.DictReader(f)]

    assert rows_without_call_id(out1) == rows_without_call_id(out2)
