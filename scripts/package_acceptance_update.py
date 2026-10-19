from pathlib import Path
import hashlib, json, zipfile
root=Path(__file__).resolve().parents[1]
include=['requirements-reproduction.lock','THIRD_PARTY_NOTICES.md','COVER_LETTER_DRAFT.md','AUTHOR_SUBMISSION_INPUTS.json','REPRODUCTION.md','Dockerfile','FA_MAS_Remaining_Priorities_Verification.md','README.md','SUBMISSION_READINESS.md','AUTHOR_DECLARATIONS_TO_CONFIRM.md','FA_MAS_Bounded_Live_Study_Protocol.md','requirements-bounded.lock','pyproject.toml','build_manuscript.py','make_figures.py','FA_MAS_TSC_Submission_Ready_Manuscript.docx']
for sub in ['src','tests','configs','scripts','paper_assets','results','official_template','third_party','historical_source']:
 include += [p.relative_to(root).as_posix() for p in (root/sub).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc')]
include=sorted(set(include)); manifest={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in include}
manifest_path=root/'ACCEPTANCE_UPDATE_SHA256.json';manifest_path.write_text(json.dumps({'files':manifest,'notes':'Generated from local source and raw results; official IEEE template downloaded separately from template-selector.ieee.org.'},indent=2)+'\n')
with zipfile.ZipFile(root/'FA_MAS_Research_Evidence_Artifact_v3.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in include+['ACCEPTANCE_UPDATE_SHA256.json']:
  z.write(root/p,p)
print(len(include),'source and evidence files packaged')
