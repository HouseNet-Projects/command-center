import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).parents[2]
class BackboneTests(unittest.TestCase):
 def test_missing_vault_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   cp=Path(d)/'cp'; cp.mkdir(); (cp/'release').mkdir(); (cp/'release/manifest.json').write_text('{"version":"1.4.2"}')
   k=Path(d)/'k'; k.mkdir(); (k/'house-net-control.json').write_text('{"repository":"HouseNet-Projects/house-net-knowledge","policy_version":"1.4.2"}'); (k/'knowledge').mkdir(); (k/'knowledge/index').mkdir(); (k/'knowledge/index/catalog.json').write_text('{"items":[]}')
   p=subprocess.run(['python3',str(ROOT/'bootstrap/backbone.py'),'--control-plane-path',str(cp),'--knowledge-path',str(k),'--vault-path',str(Path(d)/'missing'),'--report-dir',str(Path(d)/'reports')],capture_output=True)
   self.assertNotEqual(p.returncode,0); self.assertNotIn('secret',p.stdout.decode().lower())
 def test_clean_simulation_passes(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d); cp=base/'cp'; (cp/'release').mkdir(parents=True); (cp/'release/manifest.json').write_text('{"version":"1.4.2"}')
   for name,idx in [('knowledge','knowledge/index/catalog.json'),('vault','vault/index.json')]:
    p=base/name; p.mkdir(); (p/'house-net-control.json').write_text(json.dumps({'repository':f'HouseNet-Projects/house-net-{name}','policy_version':'1.4.2'})); (p/Path(idx).parent).mkdir(parents=True); (p/idx).write_text('{"items":[]}' if name=='knowledge' else '{"references":[]}')
   p=subprocess.run(['python3',str(ROOT/'bootstrap/backbone.py'),'--control-plane-path',str(cp),'--knowledge-path',str(base/'knowledge'),'--vault-path',str(base/'vault'),'--report-dir',str(base/'reports')],capture_output=True)
   self.assertEqual(p.returncode,0,p.stdout.decode())
if __name__=='__main__': unittest.main()
