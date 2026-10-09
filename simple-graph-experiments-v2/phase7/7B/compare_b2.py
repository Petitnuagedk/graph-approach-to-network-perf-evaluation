"""Byte-compare the post-change B2 legacy regression with the B0 golden."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BEFORE = HERE / "legacy_before"
AFTER = HERE / "legacy_after"
RESULT_TIMING_COLUMNS = {"wall_time_s", "cpu_time_s"}
SEMANTIC_CONFIG_FIELDS = (
    "frames_csv", "routing", "protocols", "flows", "seed", "data_rate",
    "packet_size_bytes", "loss_threshold_db", "interpolate", "default_loss_db",
    "tx_power_dbm", "link_up_loss_db", "link_down_loss_db", "fps",
    "frame_duration_s", "warmup_requested_s", "warmup_effective_s", "warmup_mode",
    "static_oracle_mode",
)
DETERMINISTIC_SUFFIXES = (
    "packets_{protocol}.csv",
    "routes_{protocol}.txt",
    "times_{protocol}.csv",
    "oracle_diagnostics_{protocol}.csv",
    "packet_diagnostics_{protocol}.csv",
)
PROTOCOLS = ("olsr", "aodv", "static")
EXPECTED_TRACE_SHA256 = "282feae63d0822c096bc427b9e7fc8705447509d352a72a78761805acd81f603"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def result_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = [field for field in (reader.fieldnames or [])
                  if field not in RESULT_TIMING_COLUMNS]
        data = [[row[field] for field in fields] for row in reader]
    return fields, data


def count_trace_matrices(path: Path) -> int:
    with path.open(encoding="utf-8") as stream:
        lines = stream.readlines()[1:]
    count = 0
    in_matrix = False
    for line in lines:
        if line.strip():
            if not in_matrix:
                count += 1
                in_matrix = True
        else:
            in_matrix = False
    return count


def main() -> int:
    mismatches: list[str] = []
    file_comparisons: list[dict[str, object]] = []
    for protocol in PROTOCOLS:
        for template in DETERMINISTIC_SUFFIXES:
            name = template.format(protocol=protocol)
            left, right = BEFORE / name, AFTER / name
            exact = left.is_file() and right.is_file() and left.read_bytes() == right.read_bytes()
            file_comparisons.append({
                "file": name,
                "byte_identical": exact,
                "before_sha256": sha256(left) if left.is_file() else None,
                "after_sha256": sha256(right) if right.is_file() else None,
            })
            if not exact:
                mismatches.append(name)

    before_fields, before_data = result_rows(BEFORE / "trace_replay_results.csv")
    after_fields, after_data = result_rows(AFTER / "trace_replay_results.csv")
    result_identical = before_fields == after_fields and before_data == after_data
    if not result_identical:
        mismatches.append("trace_replay_results.csv (excluding wall_time_s,cpu_time_s)")

    before_config = json.loads((BEFORE / "config.json").read_text(encoding="utf-8"))
    after_config = json.loads((AFTER / "config.json").read_text(encoding="utf-8"))
    settings_before = {key: before_config[key] for key in SEMANTIC_CONFIG_FIELDS}
    settings_after = {key: after_config[key] for key in SEMANTIC_CONFIG_FIELDS}
    config_settings_identical = settings_before == settings_after
    if not config_settings_identical:
        mismatches.append("config.json stable run settings")
    args_before = before_config["run_args"].replace(before_config["out_dir"], "<OUT_DIR>")
    args_after = args_before.replace("--channelProfile=legacy ", "")
    args_identical = (args_before == args_after
                      and after_config.get("channel_profile") == "legacy")
    if not args_identical:
        mismatches.append("run_args except outDir")

    trace_hash = sha256(Path(after_config["frames_csv"]))
    trace_hash_match = trace_hash == EXPECTED_TRACE_SHA256 == sha256(Path(before_config["frames_csv"]))
    if not trace_hash_match:
        mismatches.append("trace SHA-256")
    applied = [int(row["frame_apply_calls"]) for row in csv.DictReader(
        (AFTER / "trace_replay_results.csv").open(newline="", encoding="utf-8"))]
    source_frames = count_trace_matrices(Path(after_config["frames_csv"]))
    expected_applied = source_frames + math.ceil(
        float(after_config["warmup_effective_s"]) * float(after_config["fps"]))
    console = (AFTER / "console.log").read_text(encoding="utf-8")
    frame_count_match = (source_frames == 60
                         and expected_applied == 105
                         and "Loaded 105 frames" in console
                         and applied == [105, 105, 105])
    if not frame_count_match:
        mismatches.append("frame/warm-up accounting")
    legacy_interpolation = after_config["interpolate"] is True
    if not legacy_interpolation:
        mismatches.append("resolved interpolation is not true")

    source_hashes = {
        "before": before_config.get("source_hashes_sha256", {}),
        "after_graph_run_cc": sha256(Path("/home/hledirach/Documents/sp1-sp2/scratch/graph-run.cc")),
    }
    summary = {
        "gate": "B2 legacy deterministic regression",
        "invocations": 1,
        "protocol_variants": 3,
        "trace_sha256": trace_hash,
        "trace_sha256_match": trace_hash_match,
        "frame_warmup_accounting_pass": frame_count_match,
        "legacy_interpolation_true": legacy_interpolation,
        "run_args_identical_except_out_dir": args_identical,
        "stable_config_settings_identical": config_settings_identical,
        "result_csv_identical_excluding_only_wall_cpu_time": result_identical,
        "deterministic_files": file_comparisons,
        "source_hashes_before_after": source_hashes,
        "source_hash_changes_expected_due_to_post_change_build": (
            source_hashes["before"].get("graph_run_cc") != source_hashes["after_graph_run_cc"]
        ),
        "mismatches": mismatches,
        "b2_pass": not mismatches,
    }
    out = HERE / "B2_comparison.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["b2_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
