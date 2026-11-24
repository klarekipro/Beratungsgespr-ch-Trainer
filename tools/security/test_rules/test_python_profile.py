import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('profile_runner',Path(__file__).resolve().parents[1]/'run.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
class PythonProfileTests(unittest.TestCase):
 def test_debian_assessment_is_suite_and_package_specific(self):
  package={'name':'synthetic-library','ecosystem':'Debian:13'}
  advisory={'affected':[{'package':dict(package,ecosystem='Debian:12'),'ecosystem_specific':{'urgency':'unimportant'}}]}
  self.assertEqual(R.severity(advisory,package),'UNKNOWN')
  advisory['affected'].append({'package':package,'ecosystem_specific':{'urgency':'not yet assigned'}})
  self.assertEqual(R.severity(advisory,package),'UNKNOWN')
  advisory['affected'][-1]['ecosystem_specific']['urgency']='unimportant'
  self.assertEqual(R.severity(advisory,package),'INFO')
  advisory['affected'][-1]['ecosystem_specific']['urgency']='high'
  self.assertEqual(R.severity(advisory,package),'HIGH')
 def test_python_severity_is_not_replaced_by_a_distribution_classification(self):
  self.assertEqual(R.severity({'database_specific':{'severity':'HIGH'}},{'name':'synthetic','ecosystem':'PyPI'}),'HIGH')
  self.assertEqual(R.severity({}, {'name':'synthetic','ecosystem':'PyPI'}),'UNKNOWN')
if __name__=='__main__':unittest.main()
