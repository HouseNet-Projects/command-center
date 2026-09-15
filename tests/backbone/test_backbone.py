import json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).parents[2]
KNOW=Path('/home/gevorg/house-net-knowledge'); VAULT=Path('/home/gevorg/house-net-vault')
def git_repo(path,origin):
 subprocess.run(['git','init','-q'],cwd=path,check=True); subprocess.run(['git','config','user.email','test@example.invalid'],cwd=path); subprocess.run(['git','config','user.name','Test'],cwd=path); subprocess.run(['git','remote','add','origin',origin],cwd=path); subprocess.run(['git','add','.'],cwd=path,check=True); subprocess.run(['git','commit','-qm','fixture'],cwd=path,check=True)
def env():
 d=Path(tempfile.mkdtemp()); cp=d/'control'; (cp/'release').mkdir(parents=True); (cp/'bin').mkdir(); (cp/'release/manifest.json').write_text('{"version":"1.4.2"}'); pre=cp/'bin/housenet-preflight'; pre.write_text('#!/bin/sh\nprintf \'{\\"ok\\":true}\\n\'\n'); pre.chmod(0o755); git_repo(cp,'https://github.com/HouseNet-Projects/house-net-control-plane.git')
 k=d/'knowledge'; shutil.copytree(KNOW,k,ignore=shutil.ignore_patterns('.git','__pycache__')); git_repo(k,'https://github.com/HouseNet-Projects/house-net-knowledge.git')
 v=d/'vault'; shutil.copytree(VAULT,v,ignore=shutil.ignore_patterns('.git','__pycache__')); git_repo(v,'https://github.com/HouseNet-Projects/house-net-vault.git')
 return d,cp,k,v
def run(d,cp,k,v,extra=()):
 out=d/'reports'; return subprocess.run(['python3',str(ROOT/'bootstrap/backbone.py'),'--control-plane-path',str(cp),'--knowledge-path',str(k),'--vault-path',str(v),'--report-dir',str(out),*extra],capture_output=True,text=True)
class BackboneTests(unittest.TestCase):
 def test_clean_zero_state_passes(self):
  d,cp,k,v=env(); p=run(d,cp,k,v); self.assertEqual(p.returncode,0,p.stdout); self.assertTrue((d/'reports/backbone-report.json').exists())
 def test_apply_and_repeat_are_idempotent(self):
  d,cp,k,v=env(); p=run(d,cp,k,v,['--apply']); self.assertEqual(p.returncode,0); marker=d/'reports/backbone-state.json'; first=marker.read_text(); p=run(d,cp,k,v,['--apply']); self.assertEqual(p.returncode,0); self.assertEqual(first,marker.read_text())
 def test_missing_control_plane_fails(self):
  d,cp,k,v=env(); cp.rename(d/'gone'); self.assertNotEqual(run(d,d/'missing-control-plane',k,v).returncode,0)
 def test_missing_knowledge_fails(self):
  d,cp,k,v=env(); k.rename(d/'gone'); self.assertNotEqual(run(d,cp,d/'missing-knowledge',v).returncode,0)
 def test_missing_vault_fails(self):
  d,cp,k,v=env(); v.rename(d/'gone'); self.assertNotEqual(run(d,cp,k,d/'missing-vault').returncode,0)
 def test_wrong_origin_fails(self):
  d,cp,k,v=env(); subprocess.run(['git','remote','set-url','origin','https://example.invalid/x.git'],cwd=k,check=True); self.assertNotEqual(run(d,cp,k,v).returncode,0)
 def test_wrong_policy_lock_fails(self):
  d,cp,k,v=env(); x=json.loads((k/'house-net-control.json').read_text()); x['policy_version']='0.0.0'; (k/'house-net-control.json').write_text(json.dumps(x)); self.assertNotEqual(run(d,cp,k,v).returncode,0)
 def test_corrupt_catalog_fails(self):
  d,cp,k,v=env(); (k/'knowledge/index/catalog.json').write_text('{bad'); self.assertNotEqual(run(d,cp,k,v).returncode,0)
 def test_corrupt_vault_index_fails(self):
  d,cp,k,v=env(); (v/'vault/index.json').write_text('{bad'); self.assertNotEqual(run(d,cp,k,v).returncode,0)
 def test_no_secret_disclosure(self):
  d,cp,k,v=env(); (v/'vault/index.json').write_text('{"references":[{"id":"secret-value-never-print"}]}'); p=run(d,cp,k,v); self.assertNotEqual(p.returncode,0); self.assertNotIn('secret-value-never-print',p.stdout+p.stderr)
 def test_dry_run_does_not_write_state(self):
  d,cp,k,v=env(); p=run(d,cp,k,v); self.assertEqual(p.returncode,0); self.assertFalse((d/'reports/backbone-state.json').exists())
if __name__=='__main__': unittest.main()
