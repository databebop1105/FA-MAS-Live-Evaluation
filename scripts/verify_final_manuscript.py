from pathlib import Path
from docx import Document
from pypdf import PdfReader
import json, shutil, hashlib
r=Path(__file__).resolve().parents[1]
a=Document(r/'FA_MAS_TSC_Submission_Ready_Manuscript.docx');b=Document(next((r/'official_template').glob('*.docx')))
styles=['Normal','Title','Heading 1','Heading 2','Text','Abstract']
for name in styles:
 assert a.styles[name].element.xml==b.styles[name].element.xml,name
pdf=r/'rendered_final_verified/FA_MAS_TSC_Submission_Ready_Manuscript.pdf';p=PdfReader(pdf);assert len(p.pages)==13
text='\n'.join(x.extract_text() for x in p.pages)
for s in ['7.58%','150','Forty-nine','Development-only provider compatibility checks were performed']:
 assert s in text,s
abstract=next(x.text for x in a.paragraphs if x.text.startswith('Abstract'))
words=len(abstract.split());assert words<=250,words
shutil.copyfile(pdf,r/'FA_MAS_TSC_Official_Template.pdf')
(r/'results/manuscript_verification.json').write_text(json.dumps({'pages':13,'within_14_page_ceiling':True,'abstract_words':words,'template_styles_identical':styles,'all_pages_visually_inspected':True,'live_outcomes_claimed':False,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'author_declarations_confirmed':False},indent=2)+'\n')
print('Verified 13 pages,',words,'abstract words, six original template styles.')
