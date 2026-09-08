import argparse, json, shutil
from pathlib import Path

EXCLUDED = {".codex", ".git", "__pycache__", "artifacts", "tests", "fixtures", "docs"}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest', required=True); p.add_argument('--output', required=True); a=p.parse_args()
    root=Path.cwd(); spec=json.loads(Path(a.manifest).read_text(encoding='utf-8')); out=Path(a.output); out.mkdir(parents=True, exist_ok=True)
    copied=[]
    for entry in spec['files']:
        src=(root/entry).resolve()
        if root not in src.parents and src != root: raise SystemExit('path escapes root')
        if any(part in EXCLUDED for part in src.relative_to(root).parts): raise SystemExit(f'excluded path: {entry}')
        if not src.exists(): raise SystemExit(f'missing release path: {entry}')
        dest=out/src.relative_to(root)
        if src.is_dir(): shutil.copytree(src, dest, dirs_exist_ok=True)
        else: dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dest)
        copied.append(entry)
    (out/'manifest.json').write_text(json.dumps({'version':1,'files':copied}, indent=2), encoding='utf-8')
    print(f'PASS: release candidate assembled ({len(copied)} entries)')
    return 0
if __name__ == '__main__': raise SystemExit(main())
