import importlib.util
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('sast_fixture_runner',Path(__file__).resolve().parents[1]/'run.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
class PythonSastTests(unittest.TestCase):
 def test_python_specific_positive_and_safe_parameterized_negative(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);source=p/'source';source.mkdir()
   (source/'unsafe.py').write_text("import os,httpx\nkey=os.environ.get('OPENAI_API_KEY','')\nprint(key)\nhttpx.Client(verify=False)\ndef endpoint(request,db):\n name=request.query_params['name']\n db.execute('SELECT * FROM users WHERE name=' + name)\n")
   (source/'safe.py').write_text("import httpx\nhttpx.Client(verify=True)\ndef endpoint(request,db):\n name=request.query_params['name']\n db.execute('SELECT * FROM users WHERE name=?',(name,))\n")
   lock=R.read(R.CONFIG/'tools.lock.json')
   result=R.docker(lock['images']['semgrep'],['semgrep','scan','--oss-only','--metrics=off','--disable-version-check','--strict','--error','--json','--config','/config/semgrep.yml','--output','/report/result.json','/work'],[(source,'/work',False),(R.CONFIG,'/config',False),(p,'/report',True)])
   self.assertEqual(result.returncode,1)
   data=R.read(p/'result.json');self.assertFalse(data['errors'])
   self.assertEqual({x['check_id'].split('.')[-1] for x in data['results']},{'trainer-python-secret-logging','trainer-python-disabled-tls','trainer-python-request-to-sql'})
   self.assertFalse([x for x in data['results'] if Path(x['path']).name=='safe.py'])
if __name__=='__main__':unittest.main()
