import os.path as path

from unittest import TestCase

from models import Aggregator
from utils import is_supernet, is_network, is_addr, validate_net_data
from utils import normalize

from consts import HORIZONTAL_MODE, VERTICAL_MODE, MAX

class TestAggregator(TestCase):

    def test_aggregate(self):
        self.skipTest('not nessesary')
        initial_networks = [
            "182.167.12.0/25",
            "182.167.12.128/25",
            "8.8.8.8/32"
        ]

        result_networks = [
            "182.167.12.0/24",
            "8.8.8.8/32"
        ]

        aggr = Aggregator()
        aggregated_list = aggr.aggregate(initial_networks)
        self.assertCountEqual(aggregated_list, result_networks)

    def test_aggregate_from_file(self):
        self.skipTest('not nessesary')
        aggr = Aggregator()
        aggr.permissive_prefix = 3

        samples_root_path = 'networks_samples'
        samples = list(path.join(samples_root_path, sample) for sample in ['net1', 'net2', 'net3'])

        initial_networks = []
        result_networks = ['10.16.1.0/24', '10.160.10.16/28', '185.104.104.0/22', '185.152.80.0/22', '31.13.132.0/24',
                           '31.13.134.0/23', '10.16.10.0/24', '192.168.32.0/24', '31.13.128.0/22']

        for r in samples:
            with open(r) as file:
                for net in file:
                    # To clean up after reading with \n characher
                    net = net.rstrip('\n')

                    initial_networks.append(normalize(net))

        aggregated_list = aggr.aggregate(initial_networks)

        self.assertCountEqual(aggregated_list, result_networks)

    def test_aggregate_from_itpark(self):
        #self.skipTest('not nessesary')
        aggr = Aggregator()
        aggr.permissive_prefix = 8
        aggr.swap_prefix = 8
        aggr.mode = HORIZONTAL_MODE | VERTICAL_MODE| MAX

        samples_root_path = 'networks_samples'
        samples = list(path.join(samples_root_path, sample) for sample in ['net4', ])

        initial_networks = []
        result_networks = ['10.16.1.0/24', '10.160.10.16/28', '185.104.104.0/22', '185.152.80.0/22', '31.13.132.0/24',
                           '31.13.134.0/23', '10.16.10.0/24', '192.168.32.0/24', '31.13.128.0/22']

        for r in samples:
            with open(r) as file:
                for net in file:
                    # To clean up after reading with \n characher
                    net = net.rstrip('\n')

                    initial_networks.append(normalize(net))

        aggregated_list = aggr.aggregate(initial_networks)

        from pprint import pprint as print
        print(aggregated_list)

        print(len(aggregated_list))

    def test_to_csv(self):

        self.skipTest('not nessesary')
        aggr = Aggregator()
        aggr.permissive_prefix = 24
        aggr.mode = HORIZONTAL_MODE

        samples_root_path = 'networks_samples'
        samples = list(path.join(samples_root_path, sample) for sample in ['net1', 'net2', 'net3','net4'])

        initial_networks = []
        result_networks = ['10.16.1.0/24', '10.160.10.16/28', '185.104.104.0/22', '185.152.80.0/22', '31.13.132.0/24',
                           '31.13.134.0/23', '10.16.10.0/24', '192.168.32.0/24', '31.13.128.0/22']

        for r in samples:
            with open(r) as file:
                for net in file:
                    # To clean up after reading with \n characher
                    net = net.rstrip('\n')

                    initial_networks.append(normalize(net))

        aggregated_list = aggr.aggregate(initial_networks)

        aggr.to_csv('/tmp/aggregated.csv')


    def test_my(self):

        self.skipTest('not nessesary')
        aggr = Aggregator()
        aggr.permissive_prefix = 8
        aggr.swap_prefix = 2
        aggr.mode = VERTICAL_MODE | HORIZONTAL_MODE | MAX

        nets = [
            "192.168.0.128/25",
            "172.168.0.128/17",
            "167.23.42.0/4",
            "192.168.24.0/25",
            "192.168.0.0/24",
            "10.10.10.0/24",
            '10.0.0.0/16',
            '10.0.0.0/14',


        ]


        print(aggr.aggregate(nets))

    def test_my2(self):

        self.skipTest('not nessesary')
        aggr = Aggregator()
        aggr.permissive_prefix = 6

        nets = [
            "192.168.0.128/25",
            "192.168.0.0/25",
            "192.168.0.0/24",
            "10.10.10.0/24",
            '10.0.0.0/8'

        ]


        print(aggr.aggregate(nets))




