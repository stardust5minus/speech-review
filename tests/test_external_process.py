import subprocess
import sys
import unittest
from backend.external_process import run


class ExternalProcessTest(unittest.TestCase):
    def test_output_and_returncode(self):
        result=run([sys.executable,'-c',"print('MFA child')"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout.strip(),b'MFA child')

    def test_failure_propagates(self):
        with self.assertRaises(subprocess.CalledProcessError):
            run([sys.executable,'-c','raise SystemExit(7)'],check=True)

    def test_timeout_stops_child(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run([sys.executable,'-c','import time; time.sleep(20)'],timeout=.1)
