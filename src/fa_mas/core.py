from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List
import random


class Fault(str, Enum):
    NONE = "none"
    INFRA = "infrastructure"
    PROTOCOL = "protocol"
    SEMANTIC = "semantic"
    AGENT = "agent"
    COORDINATION = "coordination"
    STATEFUL = "stateful"
    SECURITY = "security"


@dataclass(frozen=True)
class Contract:
    service: str
    idempotency: str
    compensation: bool
    scopes: frozenset[str]
    latency_p95_ms: int
    cost: float
    alternatives: tuple[str, ...] = ()


@dataclass
class State:
    completed: List[str] = field(default_factory=list)
    ledger: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    cost: float = 0.0
    attempts: int = 0
    recovery_attempts: int = 0
    detected: bool = False
    localized: bool = False
    compensated: bool = False
    unauthorized_attempt: bool = False
    duplicate_side_effect: bool = False
    invariant_violation: bool = False


WORKFLOWS = {
    "refund": [
        Contract("account_lookup", "read", False, frozenset({"account:read"}), 120, 1.0, ("account_cache",)),
        Contract("policy_check", "read", False, frozenset({"policy:read"}), 180, 1.2, ("policy_replica",)),
        Contract("refund", "idempotent_write", True, frozenset({"refund:write"}), 350, 3.2, ("refund_backup",)),
        Contract("notify", "idempotent_write", False, frozenset({"notify:write"}), 100, 0.6, ("notify_backup",)),
    ],
    "travel": [
        Contract("search", "read", False, frozenset({"travel:read"}), 260, 1.4, ("search_backup",)),
        Contract("reserve", "non_idempotent_write", True, frozenset({"booking:write"}), 420, 3.5, ("reserve_backup",)),
        Contract("pay", "idempotent_write", True, frozenset({"payment:write"}), 390, 4.0, ("pay_backup",)),
        Contract("confirm", "read", False, frozenset({"booking:read"}), 160, 0.8, ("confirm_backup",)),
    ],
    "incident": [
        Contract("telemetry", "read", False, frozenset({"ops:read"}), 220, 1.3, ("telemetry_replica",)),
        Contract("localize", "read", False, frozenset({"ops:read"}), 260, 1.8, ("localize_backup",)),
        Contract("remediate", "idempotent_write", True, frozenset({"ops:write"}), 380, 3.6, ("remediate_backup",)),
        Contract("validate", "read", False, frozenset({"ops:read"}), 190, 1.0, ("validate_backup",)),
    ],
}


POLICIES = {
    "static": dict(detect=.00, localize=.00, retry=0, substitute=False, replan=False, contracts=False, compensate=False, security=False),
    "retry": dict(detect=.58, localize=.50, retry=2, substitute=False, replan=False, contracts=False, compensate=False, security=False),
    "react": dict(detect=.68, localize=.58, retry=1, substitute=False, replan=True, contracts=False, compensate=False, security=False),
    "replan": dict(detect=.72, localize=.62, retry=0, substitute=True, replan=True, contracts=False, compensate=False, security=False),
    "self_heal": dict(detect=.82, localize=.76, retry=1, substitute=True, replan=True, contracts=False, compensate=False, security=False),
    "unconstrained": dict(detect=.80, localize=.72, retry=1, substitute=True, replan=True, contracts=False, compensate=False, security=False),
    "fa_mas": dict(detect=.93, localize=.90, retry=1, substitute=True, replan=True, contracts=True, compensate=True, security=True),
}


FAULT_DETECTABILITY = {
    Fault.INFRA: .98, Fault.PROTOCOL: .96, Fault.SEMANTIC: .72, Fault.AGENT: .76,
    Fault.COORDINATION: .70, Fault.STATEFUL: .62, Fault.SECURITY: .90,
}


def _fault_hits(rng: random.Random, intensity: float) -> bool:
    return rng.random() < intensity


