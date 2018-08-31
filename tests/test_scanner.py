from unittest import TestCase
from models import Scanner

class TestScanner(TestCase):
    def test_add_net_to_scope(self):
        self.skipTest('not implemented')

    def test_run_scan_sync(self):

        self.skipTest('not implemented')

        hosts = ['127.0.0.1', '192.168.0.102', '192.168.0.1', '8.8.8.8']

        scanner = Scanner()

        for host in hosts: scanner.add_net_to_scope(host)

        scanner.run_scan_sync()


    def test_run_scan_sync_work(self):

        hosts = ['10.90.7.25',
                '10.90.7.9',
                '10.90.8.10',
                '10.90.8.11',
                '10.90.8.14',
                '10.90.8.18',
                '10.90.8.4',
                '10.90.8.5',
                '10.90.8.6',
                '10.90.8.9',
                '10.90.9.1',
                '10.90.9.10',
                '10.90.9.14',
                '10.90.9.4',
                '10.90.9.6',
                 ]

        scanner = Scanner()

        for host in hosts: scanner.add_net_to_scope(host)

        scanner.run_scan_sync()
