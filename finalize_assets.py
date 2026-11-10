"""Copy reviewed documents into the dashboard; maintain portable release links."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
path=ROOT/'dist/index.html'
text=path.read_text(encoding='utf-8').replace('Has primary source','Primary source attached')
if 'Research_Report.pdf' not in text:
    links='<a href="Research_Report.pdf">Research report ↗</a><a href="Collection_Architecture.pdf">Collection architecture ↗</a><a href="Rationale.pdf">One-page rationale ↗</a><a href="https://github.com/VISHNU0906/state-ai-policy-observatory">Code and methodology ↗</a>'
    text=text.replace('<div class="downloads">','<div class="downloads">'+links)
path.write_text(text,encoding='utf-8')
path=ROOT/'docs/AGGREGATION_RESEARCH.md'
text=path.read_text(encoding='utf-8').replace('A future extraction adapter may use `FIRECRAWL_API_KEY`','The extraction adapter uses `FIRECRAWL_API_KEY`')
path.write_text(text,encoding='utf-8')
for p in (ROOT/'output').glob('*.pdf'):shutil.copy2(p,ROOT/'dist'/p.name)
