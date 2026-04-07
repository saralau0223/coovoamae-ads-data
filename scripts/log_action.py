#!/usr/bin/env python3
"""广告优化操作记录器"""
import json, sys
from datetime import datetime
from pathlib import Path
ACTIONS_DIR = Path("/root/coovoamae-ads-data/data/actions")
def log_action(atype, target, detail):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    ACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    lf = ACTIONS_DIR / f"{today}.json"
    actions = []
    if lf.exists():
        with open(lf) as f: actions = json.load(f).get("actions",[])
    try: dp = json.loads(detail)
    except: dp = {"note": detail}
    actions.append({"time":datetime.utcnow().isoformat()+"Z","type":atype,"target":target,"detail":dp})
    with open(lf,'w') as f:
        json.dump({"date":today,"count":len(actions),"actions":actions}, f, indent=2, ensure_ascii=False)
    print(f"Logged: {atype} -> {target}")
if __name__ == "__main__":
    if len(sys.argv)<4: print("Usage: log_action.py <type> <target> <detail>"); sys.exit(1)
    log_action(sys.argv[1], sys.argv[2], sys.argv[3])
