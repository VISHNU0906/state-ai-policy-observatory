"""Build a local reviewable checkpoint without publishing the candidate database."""
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from ledger import ROOT,DEFAULT_DB,Ledger,digest,now


def main():
    destination=ROOT/'output/data-system-checkpoint'
    destination.mkdir(parents=True,exist_ok=True)
    with Ledger(DEFAULT_DB) as store:
        store.backup(destination/'observatory.sqlite')
        export=Path(store.export(ROOT/'ledger-exports'))
        shutil.copytree(export,destination/'datasets',dirs_exist_ok=True)
        audit=store.audit()
    names=['ledger.py','date_rules.py','collect_durable.py','collectors.py','pipeline.py','matching.py',
           'extract_ledger.py','extract_documents.py','history_store.py','sync_tracker.py','build_ledger_bundle.py',
           'README.md','requirements-extraction.txt','docs/LEDGER_OPERATIONS.md','docs/TRACKER_INTEGRATION_FINDINGS.md',
           'docs/DATA_SYSTEM_REVIEW.md','docs/COLLECTION_RELIABILITY.md','docs/DEDUP_EVALUATION.md',
           'evaluation/event_pairs.json','evaluation/source_titles.json','evaluation/title_matching_results.json','data/tracker_integration_audit.json',
           'data/events.json','dist/app.js','proposals/durable-collection.yml',
           '.github/workflows/collect.yml','.github/workflows/pages.yml','CONTEXT_AND_HANDOFF.md',
           'docs/VALIDATION.md','docs/RELEASE.md','runs/durable-system-verification.json']
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').glob('test_*') if p.is_file()]
    for name in names:
        target=destination/'project'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).decode()
    intro='''# Data system checkpoint

This is a local checkpoint, not a claim that the proposed hosted workflow is active.

Read project/docs/LEDGER_OPERATIONS.md and project/docs/TRACKER_INTEGRATION_FINDINGS.md.
datasets/reviewed_events.csv contains approved events. All candidate and external proposal files remain unverified.
observatory.sqlite preserves observation history, imported proposal versions and review state.
The database includes public-source titles, URLs, short snippets, rejection reasons and local import-path provenance.
It excludes API credentials and full extracted publisher article bodies.

The file under project/proposals/ preserves the originally reviewed workflow proposal. Public candidate history and
workflow writes were explicitly approved. The active workflow is in the source repository under .github/workflows/collect.yml.
The live dashboard and its research release are not expanded automatically by this checkpoint.

Run python -m unittest discover -s tests -v from project/. To inspect the bundled database:
python ledger.py --db ../observatory.sqlite audit
Do not run init over the supplied database. Keep the original checkpoint as a backup before making reviews.
'''
    (destination/'START_HERE.md').write_text(intro,encoding='utf-8')
    (destination/'CHECKPOINT.json').write_text(json.dumps({'created_at':now(),'source_commit':source_commit,
        'working_tree_status':status,'audit':audit,'hosted_durable_history':'enabled on approved public data-history branch; see release verification for run outcomes'},indent=2),encoding='utf-8')
    manifest={p.relative_to(destination).as_posix():digest(p.read_bytes()) for p in sorted(destination.rglob('*')) if p.is_file() and p.name!='SHA256_MANIFEST.json'}
    (destination/'SHA256_MANIFEST.json').write_text(json.dumps({'files':manifest},indent=2),encoding='utf-8')
    archive=ROOT/'output/Data_System_Checkpoint_2026-11-10.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(destination.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(destination.parent))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Archive CRC failure')
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(manifest)+1,'audit':audit},indent=2))


if __name__=='__main__':main()
