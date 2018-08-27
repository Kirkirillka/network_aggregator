import ipaddress
import re

from mongoengine import connect

from storage_models import NetworkEntry, NETWORK


class Hive:
    """ Description: A Class to hide all functionality of working with MongoDB databases
        It should work with the following model:

        {
            "type":["address","network"],
            "value": "Data stored in CIDR format",
            "id":"Don't exactly know whether it's necessary for further interaction",
            "supernet": "Link to uplink supernet. Should be lazy relation in term of pymongo I suggest",
            "children": ["Must be a array with links to children"]
        }

        Methods:
            add_network(net_data:json): pass
            add_host(host_data:json): pass
            get_supernet(network_address): pass
            get_children(network_address): pass
    """

    def __init__(self, host, db="network_storage"):
        self.host = host
        self.db = db

    def __init_hive__(self):
        # Init first connection and choose database name
        self.conn = connect(self.host, database=self.db)

    @staticmethod
    def _validate(net_data):
        """
        # A function to check if supplied net_data meets model's requirement. Thus net_data must be a dict with
        specified fields

        Examples of net_data:
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
                        "ports": [21, 22, 80 ,443]
                        }


        :param net_data: a dict with specified fields .
        :return: True if net_data has required fields and they are in valid formats otherwise False.
        """

        # These fields must be in supplied net_data
        required_fields = ['value', 'type']
        # Extra fields are needed to just help remember what fields can be there in applied data
        extra_fields = ['os', 'ports', 'users', 'supernet']

        # Supplied data must be in dictionary form
        if not isinstance(net_data, dict):
            return False

        # Check whether supplied dictionary has all required fields
        if not all(field in net_data for field in required_fields):
            return False

        return True

    @staticmethod
    def is_addr(addr):
        """
            Checks if supplied string is valid host address. Can be both 192.168.0.23 or 192.168.0.23/32 (CIDR format).
            Only IPv4 right now.
        :param addr: a string represented a host address.
        :return: True if a string is valid host address otherwise false.
        """
        # It should be better to insert several patterns for both IPv4/IPv6.
        # Although, I haven't enough time I have put only pattern for x.x.x.x/24 IPv4 networks
        patterns = [r'^(\d{1,3}).(\d{1,3}).(\d{1,3}).(\d{1,3})(\/32)?$']

        if any(re.match(pattern, addr) for pattern in patterns):
            return True
        return False

    @staticmethod
    def is_network(net):
        """
            Checks if supplied string is valid CIDR network address (only IPv4).
        :param net:  a string to validate CIDR format.
        :return: True if a given string is a valid CIDR network address otherwise False.
        """
        # It should be better to insert several patterns for both IPv4/IPv6.
        # Although, I haven't enough time I have put only pattern for x.x.x.x/24 IPv4 networks
        patterns = [r'^(\d{1,3}).(\d{1,3}).(\d{1,3}).(\d{1,3})\/([1-3]?[0-9]?)$']

        if any(re.match(pattern, net) for pattern in patterns):
            return True
        return False

    @staticmethod
    def is_supernet(net, supernet):
        """
            Checks for given net that it's overlapped by supplied supernet,
                e.g. 192.168.13.0/25 is subnet of 192.168.13.0/24.
            Both net and supernet must be given in CIDR format (IPv4 only).
        :param net: a string represented network address in CIDR format to validate it's overlapped by supernet.
        :param supernet: a string represented network address in CIDR format which mask prefix is less than a given one.
        :return: True if net is overlapped by supernet, e.g net is a subnet of supernet.
        """
        if not (Hive.is_network(net) and Hive.is_network(supernet)):
            return False

        foo = ipaddress.ip_network(net)
        bar = ipaddress.ip_network(supernet)

        return foo.overlaps(bar)

    def is_added(self, net):
        """
            Checks if supplied net (can be both network or host address in CIDR format) is added to hive.

        :param net:  A string in CIDR format (only IPv4).
        :return: True of False whether a net exists in hive.
        """
        if any(x(net) for x in [self.is_network, self.is_addr]):
            net = NetworkEntry.objects(value=net)
            return bool(net)
        else:
            ValueError('A supplied network is not in a valid format.')

    def add_network(self, net_data: str):
        """
            Add supplied network data as a NetworkEntry into storage. net_data can be a string with network address
            or specific dictionary with required fields.
            Only IPv4 for now.

            Example of a dictionary:

            {
                "fields":"192.168.13.0/24",
                "type":"network"
            }

            TODO: implement a method to add NetworkEntry by given net_data in dict format.


        :param net_data: a string or a dict with required information about network address to add into storage.
        :return: True if a network was inserted successfully otherwise False.
        """

        if not self._validate(net_data):
            if self.is_network(net_data):
                net = NetworkEntry(value=net_data, type=NETWORK)
                net.save()
            else:
                raise ValueError('A supplied net_data is not in a valid format.')
        else:
            # Provide arguments as **kwargs key-value pairs
            net = NetworkEntry(**net_data)
            net.save()
        return True

    def add_host(self, host_data: str):
        """
                    Add supplied host data as a NetworkEntry into storage. host_data can be a string with host address
                    or specific dictionary with required fields.
                    Only IPv4 for now.

                    Example of a dictionary:

                    {
                        "fields":"192.168.13.2",
                        "type":"host"
                    }

                    TODO: implement a method to add NetworkEntry by given net_data in dict format.

                :param host_data: a string or a dict with required information about host address to add into storage.
                :return: True if a host was inserted successfully otherwise False.
                """

        if not self._validate(host_data):
            if not self.is_addr(host_data):
                return False
            else:
                net = NetworkEntry(value=host_data, type=NETWORK)
                net.save()

                return True

        # Provide arguments as **kwargs key-value pairs
        net = NetworkEntry(**host_data)
        net.save()

        return True

    def add_child_to_net(self, net, *args):
        """
            Allows to add a list of children for given net. A list must be strings in CIDR format (IPv4 only).
            Also these children as well as a given net must be already added to hive before assignment to the net.
            It returns True if children were successfully appended to net's children list.
            Otherwise it returns False either there is no net in hive.
            If given child in *args is not added, then it creates
             a new Network Entry with specified network address before assignment.
        :param net: A string in CIDR format (only IPv4) to add children networks to.
        :param args: A list of strings in CIDR format (only IPV4) to describe children's network values.
        :return: True if children were successfully appended to net's children list.
        """

        net = NetworkEntry.objects(value=net).first()
        # If target network exists
        if net:
            # For all child which is valid network or net_address, etc. 10.0.0.0/24 or 127.0.0.1
            for child in args:
                if any(x(child) for x in [self.is_network, ]):
                    # Check if the child is added to MongoDB.
                    # Otherwise, throw exception
                    if not self.is_added(child):
                        raise ValueError('A child network is not added to the hive before assignment to a supernet.')

                    # Need to use .first because <>.objects() returns a cursor, not an object
                    child_entry = NetworkEntry.objects(value=child).first()

                    # Check if the child is already set in children array
                    if child_entry not in net.children:
                        net.children.append(child_entry)
                        net.save()
                    return True
                else:
                    raise ValueError('A supplied child network is not in a valid format.')
        raise ValueError('A supernet is not found in the hive.')

    def set_supernet(self, net, supernet):
        """
            Function returns set supernet for specific supplied net.
            Both net and supernet must be added to hive and connected before.
            Check other function to see how to add and connect nets to each other.

        :param net: a string in CIDR format (only IPv4), which will be linked to supplied supernet
        :param supernet: a string in CIDR format (only IPv4), to be set as supernet.
            A NetworkEntry with that supernet value may not have that net as one of its child.
        :return: True if set successfully. False if either format is invalid or nets were not added.
        """

        # If input is not valid networks
        if not all(self.is_network(foo) for foo in (net, supernet)):
            return False

        # If nets are not added:
        if not all(self.is_added(foo) for foo in (net, supernet)):
            return False

        added_net = NetworkEntry.objects(value=net).first()
        added_supernet = NetworkEntry.objects(value=supernet).first()

        added_net.supernet = added_supernet

        added_net.save()

        return True

    def get_supernet(self, network_address):
        """
            Return a string which shows a network in CIDR format, that
             was assigned to specified network as supernet.
        :param network_address: a string in CIDR format (only IPv4) what supernet will be looked up to.
        :return: a string of supernet value in CIDR format.
        """

        net = NetworkEntry.objects(value=network_address).first()
        return str(net.supernet.value)

    def get_children(self, network_address):
        """
            Return a list of children for given network.
        :param network_address: a string in CIDR format.
        :return: a list of strings described children in CIDR format.
        """

        net = NetworkEntry.objects(value=network_address).first()
        children = net.children

        return list(child.value for child in children)


