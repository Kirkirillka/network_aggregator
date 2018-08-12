from unittest import TestCase
from models import Hive
from storage_models import NetworkEntry, connect

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


class TestHive(TestCase):

    host = "192.168.44.128"
    db = 'test_hive'

    def setUp(self):
        connect(host=self.host, db=self.db)
        NetworkEntry.objects().delete()

    def __init__(self, *args, **kwargs):
        super(TestHive, self).__init__(*args, **kwargs)
        connect(self.host, self.db)

    def test_is_addr(self):
        hive = Hive
        for x in right_host:
            self.assertEqual(hive.is_addr(x), True, x)
        for y in wrong_host:
            self.assertEqual(hive.is_addr(y), False, y)

    def test_is_network(self):
        hive = Hive
        for x in right_network:
            self.assertEqual(hive.is_network(x), True)
        for y in wrong_network:
            self.assertEqual(hive.is_network(y), False)

    def test_add_network(self):
        hive = Hive(self.host, self.db)

        for x in right_network:
            self.assertEqual(hive.add_network(x), True)

        for y in wrong_network:
            self.assertEqual(hive.add_network(y), False)

    def test_add_child_to_net(self):
        hive = Hive(self.host, self.db)

        net = "10.0.0.0/24"

        subnet1 = "10.0.0.0/25"
        subnet2 = "10.0.0.128/25"

        # Must be failed because net is not added yet
        self.assertEqual(hive.add_child_to_net(net, subnet1), False)
        self.assertEqual(hive.add_child_to_net(net, subnet2), False)

        # Create a net NetworkEntry before addition a net child to it
        # Must be true
        self.assertEqual(hive.add_network(net), True)
        self.assertEqual(hive.add_child_to_net(net, subnet1), True)
        self.assertEqual(hive.add_child_to_net(net, subnet2), True)

    def test_add_host(self):

        hive = Hive(self.host, self.db)

        for x in right_host:
            self.assertEqual(hive.add_host(x), True, x)

        for y in wrong_host:
            self.assertEqual(hive.add_host(y), False, y)

    def test_get_supernet(self):

        subnet = "192.168.23.0/25"
        supernet = "192.168.23.0/24"

        hive = Hive(self.host,self.db)

        # Must be false, because these news are not added yet
        self.assertEqual(hive.set_supernet(subnet, supernet), False)

        # First we need to add these networks to hive
        self.assertEqual(hive.add_network(subnet), True)
        self.assertEqual(hive.add_network(supernet), True)

        # Set supernet to net
        self.assertEqual(hive.set_supernet(subnet, supernet), True)

        # Check if a supernet is a parent for subnet
        self.assertEqual(hive.get_supernet(subnet), supernet)

    def test_get_children(self):

        subnet = "192.168.23.0/25"
        supernet = "192.168.23.0/24"

        hive = Hive(self.host)
        self.assertEqual(hive.add_network(subnet), True)
        self.assertEqual(hive.add_network(supernet), True)

        # Add subnet to supernet as a child
        self.assertEqual(hive.add_child_to_net(supernet, subnet), True)

        # Check if a subnet is a child of a supernet
        self.assertEqual(subnet in hive.get_children(supernet), True)