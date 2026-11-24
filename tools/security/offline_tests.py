
import sys,os,tempfile,unittest,json,contextlib
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];out=a.output;network={'blocked_attempts':0}
def audit(event,args):
 if event in ('socket.connect','socket.getaddrinfo'):
  network['blocked_attempts']+=1;raise RuntimeError('network disabled for isolated audit')
 if event=='subprocess.Popen':
  name=Path(str(args[0])).name
  if name not in ('git','ffprobe','pdftotext','pdfinfo','pdffonts'):
   raise RuntimeError('unexpected child process disabled for isolated audit')
sys.addaudithook(audit)
with tempfile.TemporaryDirectory(prefix='trainer-m06-synthetic-') as tmp:
 os.environ.update(TRAINER_DATA_DIR=tmp+'/bootstrap',TRAINER_AUDIT_DIR='',TRAINER_REMOTE_HTTPS='0',TRAINER_ALLOWED_HOSTS='testserver',OPENAI_API_KEY='',PYTHONDONTWRITEBYTECODE='1')
 sys.dont_write_bytecode=True;sys.path.insert(0,str(root));os.chdir(root)
 names=['tests.functional.test_portals.PortalSmoke','tests.dashboard.test_learning_workflow.WorkflowChecks',
        'tests.dashboard.test_certificate_design.CertificateDesign.test_unicode_layout_one_page_fonts_and_safe_failure',
        'tests.dashboard.test_simple_actor.SimpleActorSmoke.test_single_responses_request_no_storage_or_verifier',
        'tests.dashboard.test_pilot_deployment.PilotDeploymentTests']
 suite=unittest.defaultTestLoader.loadTestsFromNames(names)
 import io
 stream=io.StringIO()
 with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
  result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 payload={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'failures':[str(t) for t,_ in result.failures],'errors':[str(t) for t,_ in result.errors],'network':network,'live_database_used':False,'paid_calls':0,'test_names':names}
 out.write_text(json.dumps(payload,indent=2)+'\n');# Raw assertion/provider output intentionally withheld.
 print(json.dumps(payload))
