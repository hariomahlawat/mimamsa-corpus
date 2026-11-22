"""Identify an exact 27 Nov 1954 official Gazette scan without lowering evidentiary standards.

This is source discovery only. HTML, indexes, snippets and privately hosted
copies must NEVER be labelled as the authoritative original Gazette.
"""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib,io,json,re,urllib.parse
from pathlib import Path
import requests
from huggingface_hub import HfApi,CommitOperationAdd,hf_hub_download

REPO="hariomahlawat/mimamsa-corpus"
OUTPUT="legal_knowledge/gazette_discovery/v3.5/01_1954_Gazette_Source_Probe.json"
TARGET={
  "instrument":"Army Rules, 1954",
  "gazette":"Gazette of India, Part II, Section 4",
  "publication_date":"1954-11-27",
  "notification":"S.R.O. 484",
  "issue_number_reported_by_secondary_source":"47",
  "printed_pages_reported_by_secondary_source":"291–378",
  "critical_question":"Army Rule 23(3) warning: does the original gazetted wording contain the negative not?"
}
URLS=[
 ("GOVT_EGAZETTE_HOME","https://egazette.gov.in/"),
 ("GOVT_EGAZETTE_SEARCH","https://egazette.gov.in/SearchGazette.aspx"),
 ("CSL_WEEKLY_MIRROR_INDEX","https://egazette.servantsofknowledge.in/sources/csl_weekly/"),
 ("CSL_ARCHIVED_GAZETTE_SEARCH","https://egazette.servantsofknowledge.in/search/?q=1954-11-27"),
 ("CSL_ARCHIVED_GAZETTE_TEXT","https://egazette.servantsofknowledge.in/search/?q=27+November+1954"),
 ("CSL_ARCHIVED_SRO_TEXT","https://egazette.servantsofknowledge.in/search/?q=S.R.O.+484"),
 ("INTERNET_ARCHIVE_METADATA","https://archive.org/advancedsearch.php?q="+urllib.parse.quote('title:"Gazette of India" AND year:1954')+"&fl%5B%5D=identifier&fl%5B%5D=title&rows=15&page=1&output=json"),
]
def get(path,revision=None):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",
                filename=path,revision=revision,force_download=True))
def main():
    api=HfApi()
    if not api.repo_info(repo_id=REPO,repo_type="dataset").private:
        raise RuntimeError("Private HF dataset mandatory")
    runs=[]
    for key,url in URLS:
        row={"probe_id":key,"url":url,"status":"NOT_TESTED"}
        try:
            r=requests.get(url,timeout=15,
                           headers={"User-Agent":"Mimamsa-public-Gazette-source-discovery/1.0"},
                           allow_redirects=True)
            row.update({"http_status":r.status_code,
                        "final_url":r.url,
                        "response_bytes":len(r.content),
                        "content_type":r.headers.get("content-type",""),
                        "response_sha256":hashlib.sha256(r.content).hexdigest()})
            r.raise_for_status()
            sample=r.text[:400000]
            lower=sample.lower()
            row["mentions_1954"]=bool("1954" in lower)
            row["mentions_27_nov_1954"]=any(k in lower for k in ("27 november 1954","27-11-1954","1954-11-27","27th november, 1954"))
            row["mentions_sro484"]=bool(re.search(r"s\.?r\.?o\.?\s*484",lower))
            row["status"]="HTML_OR_JSON_DISCOVERY_ONLY"
            possible=[]
            # Preserve exact observed links only, never invent provenance or combine fragments.
            for m in re.finditer(r'(?:href|src)=["\']([^"\']+)["\']',sample,re.I):
                val=m.group(1)
                if ("1954" in val or "484" in val or "1954" in sample[max(0,m.start()-120):m.end()+120]):
                    possible.append(urllib.parse.urljoin(r.url,val))
                if len(possible)>=12:
                    break
            row["candidate_hrefs_observed"]=list(dict.fromkeys(possible))
            detail_links=[]
            for m in re.finditer(r'(?:href|src)=["\\']([^"\\']*/details/[^"\\']+)["\\']', sample, re.I):
                link=urllib.parse.urljoin(r.url,m.group(1))
                detail_links.append({
                    "url":link,
                    "surrounding_index_text":" ".join(re.sub(r"<[^>]+>"," ",
                                             sample[max(0,m.start()-160):m.end()+300]).split())[:380]
                })
            row["gazette_detail_links_on_page"]=detail_links[:35]
            row["gazette_detail_links_count"]=len(detail_links)
            row["exact_date_matches_near_results"]=[
              " ".join(re.sub(r"<[^>]+>"," ",sample[max(0,m.start()-180):m.end()+220]).split())[:420]
              for m in list(re.finditer(r"(?:27\\s+November\\s+1954|1954-11-27|27-11-1954)",sample,re.I))[:8]
            ]
        except requests.RequestException as ex:
            row.update({"status":"REQUEST_FAILED",
                        "error_type":type(ex).__name__,
                        "error_excerpt":str(ex)[:220]})
        runs.append(row)
        print("GAZ_V35_PROBE",key,row["status"],row.get("http_status"),row.get("mentions_27_nov_1954",False))
    report={
     "target":TARGET,"checked_utc":datetime.now(timezone.utc).isoformat(),
     "original_official_gazette_pdf_archived":False,
     "rule23_original_wording_authenticated":False,
     "direct_gazette_scan_identified":False,
     "probes":runs,
     "limitations":[
        "Only automated public landing-page and metadata discovery, not exhaustive portal date/section search",
        "Even an exact historical issue indexed in a mirror is not authenticated without original image/page examination",
        "Online annotated Army Rules PDF hosted at India Code is not itself original 1954 Gazette image",
        "Requester must obtain government archival issue or certified copy, preserving issue/page, SHA and provenance",
        "Never remove the Rule23(3) disputed negation gate on the basis of this probe"
      ]
    }
    encoded=(json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode()
    res=api.create_commit(repo_id=REPO,repo_type="dataset",
       operations=[CommitOperationAdd(path_in_repo=OUTPUT,path_or_fileobj=io.BytesIO(encoded))],
       commit_message="Record attempted authenticated 1954 Army Rules Gazette source discovery without unsupported claims")
    rev=getattr(res,"oid",None)
    if not rev or get(OUTPUT,rev).read_bytes()!=encoded:
        raise RuntimeError("Gazette probe remote readback mismatch")
    print("GAZ_V35_READBACK_VERIFIED",len(runs),"probes; original Gazette authentication still OPEN",rev)

if __name__=="__main__":
    main()
