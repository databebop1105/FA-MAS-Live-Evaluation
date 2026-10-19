from pathlib import Path
p=Path('build_manuscript.py'); s=p.read_text()
replacements={
'These engineered results do not constitute live-LLM or production evidence.':'A second, distinct inventory service adds 35 authored HTTP/SQLite runs; its FA-MAS controller safely stops on incompatible alternatives but remains unsafe when release fails. These engineered results do not constitute live-LLM or production evidence.',
'The suite does not execute an LLM, dynamic multi-agent planning, or genuinely distinct implementations for its three domain labels.':'A separate inventory implementation uses stock-capacity constraints, persistent holds, capture, release, two SKUs, and an independent terminal judge. It executes 35 additional authored cases over seven faults and five policies. These model-free suites do not execute dynamic multi-agent planning; the first suite still shares one state machine across its three domain labels.',
'Seventeen current unit tests cover simulator properties and service faults; a separate auditor recomputes all 135 workflow terminal verdicts from stored ledgers.':'Eighteen current unit tests cover simulator properties and both service implementations; separate auditors recompute workflow verdicts and inventory capacity invariants from stored ledgers.',
'All counts describe engineered mechanism behavior, not a real fault distribution; no p-values or live-model performance are inferred.':'On the separate inventory implementation, FA-MAS completes four of seven authored faults, safely stops twice, and leaves one unsafe hold when release is unavailable. The feature-matched control completes four, safely stops none, and has three unsafe outcomes, including capture of a different SKU. All counts describe engineered mechanism behavior, not a real fault distribution; no p-values or live-model performance are inferred.',
'The three labels represent monetary, reservation, and operational intents in the simulator, but the local HTTP suite implements one shared state machine rather than distinct industry services.':'The three labels represent monetary, reservation, and operational intents in the simulator and the original local HTTP suite shares one state machine. A second inventory service has genuinely different storage and business invariants, but its seven authored scenarios still cannot establish population-level generalization.',
'72 single-step and 135 three-step run rows':'72 single-step, 135 three-step, and 35 inventory run rows',
'The paper\'s defensible contribution is therefore not a universal claim of superior agent intelligence.':'The paper\'s defensible contribution is therefore not a universal claim of superior agent intelligence.',
}
for a,b in replacements.items():
 if a not in s: raise SystemExit('missing: '+a)
 s=s.replace(a,b)
p.write_text(s)
