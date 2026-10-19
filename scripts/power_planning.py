"""Assumption-based cluster power planning; no empirical/live power claim."""
import csv,json,math
from pathlib import Path
from scipy.stats import t,nct
from scipy.optimize import brentq

out=Path('results/power_planning');out.mkdir(exist_ok=True)
rows=[]
G=16;m=4
for q in [.1,.25,.5]:
 for rho in [0,.5,1]:
  for alpha in [.05,.05/3]:
   critical=t.ppf(1-alpha/2,G-1)
   def power(delta):
    # D in {-1,0,+1}; E[D]=delta, P[D!=0]=q.
    # Four paired cells per service/fault cluster; assumed ICC=rho.
    se=math.sqrt((q-delta*delta)*(1+(m-1)*rho)/(G*m))
    nc=delta/se
    return float(nct.sf(critical,G-1,nc)+nct.cdf(-critical,G-1,nc))
   max_effect=q*(1-1e-8)
   mde=brentq(lambda d:power(d)-.8,0,max_effect) if power(max_effect)>=.8 else None
   rows.append({'clusters':G,'pairs_per_cluster':m,'assumed_discordance':q,'assumed_icc':rho,'alpha':alpha,
                'approx_power_2pp':power(.02),'approx_power_5pp':power(.05),
                'approx_80pct_mde':mde,'max_feasible_effect_given_q':q})
with (out/'planning.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
(out/'ASSUMPTIONS.md').write_text('# Live-bank power planning assumptions\n\nThese are hypothetical inputs, not estimates from live or held-out observations. The paired effect takes values -1, 0 and +1, with assumed discordance q and mean delta. Four task-variant/model pairs share each of 16 service/fault clusters. The assumed intracluster correlation is rho. Standard-error variance is (q-delta²)(1+3rho)/64. A noncentral-t approximation with 15 degrees of freedom provides scenario planning, not exact small-sample power. It is a reference cluster-mean t-test, not the implemented percentile bootstrap/conditional sign test. The alpha=.05/3 rows illustrate a conservative multiplicity threshold, not exact Holm power. Blank MDE means 80% power was not reached within delta<=q under this approximation. Unknown discordance/ICC, authored clusters and distribution shape make actual power unresolved. Results must not justify claims of adequate power, real effect sizes, external validity or a favorable acceptance probability. Larger independent task families should be planned before freezing if modest effects matter.\n')
print('Power planning scenarios:',len(rows));print('Approximate 2pp power range',min(r['approx_power_2pp'] for r in rows),max(r['approx_power_2pp'] for r in rows))
