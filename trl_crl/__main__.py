"""Command line entry point."""
import argparse,json
from pathlib import Path
from .pipeline import write_outputs,assess,INPUT_NAMES
from .common import read,write,file_sha,canonical_sha

def main():
 p=argparse.ArgumentParser(description='Independent evidence-based TRL/CRL assessment')
 p.add_argument('command',choices=['build','validate','summary'])
 p.add_argument('--data',type=Path,default=Path('data'));p.add_argument('--output',type=Path,default=Path('results'));p.add_argument('--no-excel',action='store_true')
 a=p.parse_args()
 if a.command=='build':s=write_outputs(a.data,a.output,not a.no_excel);print(json.dumps(s,ensure_ascii=False,indent=2))
 elif a.command=='summary':print(json.dumps(assess(a.data)[1]['SUMMARY'],ensure_ascii=False,indent=2))
 else:
  d,o=assess(a.data);checks=[]
  for name,value in o.items():
   path=a.output/(name+'.json');checks.append(dict(check='reproduce_'+name,passed=path.exists() and canonical_sha(read(path))==canonical_sha(value)))
  checks.append(dict(check='no_formal_grades',passed=all(u['formal_trl'] is None and u['formal_crl'] is None for u in o['assessment_units'])))
  checks.append(dict(check='no_direction_scalar',passed=all(u['direction_trl'] is None and u['direction_crl'] is None for u in o['direction_evidence_profiles'])))
  checks.append(dict(check='paired_axes_same_object',passed=all(u['paired_axes_usable']==(u['trl_public_evidence_stage'] is not None and u['crl_public_evidence_stage'] is not None) for u in o['assessment_units'])))
  cp=a.output/'INPUT_CHECKSUMS.json'
  checks.append(dict(check='input_checksums',passed=cp.exists() and read(cp)=={n+'.json':file_sha(a.data/(n+'.json')) for n in INPUT_NAMES}))
  report=dict(passed=sum(c['passed'] for c in checks),total=len(checks),checks=checks,interpretation='引文完整性、来源外键和逐门槛计算验证；不是语义准确率或专家认可率')
  write(a.output/'VALIDATION.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
  if not all(c['passed'] for c in checks):raise SystemExit(1)
if __name__=='__main__':main()
