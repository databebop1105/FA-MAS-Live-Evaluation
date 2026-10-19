# Build and rerun

Upload fa_mas_revised.tex and figures/ to Overleaf; choose pdfLaTeX. The supplied IEEEtran.cls activates the official journal/compsoc branch. Locally install texlive-science for algorithm/algpseudocode and run pdflatex three times. No class or margin hacks were used to meet the 14-page cap. The PDF remains a draft with author-owned facts unresolved.

The full code/data package includes the original evaluation artifact at its root and this source under revised_source/. Follow root REPRODUCTION.md. Then run python revised_source/check_data.py to regenerate arm_comparison.json and complete_outcomes.csv. HTTP regeneration uses separate commands (choose new output paths):

```bash
PYTHONPATH=src python -m fa_mas.local_services --output /tmp/fa_mas_single
PYTHONPATH=src python -m fa_mas.workflow_services --output /tmp/fa_mas_workflow
PYTHONPATH=src python -m fa_mas.inventory_services --output /tmp/fa_mas_inventory
```

This is same-host repeatability, not outside-team reproduction. No live model runs are included.
