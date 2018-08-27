from unittest import TestCase
from models import Hive
from itertools import chain
from storage_models import NetworkEntry, connect
from utils import is_addr, is_network, is_supernet, validate_net_data

right_network = [
    "10.0.0.0/24",
    "10.11.0.0/16",
    "10.12.255.255/32",
    "10.23.41.43/31",
    "89.23.14.0/27",
    "8.0.0.0/8"
]

wrong_network = [
    "10.23.31.14",
    "12.23.41.12/142",
    "23.41.14.1",
    "127.0.0.1"
]

right_host = [
    "127.0.0.1",
    "127.0.0.1/32",
    "23.41.12.13",
    "93.23.15.42/32"
]

wrong_host = [
    "13.41.1.123/2",
    "3.13.3.4/31",
    "3.2.2"
]

subnet = "192.168.23.0/25"
supernet = "192.168.23.0/24"
omeganet = "10.0.0.0/24"


class TestHive(TestCase):

    host = "192.168.93.129"
    db = 'test_hive'

    def setUp(self):
        connect(host=self.host, db=self.db)
        NetworkEntry.objects().delete()

    def __init__(self, *args, **kwargs):
        super(TestHive, self).__init__(*args, **kwargs)
        connect(self.host, self.db)

    def test_validate(self):

        # Must be False because wrong format, e.g. nets must be in dict format
        for x in chain(wrong_network, right_network):
            self.assertEqual(validate_net_data(x), False)

        net_data1 = {
            "value": "192.168.34.4",
            "type": "host"
        }

        net_data2 = {
            "value": "192.168.34.0/24",
            "type": "network"
        }

        net_data3 = {
            "value": "192.168.34.4",
            "type": "host",
            "os": "Linux",
            "ports": [21, 22, 80, 443]
        }

        #Must be True
        for net in [net_data1, net_data2, net_data3]:
            self.assertEqual(validate_net_data(net),True)

    def test_is_addr(self):
        for x in right_host:
            self.assertEqual(is_addr(x), True, x)
        for y in wrong_host:
            self.assertEqual(is_addr(y), False, y)

    def test_is_network(self):
        for x in right_network:
            self.assertEqual(is_network(x), True)
        for y in wrong_network:
            self.assertEqual(is_network(y), False)

    def test_is_supernet(self):

        hive = Hive(self.host, self.db)

        # First we need to add these networks to hive
        self.assertEqual(hive.add_network(subnet), True)
        self.assertEqual(hive.add_network(supernet), True)

        # Set supernet to net
        self.assertEqual(hive.set_supernet(subnet, supernet), True)

        # Must be False
        self.assertEqual(is_supernet(subnet, omeganet), False)

        # Must be True
        self.assertEqual(is_supernet(subnet, supernet), True)

    def test_is_added(self):

        hive = Hive(self.host, self.db)

        # Must be False
        for net in right_network:
            self.assertEqual(hive.is_added(net), False)

        # Then add these networks to the hive
        for net in right_network:
            hive.add_network(net)

        # Must be True
        for net in right_network:
            self.assertEqual(hive.is_added(net), True)

    def test_add_network(self):
        hive = Hive(self.host, self.db)

        # Must catch ValueError bacause each net has a wrong format
        for y in wrong_network:
            self.assertRaises(ValueError, hive.add_network, y)

        # Must return True because these net's formats are valid.
        for x in right_network:
            self.assertEqual(hive.add_network(x), True)

    def test_add_child_to_net(self):
        hive = Hive(self.host, self.db)

        net = "10.0.0.0/24"

        subnet1 = "10.0.0.0/25"
        subnet2 = "10.0.0.128/25"

        # Must be failed because net is not added yet
        self.assertRaises(ValueError, hive.add_child_to_net, net, subnet1)
        self.assertRaises(ValueError, hive.add_child_to_net, net, subnet2)

        # Create set of NetworkEntry before addition a net child to it
        self.assertEqual(hive.add_network(net), True)
        self.assertEqual(hive.add_network(subnet1), True)
        self.assertEqual(hive.add_network(subnet2), True)

        # Must be true
        self.assertEqual(hive.add_child_to_net(net, subnet1), True)
        self.assertEqual(hive.add_child_to_net(net, subnet2), True)

    def test_add_host(self):

        hive = Hive(self.host, self.db)

        for x in right_host:
            self.assertEqual(hive.add_host(x), True, x)

        for y in wrong_host:
            self.assertEqual(hive.add_host(y), False, y)

    def test_get_supernet(self):
        hive = Hive(self.host, self.db)

        # Must be false, because these news are not added yet
        self.assertEqual(hive.set_supernet(subnet, supernet), False)

        # First we need to add these networks to hive
        self.assertEqual(hive.add_network(subnet), True)
        self.assertEqual(hive.add_network(supernet), True)

        # Set supernet to net
        self.assertEqual(hive.set_supernet(subnet, supernet), True)

        # Check if a supernet is a parent for subnet
        self.assertEqual(hive.get_supernet(subnet), supernet)

    def test_set_supernet(self):
        hive = Hive(self.host, self.db)

        # Must be false, because these news are not added yet
        self.assertEqual(hive.set_supernet(subnet, supernet), False)

        # First we need to add these networks to hive
        self.assertEqual(hive.add_network(subnet), True)
        self.assertEqual(hive.add_network(supernet), True)

        # Then set_supernet
        hive.set_supernet(subnet, supernet)

        # Check if a supernet is a parent for subnet
        self.assertEqual(hive.get_supernet(subnet), supernet)

    def test_get_children(self):
        hive = Hive(self.host)
        self.assertEqual(hive.add_network(subnet), True)
        self.assertEqual(hive.add_network(supernet), True)

        # Add subnet to supernet as a child
        self.assertEqual(hive.add_child_to_net(supernet, subnet), True)

        # Check if a subnet is a child of a supernet
        self.assertEqual(subnet in hive.get_children(supernet), True)
