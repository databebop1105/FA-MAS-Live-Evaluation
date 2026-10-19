from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .experiment import exact_mcnemar, holm_adjust


PRIMARY = ("task_success", "acceptable_outcome", "unsafe_side_effect")


def cluster_bootstrap(values: pd.DataFrame, cluster: str, rng: np.random.Generator,
                      n: int = 5000) -> tuple[float, float, float]:
    clusters = values[cluster].unique()
    effects = []
    for _ in range(n):
        sampled = rng.choice(clusters, len(clusters), replace=True)
        effects.append(np.mean([values.loc[values[cluster] == c, "difference"].mean() for c in sampled]))
    effect = float(values.groupby(cluster).difference.mean().mean())
    return effect, float(np.quantile(effects, .025)), float(np.quantile(effects, .975))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default="results/live_tier/live_runs.jsonl")
    parser.add_argument("--output", default="results/live_tier")
    args = parser.parse_args()
    records = [json.loads(line) for line in Path(args.runs).read_text().splitlines() if line.strip()]
    if not records or {r.get("evidence_class") for r in records} != {"live"}:
        raise RuntimeError("Analysis accepts only completed live-model rows")
    df = pd.DataFrame(records)
    keys = ["task_id", "fault", "seed", "model_id", "temperature"]
    if df.duplicated(keys + ["policy"]).any(): raise RuntimeError("Duplicate live experiment cells")
    expected = len(df[keys].drop_duplicates()) * df.policy.nunique()
    if len(df) != expected: raise RuntimeError("Incomplete policy matrix; retain failures as labeled rows")
    summary = df.groupby(["policy", "model_id", "temperature"])[list(PRIMARY) + ["latency_ms", "total_tokens"]].mean().reset_index()
    fa = df[df.policy == "fa_mas"].set_index(keys)
    comparisons = []
    rng = np.random.default_rng(20260922)
    for policy in sorted(set(df.policy) - {"fa_mas"}):
        base = df[df.policy == policy].set_index(keys)
        common = fa.index.intersection(base.index)
        if len(common) != len(fa) or len(common) != len(base): raise RuntimeError("Unpaired policy rows")
        for metric in PRIMARY:
            frame = pd.DataFrame({"difference": fa.loc[common, metric].to_numpy() - base.loc[common, metric].to_numpy(),
                                  "task_id": [x[0] for x in common]})
            effect, lo, hi = cluster_bootstrap(frame, "task_id", rng)
            p, n10, n01 = exact_mcnemar(fa.loc[common, metric], base.loc[common, metric])
            comparisons.append({"baseline": policy, "metric": metric, "effect": effect, "ci_low": lo,
                                "ci_high": hi, "mcnemar_exact_p": p, "fa_only_success": n10,
                                "baseline_only_success": n01, "n_pairs": len(common)})
    comp = pd.DataFrame(comparisons)
    comp["holm_p"] = comp.groupby("metric")["mcnemar_exact_p"].transform(lambda x: holm_adjust(x.to_numpy()))
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "live_summary.csv", index=False)
    comp.to_csv(out / "live_paired_comparisons.csv", index=False)
    manifest = {"evidence_class": "live", "rows": len(df), "complete_matrix": True,
                "models": sorted(df.model_id.unique()), "tasks": int(df.task_id.nunique())}
    (out / "live_analysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__": main()
