"""Generates per-CI metric time series, one CSV per CI, for a subset of CIs. A portion are
deliberately shaped as slow-degradation curves (memory creep, rising latency) — the tuning
workflow's verification criterion is "sustained improvement across a window", so scenarios need
a real trend to show recovering, not a single before/after point. Fully synthetic, fixed seed.

    python data_gen/metrics.py

Writes:
    data/metrics/{ci_id}.csv          one per sampled CI: timestamp,cpu_pct,memory_pct,latency_ms,error_rate
    data/metrics_index.json           which CIs got a series, and which are degradation curves
"""
import csv
import json
import os
import random

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
METRICS_DIR = os.path.join(DATA_DIR, "metrics")

SEED = 20260807
random.seed(SEED)

CI_SAMPLE_SIZE = 40          # not every CI needs a metric series for the demo
POINTS_PER_SERIES = 100      # ~24h at ~15min intervals
DEGRADATION_SHARE = 0.25     # of the sampled CIs, how many get a deliberate slow-degradation curve


def _load_cis() -> list[dict]:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        return json.load(f)["cis"]


def _stable_series(n: int) -> list[dict]:
    """Normal steady-state metrics with small random jitter — nothing trending."""
    base_cpu, base_mem, base_lat = random.uniform(20, 50), random.uniform(30, 60), random.uniform(50, 150)
    return [
        {
            "cpu_pct": round(max(0, min(100, base_cpu + random.uniform(-5, 5))), 1),
            "memory_pct": round(max(0, min(100, base_mem + random.uniform(-4, 4))), 1),
            "latency_ms": round(max(1, base_lat + random.uniform(-15, 15)), 1),
            "error_rate": round(max(0, random.uniform(0, 0.5)), 2),
        }
        for _ in range(n)
    ]


def _degradation_series(n: int) -> list[dict]:
    """Slow, monotonic-ish creep in memory/latency over the window — the shape a tuning workflow
    is meant to catch and later show *recovering* after a fix is applied."""
    base_mem, base_lat = random.uniform(35, 45), random.uniform(80, 120)
    points = []
    for i in range(n):
        progress = i / max(1, n - 1)
        mem = base_mem + progress * random.uniform(35, 50) + random.uniform(-2, 2)
        lat = base_lat + progress * random.uniform(300, 600) + random.uniform(-10, 10)
        points.append({
            "cpu_pct": round(max(0, min(100, random.uniform(25, 55))), 1),
            "memory_pct": round(max(0, min(100, mem)), 1),
            "latency_ms": round(max(1, lat), 1),
            "error_rate": round(max(0, random.uniform(0, 1.5) * progress), 2),
        })
    return points


def generate_metrics(cis: list[dict]) -> dict:
    sampled = random.sample(cis, min(CI_SAMPLE_SIZE, len(cis)))
    degradation_count = round(len(sampled) * DEGRADATION_SHARE)
    degradation_ids = {ci["id"] for ci in random.sample(sampled, degradation_count)}

    os.makedirs(METRICS_DIR, exist_ok=True)
    index = {"sampled_ci_ids": [ci["id"] for ci in sampled], "degradation_ci_ids": sorted(degradation_ids)}

    for ci in sampled:
        series = _degradation_series(POINTS_PER_SERIES) if ci["id"] in degradation_ids else _stable_series(POINTS_PER_SERIES)
        path = os.path.join(METRICS_DIR, f"{ci['id']}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_offset_min", "cpu_pct", "memory_pct", "latency_ms", "error_rate"])
            for i, point in enumerate(series):
                writer.writerow([i * 15, point["cpu_pct"], point["memory_pct"], point["latency_ms"], point["error_rate"]])

    return index


def main() -> None:
    cis = _load_cis()
    index = generate_metrics(cis)
    with open(os.path.join(DATA_DIR, "metrics_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"metrics/: {len(index['sampled_ci_ids'])} CI series written, {len(index['degradation_ci_ids'])} are degradation curves")


if __name__ == "__main__":
    main()

    with open(os.path.join(DATA_DIR, "metrics_index.json"), encoding="utf-8") as f:
        index = json.load(f)
    assert len(index["sampled_ci_ids"]) == CI_SAMPLE_SIZE
    assert len(index["degradation_ci_ids"]) >= 1, "no degradation curves generated — tuning scenarios need at least one"
    for ci_id in index["sampled_ci_ids"]:
        path = os.path.join(METRICS_DIR, f"{ci_id}.csv")
        assert os.path.exists(path), f"missing metrics file for {ci_id}"
        with open(path, encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == POINTS_PER_SERIES + 1, f"{ci_id}.csv has {len(rows)-1} data rows, expected {POINTS_PER_SERIES}"
    # spot-check: a degradation series should end with materially higher memory_pct than it started
    sample_id = index["degradation_ci_ids"][0]
    with open(os.path.join(METRICS_DIR, f"{sample_id}.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    start_mem, end_mem = float(rows[0]["memory_pct"]), float(rows[-1]["memory_pct"])
    assert end_mem > start_mem + 15, f"{sample_id} degradation curve too flat: {start_mem} -> {end_mem}"
    print("\nSELF-TEST PASSED: file count, row counts, and degradation curve shape all valid.")
