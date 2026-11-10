"""Package tracked source and reachable history with standalone submission assets."""
from pathlib import Path
import hashlib, json, shutil, subprocess, zipfile
ROOT=Path(__file__).resolve().parent
DEST=ROOT.parent/'State_AI_Policy_Submission_2026-11-10'

def run(*args):return subprocess.check_output(args,cwd=ROOT).decode().strip()

def main():
    if run('git','status','--porcelain'):raise RuntimeError('Commit all release changes before packaging')
    DEST.mkdir(exist_ok=True)
    sha=run('git','rev-parse','HEAD')
    source=DEST/'state-ai-policy-source.zip';bundle=DEST/'state-ai-policy-history.bundle'
    subprocess.run(['git','archive','--format=zip','--output',str(source),'HEAD'],cwd=ROOT,check=True)
    subprocess.run(['git','bundle','create',str(bundle),'--all'],cwd=ROOT,check=True)
    subprocess.run(['git','bundle','verify',str(bundle)],cwd=ROOT,check=True,capture_output=True)
    for dirname in ['data','docs','output','dist']:
        shutil.copytree(ROOT/dirname,DEST/({'output':'reports','dist':'offline-dashboard'}.get(dirname,dirname)),dirs_exist_ok=True)
    shutil.copy2(ROOT/'README.md',DEST/'PROJECT_README.md')
    intro='''# Submission: AI-related policy activity across Indian states

85 reviewed milestones | 12 states | 113 source documents
Research window: 1 January 2024 to 10 November 2026

Live dashboard: https://vishnu0906.github.io/state-ai-policy-observatory/
Public source and commit history: https://github.com/VISHNU0906/state-ai-policy-observatory

Start with reports/Research_Report.pdf and reports/Rationale.pdf.
The main dataset is data/events.csv. Source evidence is data/sources.csv.
Provider comparison and integration details are in reports/Collection_Architecture.pdf.
Open offline-dashboard/index.html for a local copy of the dashboard.

Extract state-ai-policy-source.zip to run the code. Python 3.11+ is sufficient:
python -m unittest discover -s tests -v
python pipeline.py build
python -m http.server 8765 --directory dist

To restore the complete Git history:
git clone state-ai-policy-history.bundle state-ai-policy-observatory

The scheduled job collects pending candidates daily at 07:47 IST. It never automatically
adds unreviewed claims to the published dataset. Public source links need internet access.
See docs/RELEASE.md and docs/VALIDATION.md for test results and known limitations.
All files are local; no Drive folder was created. No credentials or source article bodies
are included. SHA256_MANIFEST.json identifies the source commit and file checksums.
'''
    (DEST/'START_HERE.md').write_text(intro,encoding='utf-8')
    files={p.relative_to(DEST).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='SHA256_MANIFEST.json'}
    (DEST/'SHA256_MANIFEST.json').write_text(json.dumps({'source_commit':sha,'research_cutoff':'2026-11-10','files':files},indent=2),encoding='utf-8')
    archive=DEST.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DEST.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(DEST.parent))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise RuntimeError('Archive CRC check failed')
    print(json.dumps({'folder':str(DEST),'archive':str(archive),'commit':sha,'files':len(files)+1,'zip_bytes':archive.stat().st_size},indent=2))

if __name__=='__main__':main()