def run_trial(domain: str, fault: str, intensity: float, baseline: str, seed: int,
              slo: dict, weights: dict, ablation: str = "full", *,
              policy_override: dict | None = None, detection_bonus: bool = True,
              selection: str = "utility", strict_terminal: bool = False,
              recovery_semantics: str = "legacy") -> dict:
    if recovery_semantics not in {"legacy", "effect_aware"}:
        raise ValueError("Unknown recovery semantics")
    rng = random.Random(seed)
    policy = dict(POLICIES[baseline])
    if policy_override is not None: policy.update(policy_override)
    if baseline == "fa_mas":
        if ablation == "no_semantic_contracts": policy["contracts"] = False
        if ablation == "no_compensation": policy["compensate"] = False
        if ablation == "fixed_rules": policy["substitute"] = False
        if ablation == "no_provenance": policy["localize"] -= .18
        if ablation == "no_substitution": policy["substitute"] = False
    st = State()
    injected = Fault(fault)
    failure_step = rng.randrange(len(WORKFLOWS[domain])) if injected != Fault.NONE else -1
    recovered = False
    abstained = False
    for idx, contract in enumerate(WORKFLOWS[domain]):
        st.attempts += 1
        base_latency = rng.lognormvariate(4.65, .18) + contract.latency_p95_ms * .35
        st.latency_ms += base_latency
        st.cost += contract.cost
        active = idx == failure_step and _fault_hits(rng, intensity)
        if not active:
            st.completed.append(contract.service)
            if "write" in contract.idempotency: st.ledger[contract.service] = 1
            continue

        if injected == Fault.STATEFUL and "write" in contract.idempotency:
            st.ledger[contract.service] = 1
        detect_p = policy["detect"] * FAULT_DETECTABILITY[injected]
        if detection_bonus and policy["contracts"] and injected in {Fault.PROTOCOL, Fault.SEMANTIC, Fault.STATEFUL, Fault.SECURITY}:
            detect_p = min(.995, detect_p + .16)
        st.detected = rng.random() < detect_p
        st.localized = st.detected and rng.random() < policy["localize"]
        if injected == Fault.SECURITY and policy["security"]:
            abstained = True
            recovered = True
            break
        if recovery_semantics == "effect_aware" and injected == Fault.SECURITY:
            # Detection does not make a forbidden invocation authorized.
            st.unauthorized_attempt = True
        if not st.detected:
            st.invariant_violation = injected in {Fault.SEMANTIC, Fault.AGENT, Fault.COORDINATION, Fault.STATEFUL, Fault.SECURITY}
            st.unauthorized_attempt = injected == Fault.SECURITY
            if injected == Fault.STATEFUL and "write" in contract.idempotency:
                st.duplicate_side_effect = True
                st.ledger[contract.service] = 2
            break

        candidates = []
        if policy["retry"]: candidates.append(("retry", .60, base_latency, contract.cost, .55 if injected == Fault.STATEFUL else .10))
        if policy["substitute"] and contract.alternatives: candidates.append(("substitute", .78, base_latency * 1.25, contract.cost * 1.15, .14))
        if policy["replan"]: candidates.append(("replan", .70, base_latency * 1.7, contract.cost * 1.55, .18))
        # Compensation is meaningful only for an observed/uncertain existing
        # effect. Historical mode is preserved for exact evidence replay.
        needs_compensation = injected == Fault.STATEFUL and st.ledger.get(contract.service, 0) > 0
        if policy["compensate"] and contract.compensation and (recovery_semantics == "legacy" or needs_compensation):
            candidates.append(("compensate", .88, base_latency * .75, contract.cost * .6, .05))
        if not candidates: break
        if policy["contracts"] or recovery_semantics == "effect_aware":
            feasible = [c for c in candidates if st.attempts < slo["max_attempts"] and st.latency_ms + c[2] <= slo["latency_ms"] and st.cost + c[3] <= slo["cost_units"]]
            if not feasible:
                abstained = True
                break
            candidates = feasible
            if selection == "first": action = candidates[0]
            elif selection == "frontier":
                from .frontier import Candidate, select_frontier
                action = select_frontier([Candidate(*c) for c in candidates], weights).as_tuple()
            else: action = max(candidates, key=lambda c: c[1] - weights["latency"]*c[2] - weights["cost"]*c[3] - weights["risk"]*c[4])
        else:
            action = candidates[0] if baseline in {"retry", "react"} else rng.choice(candidates)
        st.recovery_attempts += 1
        st.latency_ms += action[2]
        st.cost += action[3]
        recovered = rng.random() < action[1]
        if injected == Fault.STATEFUL and "write" in contract.idempotency:
            if action[0] == "compensate" and recovered:
                st.compensated = True
                st.ledger[contract.service] = 0
                # Compensation is a safe rollback, not task completion. Reconcile,
                # invoke an alternative provider, and resume from this step.
                st.recovery_attempts += 1
                st.latency_ms += base_latency * 1.10
                st.cost += contract.cost * 1.10
                recovered = rng.random() < .78
                if recovered:
                    st.completed.append(contract.service)
                    st.ledger[contract.service] = 1
            elif action[0] == "retry":
                if contract.idempotency != "idempotent_write":
                    st.duplicate_side_effect = True
                    st.ledger[contract.service] = 2
        if not recovered:
            st.invariant_violation = injected in {Fault.SEMANTIC, Fault.STATEFUL, Fault.SECURITY}
            break
        if action[0] != "compensate":
            st.completed.append(contract.service)
            if "write" in contract.idempotency: st.ledger[contract.service] = 1

    terminal_ok = len(st.completed) == len(WORKFLOWS[domain])
    if abstained and injected == Fault.SECURITY and policy["security"]:
        terminal_ok = False
    unsafe = st.duplicate_side_effect or st.invariant_violation or st.unauthorized_attempt
    orphan = strict_terminal and not terminal_ok and any(v > 0 for v in st.ledger.values())
    unsafe = unsafe or orphan
    task_success = terminal_ok and not unsafe
    safe_termination = abstained and not unsafe
    acceptable_outcome = task_success or safe_termination
    latency_ok = st.latency_ms <= slo["latency_ms"]
    cost_ok = st.cost <= slo["cost_units"]
    slo_attained = task_success and latency_ok and cost_ok
    return {
        "domain": domain, "fault": fault, "intensity": intensity, "baseline": baseline,
        "seed": seed, "ablation": ablation, "task_success": int(task_success),
        "slo_attained": int(slo_attained), "unsafe_side_effect": int(unsafe),
        "detected": int(st.detected), "localized": int(st.localized),
        "recovered": int(recovered), "abstained": int(abstained),
        "safe_termination": int(safe_termination), "acceptable_outcome": int(acceptable_outcome),
        "latency_ms": round(st.latency_ms, 3), "cost_units": round(st.cost, 3),
        "attempts": st.attempts, "recovery_attempts": st.recovery_attempts,
        "duplicate_side_effect": int(st.duplicate_side_effect),
        "unauthorized_attempt": int(st.unauthorized_attempt),
        "invariant_violation": int(st.invariant_violation), "compensated": int(st.compensated),
        "failure_step": failure_step,
        **({"orphaned_effect": int(orphan)} if strict_terminal else {}),
    }
