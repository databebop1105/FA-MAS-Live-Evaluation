from __future__ import annotations

import argparse, json, platform, subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from scipy.stats import binomtest
import matplotlib.pyplot as plt
from .core import run_trial

ABLATIONS = ["no_semantic_contracts", "no_compensation", "fixed_rules", "no_provenance", "no_substitution"]

def markdown_table(frame, digits=3):
    cols=list(frame.columns)
    def fmt(v):
        return f"{v:.{digits}f}" if isinstance(v,(float,np.floating)) else str(v)
    rows=["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"]*len(cols)) + " |"]
    rows += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in frame.itertuples(index=False,name=None)]
    return "\n".join(rows)


def bootstrap_diff(a, b, rng, n=3000):
    d = np.asarray(a) - np.asarray(b)
    draws = rng.choice(d, (n, len(d)), replace=True).mean(axis=1)
    return float(d.mean()), float(np.quantile(draws, .025)), float(np.quantile(draws, .975))

def holm_adjust(pvalues):
    p=np.asarray(pvalues,float); order=np.argsort(p); out=np.empty(len(p)); running=0.0
    for rank,idx in enumerate(order):
        running=max(running,(len(p)-rank)*p[idx]); out[idx]=min(1.0,running)
    return out


def exact_mcnemar(a, b):
    """Two-sided exact McNemar test for paired binary outcomes."""
    a = np.asarray(a, dtype=int)
    b = np.asarray(b, dtype=int)
    n10 = int(np.sum((a == 1) & (b == 0)))
    n01 = int(np.sum((a == 0) & (b == 1)))
    discordant = n10 + n01
    if discordant == 0:
        return 1.0, n10, n01
    p = float(binomtest(min(n10, n01), discordant, 0.5, alternative="two-sided").pvalue)
    return p, n10, n01


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/preregistered.yaml")
    args = ap.parse_args()
    cfg_path = Path(args.config)
    cfg = yaml.safe_load(cfg_path.read_text())
    out = Path("results"); out.mkdir(exist_ok=True)
    rows=[]
    for domain in cfg["domains"]:
      for fault in cfg["faults"]:
       levels = [0.0] if fault == "none" else cfg["intensities"]
       for intensity in levels:
        for rep in range(cfg["repetitions"]):
         paired_seed = cfg["seed"] + rep + 1000*cfg["faults"].index(fault) + 10000*cfg["domains"].index(domain) + int(intensity*100)*100000
         for baseline in cfg["baselines"]:
          rows.append(run_trial(domain,fault,intensity,baseline,paired_seed,cfg["slo"],cfg["utility_weights"]))
         if fault != "none":
          for abl in ABLATIONS:
           rows.append(run_trial(domain,fault,intensity,"fa_mas",paired_seed,cfg["slo"],cfg["utility_weights"],abl))
    df=pd.DataFrame(rows); df.to_csv(out/"runs.csv",index=False)
    full=df[df.ablation=="full"]
    metrics=["task_success","acceptable_outcome","safe_termination","slo_attained","unsafe_side_effect","latency_ms","cost_units","detected","localized"]
    summary=full.groupby(["baseline","domain","fault","intensity"])[metrics].agg(["mean","std","count"])
    summary.to_csv(out/"summary.csv")
    rng=np.random.default_rng(cfg["seed"])
    comparisons=[]
    keys=["domain","fault","intensity","seed"]
    f=full[full.baseline=="fa_mas"].set_index(keys)
    for baseline in [b for b in cfg["baselines"] if b!="fa_mas"]:
      b=full[full.baseline==baseline].set_index(keys)
      common=f.index.intersection(b.index)
      for metric in cfg["primary_outcomes"]:
       effect,lo,hi=bootstrap_diff(f.loc[common,metric],b.loc[common,metric],rng)
       p, n10, n01 = exact_mcnemar(f.loc[common,metric], b.loc[common,metric])
       comparisons.append({"baseline":baseline,"metric":metric,"effect_fa_mas_minus_baseline":effect,"ci_low":lo,"ci_high":hi,"mcnemar_exact_p":p,"fa_only_success":n10,"baseline_only_success":n01,"n_pairs":len(common)})
    comp=pd.DataFrame(comparisons); comp.to_csv(out/"paired_comparisons.csv",index=False)
    comp["holm_p"] = comp.groupby("metric")["mcnemar_exact_p"].transform(lambda x: holm_adjust(x.to_numpy()))
    comp.to_csv(out/"paired_comparisons.csv",index=False)
    abl=df[(df.baseline=="fa_mas") & (df.fault!="none")].groupby("ablation")[metrics].mean().reset_index()
    abl.to_csv(out/"ablations.csv",index=False)
    agg=full.groupby("baseline").agg(success=("task_success","mean"),acceptable=("acceptable_outcome","mean"),safe_termination=("safe_termination","mean"),slo=("slo_attained","mean"),unsafe=("unsafe_side_effect","mean"),latency=("latency_ms","mean"),cost=("cost_units","mean")).reset_index()
    agg.to_csv(out/"headline.csv",index=False)
    fig,ax=plt.subplots(figsize=(7,4)); ax.scatter(agg.cost,agg.success)
    for _,r in agg.iterrows(): ax.annotate(r.baseline,(r.cost,r.success),xytext=(4,3),textcoords="offset points",fontsize=8)
    ax.set(xlabel="Mean cost units",ylabel="Task success",title="Reliability-cost frontier"); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(out/"reliability_cost_frontier.png",dpi=180); plt.close(fig)
    manifest={"config":cfg,"python":platform.python_version(),"platform":platform.platform(),"rows":len(df),"note":"Controlled stochastic simulator; no live LLM/API calls."}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2))
    lines=["# FA-MAS prespecified simulator report","","**Evidence boundary:** controlled stochastic service simulation; not live LLM or production-service evidence.","",f"Run-level observations: **{len(df):,}**.","","## Headline aggregates","",markdown_table(agg),"","## Paired primary comparisons","",markdown_table(comp,4),"","## FA-MAS ablations","",markdown_table(abl),"",f"Primary outcomes and analysis were loaded from `{cfg_path.as_posix()}`. Seeds are paired across systems. Confidence intervals are paired bootstrap 95% intervals; p-values are two-sided exact McNemar tests for paired binary outcomes with Holm correction within each metric family."]
    (out/"REPORT.md").write_text("\n".join(lines))
    print(agg.to_string(index=False)); print(f"\nWrote {len(df)} rows to {out.resolve()}")

if __name__ == "__main__": main()
