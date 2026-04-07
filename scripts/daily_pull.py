#!/usr/bin/env python3
"""COOVOAMAE 广告数据每日拉取 → GitHub"""
import json, csv, os, subprocess, sys, gzip, time
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request, urllib.parse

REPO_DIR = Path("/root/coovoamae-ads-data")
DATA_DIR = REPO_DIR / "data"
ADS_PROFILE_ID = "1895728934123476"

def load_creds():
    cfg = Path("/root/.amazon_mcp_config.json")
    if cfg.exists():
        with open(cfg) as f:
            c = json.load(f)
        return {
            "client_id": c.get("client_id", c.get("ads_client_id", "")),
            "client_secret": c.get("client_secret", c.get("ads_client_secret", "")),
            "refresh_token": c.get("refresh_token", c.get("ads_refresh_token", "")),
        }
    return {
        "client_id": os.environ.get("AMAZON_CLIENT_ID", ""),
        "client_secret": os.environ.get("AMAZON_CLIENT_SECRET", ""),
        "refresh_token": os.environ.get("AMAZON_REFRESH_TOKEN", ""),
    }

def get_token(creds):
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token", "client_id": creds["client_id"],
        "client_secret": creds["client_secret"], "refresh_token": creds["refresh_token"],
    }).encode()
    req = urllib.request.Request("https://api.amazon.com/auth/o2/token", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["access_token"]

def request_report(token, rtype, date_str, creds):
    configs = {
        "search_terms": {"reportTypeId":"spSearchTerm","groupBy":["searchTerm"],
            "columns":["date","campaignName","campaignId","adGroupName","adGroupId",
                "keyword","keywordType","searchTerm","impressions","clicks","cost","purchases7d","sales7d","acos7d"]},
        "keywords": {"reportTypeId":"spTargeting","groupBy":["targeting"],
            "columns":["date","campaignName","campaignId","adGroupName","adGroupId",
                "keywordId","keyword","matchType","impressions","clicks","cost","purchases7d","sales7d","acos7d","cpc","ctr"]},
        "campaigns": {"reportTypeId":"spCampaigns","groupBy":["campaign"],
            "columns":["date","campaignName","campaignId","campaignStatus",
                "campaignBudgetAmount","impressions","clicks","cost","purchases7d","sales7d","acos7d","roas7d"]},
    }
    c = configs[rtype]
    body = json.dumps({"reportDate":date_str,"configuration":{
        "adProduct":"SPONSORED_PRODUCTS","groupBy":c["groupBy"],"columns":c["columns"],
        "reportTypeId":c["reportTypeId"],"timeUnit":"DAILY","format":"GZIP_JSON"}}).encode()
    req = urllib.request.Request("https://advertising-api.amazon.com/reporting/reports", data=body, headers={
        "Content-Type":"application/vnd.createasyncreportrequest.v3+json",
        "Authorization":f"Bearer {token}",
        "Amazon-Advertising-API-ClientId":creds["client_id"],
        "Amazon-Advertising-API-Scope":ADS_PROFILE_ID})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("reportId")

def poll_download(token, rid, output, creds, max_wait=300):
    headers = {"Authorization":f"Bearer {token}","Amazon-Advertising-API-ClientId":creds["client_id"],"Amazon-Advertising-API-Scope":ADS_PROFILE_ID}
    start = time.time()
    while time.time()-start < max_wait:
        req = urllib.request.Request(f"https://advertising-api.amazon.com/reporting/reports/{rid}", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        st = result.get("status")
        if st == "COMPLETED":
            url = result.get("url")
            if url:
                with urllib.request.urlopen(url, timeout=60) as r2:
                    raw = r2.read()
                try: data = json.loads(gzip.decompress(raw))
                except: data = json.loads(raw)
                if data:
                    with open(output, "w", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
                        w.writeheader(); w.writerows(data)
                    return len(data)
            return 0
        elif st == "FAILURE": return -1
        time.sleep(15)
    return -1

def gen_summary(date_str):
    daily = DATA_DIR/"daily"/date_str; sumdir = DATA_DIR/"summary"; sumdir.mkdir(parents=True, exist_ok=True)
    s = {"date":date_str,"generated_at":datetime.utcnow().isoformat()+"Z",
         "campaigns":{},"top_search_terms":{"profitable":[],"wasteful":[]},
         "totals":{"spend":0,"sales":0,"orders":0,"impressions":0,"clicks":0}}
    cf = daily/"campaigns.csv"
    if cf.exists():
        with open(cf) as f:
            for r in csv.DictReader(f):
                sp=float(r.get("cost",0));sl=float(r.get("sales7d",0));od=int(float(r.get("purchases7d",0)))
                imp=int(float(r.get("impressions",0)));cl=int(float(r.get("clicks",0)))
                s["campaigns"][r.get("campaignName","")]={"spend":round(sp,2),"sales":round(sl,2),"orders":od,
                    "acos":round(sp/sl*100,1) if sl>0 else 999,"status":r.get("campaignStatus","")}
                for k,v in [("spend",sp),("sales",sl),("orders",od),("impressions",imp),("clicks",cl)]:
                    s["totals"][k]+=v
    t=s["totals"];t["spend"]=round(t["spend"],2);t["sales"]=round(t["sales"],2)
    t["acos"]=round(t["spend"]/t["sales"]*100,1) if t["sales"]>0 else 999
    t["ctr"]=round(t["clicks"]/t["impressions"]*100,2) if t["impressions"]>0 else 0
    t["cpc"]=round(t["spend"]/t["clicks"],2) if t["clicks"]>0 else 0
    stf = daily/"search_terms.csv"
    if stf.exists():
        terms=[]
        with open(stf) as f:
            for r in csv.DictReader(f):
                sp=float(r.get("cost",0));sl=float(r.get("sales7d",0));od=int(float(r.get("purchases7d",0)))
                ac=(sp/sl*100) if sl>0 else 999
                terms.append({"term":r.get("searchTerm",""),"campaign":r.get("campaignName",""),
                    "spend":round(sp,2),"sales":round(sl,2),"orders":od,"acos":round(ac,1),"clicks":int(float(r.get("clicks",0)))})
        s["top_search_terms"]["profitable"]=sorted([x for x in terms if x["sales"]>0 and x["acos"]<=25],key=lambda x:x["sales"],reverse=True)[:20]
        s["top_search_terms"]["wasteful"]=sorted([x for x in terms if (x["spend"]>1 and x["orders"]==0) or x["acos"]>50],key=lambda x:x["spend"],reverse=True)[:20]
        s["search_term_count"]=len(terms)
    for name in ["latest.json",f"{date_str}.json"]:
        with open(sumdir/name,"w") as f: json.dump(s,f,indent=2,ensure_ascii=False)
    return s

def gen_trend():
    sumdir=DATA_DIR/"summary"; days=[]
    for i in range(7):
        d=(datetime.utcnow()-timedelta(days=i+1)).strftime("%Y-%m-%d")
        fp=sumdir/f"{d}.json"
        if fp.exists():
            with open(fp) as f: dd=json.load(f)
            days.append({"date":d,**{k:dd["totals"][k] for k in ["spend","sales","orders","acos"]}})
    days.reverse()
    with open(sumdir/"weekly_trend.json","w") as f:
        json.dump({"updated":datetime.utcnow().isoformat()+"Z","days":days},f,indent=2)

def git_push(date_str):
    os.chdir(REPO_DIR)
    subprocess.run(["git","add","-A"],check=True)
    if subprocess.run(["git","diff","--cached","--quiet"]).returncode==0:
        print("  No changes"); return
    subprocess.run(["git","commit","-m",f"Daily ads data {date_str}"],check=True)
    subprocess.run(["git","push"],check=True)
    print(f"  Pushed: {date_str}")

def main():
    target=(datetime.utcnow()-timedelta(days=1)).strftime("%Y-%m-%d")
    if len(sys.argv)>1: target=sys.argv[1]
    print(f"=== COOVOAMAE Ads Pull: {target} ===")
    daily=DATA_DIR/"daily"/target; daily.mkdir(parents=True,exist_ok=True)
    creds=load_creds()
    if not creds.get("refresh_token"):
        print("No refresh_token. Check ~/.amazon_mcp_config.json"); sys.exit(1)
    print("Getting token..."); token=get_token(creds)
    rids={}
    for rt in ["search_terms","keywords","campaigns"]:
        print(f"Requesting {rt}...")
        rid=request_report(token,rt,target,creds)
        if rid: rids[rt]=rid; print(f"  ID: {rid}")
        else: print(f"  Failed")
    for rt,rid in rids.items():
        out=daily/f"{rt}.csv"; print(f"Downloading {rt}...")
        n=poll_download(token,rid,out,creds); print(f"  {n} rows")
    print("Generating summary..."); s=gen_summary(target)
    print(f"  spend=${s[totals][spend]}, sales=${s[totals][sales]}, ACoS={s[totals][acos]}%")
    print("Generating trend..."); gen_trend()
    print("Pushing..."); git_push(target)
    print("=== Done ===")

if __name__=="__main__": main()
