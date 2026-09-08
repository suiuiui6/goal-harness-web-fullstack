import argparse, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--variant', required=True); p.add_argument('--output', required=True); a=p.parse_args()
    status='not-run'
    report={'level':'fullstack_fixture','status':status,'variant':a.variant,'limitations':['browser execution is unavailable in this Windows sandbox; no business result claimed']}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True); Path(a.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 2
if __name__ == '__main__': raise SystemExit(main())
