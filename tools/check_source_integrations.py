import argparse, json, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root', default='.'); p.add_argument('--online', action='store_true'); a=p.parse_args(); root=Path(a.root)
    manifest=json.loads((root/'tools/source-integrations.json').read_text(encoding='utf-8'))
    errors=[]
    for source in manifest['sources']:
        path=root/source['integration_path']
        if not path.exists(): errors.append(f"missing integration path: {path}")
        commit=source.get('commit', '')
        if len(commit) != 40 or any(ch not in '0123456789abcdef' for ch in commit): errors.append(f"invalid pinned commit for {source['name']}")
        if a.online:
            result=subprocess.run(['git','ls-remote',source['repository']+'.git',f"refs/heads/{source['ref']}"],capture_output=True,text=True)
            observed=result.stdout.split()[0] if result.returncode == 0 and result.stdout.split() else ''
            if observed != commit: errors.append(f"upstream drift for {source['name']}: expected {commit}, observed {observed or 'unavailable'}")
    if errors:
        print('\n'.join(errors)); return 1
    print(f"PASS: {len(manifest['sources'])} source integrations pinned")
    return 0
if __name__ == '__main__': raise SystemExit(main())
