from unittest import TestCase
from models import Scanner

class TestScanner(TestCase):
    def test_add_net_to_scope(self):
        self.skipTest('not implemented')

    def test_run_scan_sync(self):

        hosts = ['127.0.0.1', '192.168.0.102', '192.168.0.1', '8.8.8.8']

        scanner = Scanner()

        for host in hosts: scanner.add_net_to_scope(host)

        scanner.run_scan_sync()