class Aggregator():
    """ This class and the whole logic are based on
            https://github.com/grelleum/supernets.git

        Thank you, Grem Mueller @grlleum for such good aggregation algorithm!
    """

    def __init__(self):
        self.max_supernet_prefix = 0
        self._networks = {}
        self._prefixes = {}

    def _add_network(self,network):
        """ Adds network(s) to the global networks dictionary.
        Since network is a key value, duplicates are inherently removed.
        """

        def add_network_to_prefixes(network):
            """ Adds networks to the prefix dictionary.
            The prefix dictionary is keyed by prefixes.
            Networks of the same prefix length are stored in a list.
            """
            prefixes = self._prefixes
            prefix = network.prefixlen
            if not prefixes.get(prefix,None):
                #Prepare list to safely appent
                prefixes[prefix] = []
            prefixes[prefix].append(network)


        networks = self._networks
        if network not in networks:
            networks[network] = network.prefixlen
            add_network_to_prefixes(network)

    def _delete_network(self,*args):
        """Removes one of more networks from the global networks dictionary."""
        networks = self._networks
        for network in args:
            networks.pop(network, None)

    def _prepare_input(self,argv):

        for line in argv:
            network = ipaddress.ip_network(line, strict = False)
            self._add_network(network)

    def _compare_networks_of_same_prefix_length(self,prefix_list):

        def find_existing_supernet(network):
            """ This function checks if a subnet is part a of an existing supernet."""
            result = None
            for prefix in range(network.prefixlen - 1, 0, -1):
                super_network = network.supernet(new_prefix=prefix)
                if super_network in self._networks:
                    result = super_network
                    break
            return result

        previous_net = None
        for current_net in prefix_list:
            existing_supernet = find_existing_supernet(current_net)
            if existing_supernet:
                self._delete_network(current_net)
            elif previous_net is None:
                previous_net = current_net
            else:
                # Calculate a one bit larger subet and see if they are the same.
                supernet1 = previous_net.supernet(prefixlen_diff=1)
                supernet2 = current_net.supernet(prefixlen_diff=1)
                if supernet1 == supernet2:
                    self._add_network(supernet1)
                    self._delete_network(previous_net, current_net)
                    previous_net = None
                else:
                    previous_net = current_net

    def _process_prefixes(self,prefix=0):
        """Read each list of networks starting with the largest prefixes."""
        prefixes = self._prefixes

        for x in range(128, prefix, -1):
            if x in prefixes:
                self._compare_networks_of_same_prefix_length(sorted(prefixes[x]))

    def aggregate(self,argv):
        self._prepare_input(argv)
        self._process_prefixes()
        return list(str(net) for net in self._networks)