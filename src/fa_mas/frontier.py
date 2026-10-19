"""Reference Pareto selector for finite single-action recovery candidates.

This is not executable-subgraph enumeration or a calibrated predictor.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Candidate:
    name: str
    success: float
    latency: float
    cost: float
    risk: float
    def as_tuple(self):return (self.name,self.success,self.latency,self.cost,self.risk)
    def vector(self):return (-self.success,self.latency,self.cost,self.risk)

def frontier(candidates):
    for c in candidates:
        if any(not math.isfinite(x) for x in c.vector()) or not 0<=c.success<=1 or min(c.latency,c.cost,c.risk)<0:
            raise ValueError('Invalid candidate estimate')
    return [c for c in candidates if not any(all(x<=y for x,y in zip(d.vector(),c.vector())) and any(x<y for x,y in zip(d.vector(),c.vector())) for d in candidates)]

def select_frontier(candidates,weights):
    if any(not math.isfinite(weights[k]) or weights[k]<0 for k in ('latency','cost','risk')):raise ValueError('Monotone nonnegative weights required')
    values=frontier(candidates)
    if not values:raise ValueError('Empty feasible frontier')
    return max(values,key=lambda c:c.success-weights['latency']*c.latency-weights['cost']*c.cost-weights['risk']*c.risk)
