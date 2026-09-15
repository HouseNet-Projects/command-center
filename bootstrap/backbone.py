#!/usr/bin/env python3
"""Deterministic, dry-run-by-default HouseNet knowledge/vault bootstrap verifier."""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'bootstrap/backbone-manifest.json'

def sha(path):
 h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()
def report_step(out, name, status, detail): out['steps'].append({'step':name,'status':status,'detail':detail})
def verify_repo(out, spec, path):
 if not path or not path.is_dir(): report_step(out,'repository:'+spec['id'],'FAIL','required repository path is unavailable'); return
 lock=path/'house-net-control.json'
 if not lock.is_file(): report_step(out,'repository:'+spec['id'],'FAIL','control lock missing'); return
 data=json.loads(lock.read_text());
 if data.get('repository') != spec['repository']: report_step(out,'repository:'+spec['id'],'FAIL','repository identity mismatch'); return
 if data.get('policy_version') != out['manifest']['control_plane']['policy_version']: report_step(out,'repository:'+spec['id'],'FAIL','policy version mismatch'); return
 if spec['id']=='knowledge':
  idx=json.loads((path/'knowledge/index/catalog.json').read_text()); detail=f"catalog_items={len(idx.get('items',[]))}"
 else:
  idx=json.loads((path/'vault/index.json').read_text()); detail=f"references={len(idx.get('references',[]))}"
 report_step(out,'repository:'+spec['id'],'PASS',detail)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--knowledge-path',type=Path); ap.add_argument('--vault-path',type=Path); ap.add_argument('--control-plane-path',type=Path); ap.add_argument('--report-dir',type=Path,default=ROOT/'bootstrap/reports'); ap.add_argument('--apply',action='store_true'); ap.add_argument('--json',action='store_true'); args=ap.parse_args()
 m=json.loads(MANIFEST.read_text()); out={'ok':True,'mode':'apply' if args.apply else 'dry-run','manifest':m,'steps':[],'secrets_exposed':False}
 cp=args.control_plane_path or Path(os.environ.get('HOUSENET_CONTROL_PLANE_PATH',''))
 if not cp.is_dir(): report_step(out,'control-plane','FAIL','control-plane path is unavailable'); out['ok']=False
 else:
  lock=cp/'release/manifest.json'
  if not lock.is_file(): report_step(out,'control-plane','FAIL','release manifest missing'); out['ok']=False
  else:
   v=json.loads(lock.read_text()); status='PASS' if v.get('version')==m['control_plane']['policy_version'] else 'FAIL'; report_step(out,'control-plane','%s'%status,f"version={v.get('version')}"); out['ok'] &= status=='PASS'
 verify_repo(out,m['repositories'][0],args.knowledge_path or Path(os.environ.get('HOUSENET_KNOWLEDGE_PATH','')))
 verify_repo(out,m['repositories'][1],args.vault_path or Path(os.environ.get('HOUSENET_VAULT_PATH','')))
 out['ok'] &= all(s['status']=='PASS' for s in out['steps'])
 if args.apply and out['ok']:
  args.report_dir.mkdir(parents=True,exist_ok=True); (args.report_dir/'backbone-state.json').write_text(json.dumps({'restored_non_secret_context':True},indent=2)+'\n'); report_step(out,'local-state','PASS','wrote non-secret bootstrap state')
 elif args.apply: report_step(out,'local-state','SKIP','blocked by failed verification')
 args.report_dir.mkdir(parents=True,exist_ok=True); (args.report_dir/'backbone-report.json').write_text(json.dumps(out,indent=2)+'\n')
 if args.json: print(json.dumps(out,sort_keys=True))
 else:
  for s in out['steps']: print(f"{s['status']} — {s['step']}: {s['detail']}")
  print('PASS — bootstrap foundation verified' if out['ok'] else 'FAIL — bootstrap foundation blocked')
 return 0 if out['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
