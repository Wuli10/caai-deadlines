#!/usr/bin/env python3
"""Refresh CAAI conference deadline data from the ccfddl RSS feed."""
from __future__ import annotations
import argparse,email.utils,json,re,subprocess,sys,urllib.error,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
DEFAULT_FEED_URL="https://ccfddl.com/conference/deadlines_en.xml"
DATA_PREFIX="window.CAAI_DATA = "
def key_from_url(url:str)->str:
    if not url:return""
    compact=re.sub(r"\s+","",url.replace(" -","-").replace("- ","-"))
    m=re.search(r"/db/conf/([^/]+)/?",compact,re.I)
    if m:return m.group(1).lower()
    return re.sub(r"^https?://(www\.)?","",compact.lower()).rstrip("/")
def read_existing_data(path:Path)->dict:
    text=path.read_text(encoding="utf-8").strip()
    if not text.startswith(DATA_PREFIX):raise ValueError(f"{path} does not start with {DATA_PREFIX!r}")
    payload=text[len(DATA_PREFIX):]
    if payload.endswith(";"):payload=payload[:-1]
    return json.loads(payload)
def write_data(path:Path,data:dict)->None:
    path.write_text(DATA_PREFIX+json.dumps(data,ensure_ascii=False,indent=2)+";\n",encoding="utf-8")
def fetch_feed(feed_url:str,local_rss:str|None)->tuple[bytes,str]:
    if local_rss:
        p=Path(local_rss);return p.read_bytes(),p.as_posix()
    req=urllib.request.Request(feed_url,headers={"User-Agent":"caai-deadlines-updater/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=30) as response:return response.read(),feed_url
    except urllib.error.URLError:
        completed=subprocess.run(["curl","-fsSL",feed_url],check=True,stdout=subprocess.PIPE)
        return completed.stdout,feed_url
def parse_feed(feed_bytes:bytes)->tuple[str,dict[str,list[dict]]]:
    root=ET.fromstring(feed_bytes);build_date=root.findtext("./channel/lastBuildDate") or "";by_key={}
    for item in root.findall("./channel/item"):
        title=item.findtext("title") or "";link=item.findtext("link") or "";desc=item.findtext("description") or "";pub=item.findtext("pubDate") or "";lines=desc.splitlines();full=lines[0].strip() if lines else "";fields={};dblp="";label="Deadline";dtext=""
        for line in lines[1:]:
            if line.startswith("Deadline"):
                m=re.match(r"Deadline(?: \(([^)]+)\))?:\s*(.*)",line)
                if m:label=m.group(1) or "Deadline";dtext=m.group(2).strip()
            elif line.startswith("DBLP:"):dblp=line.split("DBLP:",1)[1].strip()
            elif ": " in line:
                k,v=line.split(": ",1);fields[k]=v
        key=key_from_url(dblp)
        if not key or not pub:continue
        deadline=email.utils.parsedate_to_datetime(pub)
        if deadline.tzinfo is None:deadline=deadline.replace(tzinfo=timezone.utc)
        by_key.setdefault(key,[]).append({"title":title,"name":full,"deadlineIso":deadline.isoformat(),"deadlineText":dtext,"deadlineZone":label,"eventDate":fields.get("Date",""),"location":fields.get("Location",""),"website":fields.get("Conference Website",link),"source":"ccfddl"})
    for v in by_key.values():v.sort(key=lambda e:e["deadlineIso"])
    return build_date,by_key
def refresh_deadlines(data:dict,build_date:str,by_key:dict[str,list[dict]])->dict:
    now=datetime.now(timezone.utc);matched=0;upcoming=0
    for c in data["conferences"]:
        keys=[c.get("key",""),*c.get("extraKeys",[])];seen=set();all_deadlines=[]
        for key in keys:
            for d in by_key.get(key,[]):
                sig=(d["title"],d["deadlineIso"])
                if sig in seen:continue
                seen.add(sig);all_deadlines.append(d)
        all_deadlines.sort(key=lambda e:e["deadlineIso"]);future=[d for d in all_deadlines if datetime.fromisoformat(d["deadlineIso"]).astimezone(timezone.utc)>=now]
        c.pop("deadlines",None);c.pop("lastKnownDeadline",None)
        if all_deadlines:matched+=1
        if future:upcoming+=1;c["deadlines"]=future[:4]
        elif all_deadlines:c["lastKnownDeadline"]=all_deadlines[-1]
    meta=data.setdefault("meta",{});meta["deadlineSource"]=DEFAULT_FEED_URL;meta["deadlineSourceBuildDate"]=build_date;meta["generatedAt"]=now.isoformat();meta["matchedConferenceCount"]=matched;meta["upcomingMatchedConferenceCount"]=upcoming
    return data
def main()->int:
    p=argparse.ArgumentParser(description="Refresh CAAI deadline data from ccfddl RSS.");p.add_argument("--data",default="data.js");p.add_argument("--feed-url",default=DEFAULT_FEED_URL);p.add_argument("--rss");args=p.parse_args()
    path=Path(args.data);data=read_existing_data(path);feed,source=fetch_feed(args.feed_url,args.rss);build,by_key=parse_feed(feed);refreshed=refresh_deadlines(data,build,by_key);write_data(path,refreshed);print(f"Updated {refreshed['meta']['conferenceCount']} conferences from {source}; {refreshed['meta']['upcomingMatchedConferenceCount']} have upcoming deadlines.");return 0
if __name__=="__main__":sys.exit(main())
