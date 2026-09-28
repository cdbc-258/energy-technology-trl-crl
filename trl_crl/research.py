"""Optional public news discovery. Results are leads, never maturity scores."""
import argparse,json,urllib.request,urllib.parse,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path

def search(query,cutoff,language='zh-CN'):
 zh=language=='zh-CN'
 params={'q':query+' before:'+cutoff,'hl':language,'gl':'CN' if zh else 'US','ceid':'CN:zh-Hans' if zh else 'US:en'}
 url='https://news.google.com/rss/search?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={'User-Agent':'PublicEvidenceResearch/1.0'})
 with urllib.request.urlopen(req,timeout=30) as r:raw=r.read(8*1024*1024)
 doc=ET.fromstring(raw);rows=[]
 for e in doc.findall('.//item'):
  rows.append({'title':e.findtext('title'),'news_url':e.findtext('link'),'published_at_raw':e.findtext('pubDate'),'publisher':e.findtext('source'),'accepted_as_evidence':False})
 return {'query':query,'requested_url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'results':rows,'scope':'News RSS discovery only; follow source links and review object identity and completed events before any grading'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('query');p.add_argument('--before',required=True,help='Exclusive cutoff YYYY-MM-DD');p.add_argument('--language',default='zh-CN');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(search(a.query,a.before,a.language),ensure_ascii=False,indent=2)+'\n')
