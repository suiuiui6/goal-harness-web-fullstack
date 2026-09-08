import argparse, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root', default='.'); p.add_argument('--output', required=True); a=p.parse_args()
    files=[Path(a.root)/'source/goal/SKILL.md', Path(a.root)/'source/harness-engineering/SKILL.md']
    stages={k:{'files':[], 'bytes':0, 'lines':0, 'tokens':None, 'status':'not-run'} for k in ('S1','S2','S3')}
    for f in files:
        raw=f.read_bytes(); item={'path':str(f), 'bytes':len(raw), 'lines':len(raw.decode('utf-8').splitlines())}; stages['S1']['files'].append(item); stages['S1']['bytes'] += item['bytes']; stages['S1']['lines'] += item['lines']
    report={'encoding':'o200k_base','stages':stages,'limitations':['tiktoken measurement not executed; byte and line counts only']}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True); Path(a.output).write_text(json.dumps(report, indent=2), encoding='utf-8'); return 2
if __name__ == '__main__': raise SystemExit(main())
