import ipaddress
from multiprocessing.pool import ThreadPool as Pool
from pprint import pprint as print

from mongoengine import connect

import nmap
from consts import DEFAULT_PORT_RANGE, MAX_RANGE
from consts import TCP_SCAN, UDP_SCAN, SERVICE_VERSION_SCAN
from consts import HORIZONTAL_MODE, VERTICAL_MODE, MAX

from consts import DEBUG

from storage_models import NetworkEntry, NETWORK
from utils import normalize
from utils import validate_net_data, is_addr, is_network

from logtools import aggregated, analyze


class Hive:
    """
        Class to hide all functionality of working with MongoDB databases.

        Args:
            host (str): IPv4 numerical or domain name of MongoDB instance to connect to. It's considered to use the
                standard port TCP\27017.
            db (str): Name for database to connect to. Default is "network_storage".

        Notes:
            It should work with the following model:

            {
                "type":["address","network"],
                "value": "Data stored in CIDR format",
                "id":"Don't exactly know whether it's necessary for further interaction",
                "supernet": "Link to uplink supernet. Should be lazy relation in term of pymongo I suggest",
                "children": ["Must be a array with links to children"]
            }
    """

    def __init__(self, host, db="network_storage"):
        self.host = host
        self.db = db

    def __init_hive__(self):
        # Init first connection and choose database name
        self.conn = connect(self.host, database=self.db)

    def is_added(self, net):
        """
            Checks if supplied net (can be both network or host address in CIDR format) is added to hive.

            Raises:
                ValueError: A supplied net information is not in valid format. Net must be string in CIDR format.

        :param net: str:  A string in CIDR format (only IPv4).
        :return: bool: True of False whether a net exists in hive.
        """
        if any(x(net) for x in [is_network, is_addr]):
            net = NetworkEntry.objects(value=net)
            return bool(net)
        else:
            ValueError('A supplied network is not in a valid format.')

    def _add_net_entry(self, net_data, type: str):
        # TODO: use _add_net_entry to add new entry to hive implicity. add_network and add_host must use that function.
        pass

    def add_network(self, net_data):
        """
            Add supplied network data as a NetworkEntry into storage. net_data can be a string with network address
            or specific dictionary with required fields. Only IPv4 for now.

            Examples:
                dictionary_example = {
                    "fields":"192.168.13.0/24",
                    "type":"network"
                }

            Raises:
                ValueError: A supplied net information is not in valid format. Net must be string in CIDR format.

            TODO: implement a method to add NetworkEntry by given net_data in dict format.
            TODO: make a test and check its correctness.
            TODO: test saving NetworkEntry by dict supplying.

        :param net_data: str or dict: a string or a dict with required information about network
            address to add into storage.
        :return: bool: True if a network was inserted successfully otherwise False.
        """

        # If net_data is valid dictionary
        if isinstance(net_data, dict) and validate_net_data(net_data):
            net = NetworkEntry(**net_data)
            net.save()

            return True

        # If net_data is valid string
        if isinstance(net_data, str) and is_network(net_data):
            net = NetworkEntry(value=net_data, type=NETWORK)
            net.save()

            return True

        raise ValueError('A supplied net_data is not in a valid format.')

    def add_host(self, host_data: str):
        """
            Add supplied host data as a NetworkEntry into storage. host_data can be a string with host address
            or specific dictionary with required fields. Only IPv4 for now.

            Examples:
                dictionary_example = {
                            "fields":"192.168.13.2",
                            "type":"host"
                        }

            TODO: implement a method to add NetworkEntry by given net_data in dict format.
            TODO: test saving NetworkEntry by dict supplying.
            TODO: check function whether it works properly. Pay attention on creation an entry by dict.

        :param host_data: str or dict: A string or a dict with required information about host
            address to add into storage.
        :return: bool: True if a host was inserted successfully otherwise False.
        """

        # If net_data is valid dictionary
        if isinstance(host_data, dict) and validate_net_data(host_data):
            net = NetworkEntry(**host_data)
            net.save()

            return True

        # If net_data is valid string
        if isinstance(host_data, str) and is_addr(host_data):
            net = NetworkEntry(value=host_data, type=NETWORK)
            net.save()

            return True

        raise ValueError('A supplied net_data is not in a valid format.')

    def add_child_to_net(self, net, *args):
        """Allows to add a list of children for given net.

            Notes:
                A list must be strings in CIDR format (IPv4 only).
                Also these children must be already added to hive before assignment to the net as well as a given net.
                If given child in *args is not added, then it DOESN'T create a new Network Entry. Make sure you add a
                new NetworkEntry by yourself otherwise you raise an exception.

            Raises:
                ValueError: A child network was not added to the hive before assignment to a supernet.
                ValueError: A supplied net information is not in valid format. Net must be string in CIDR format.
                ValueError: Supernet is not found in the hive.

        :param net: str: A string in CIDR format (only IPv4) to add children networks to.
        :param args: list of str: A list of strings in CIDR format (only IPV4) to describe children's network values.
        :return: bool: True if children were successfully appended to net's children list.
        """

        # Try to find subnet in the hive
        net = NetworkEntry.objects(value=net).first()
        # If target network exists
        if net:
            # For all child which is valid network or net_address, etc. 10.0.0.0/24 or 127.0.0.1
            for child in args:
                if any(x(child) for x in [is_network, ]):
                    # Check if the child is added to MongoDB.
                    # Otherwise, throw exception
                    if not self.is_added(child):
                        raise ValueError('A child network was not added to the hive before assignment to a supernet.')

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
            Set supernet for specific supplied net.

            Notes:
                Both net and supernet must be added to hive and connected before.
                Check other function to see how to add and connect nets to each other.

        :param net: str: a string in CIDR format (only IPv4), which will be linked to supplied supernet
        :param supernet: str: a string in CIDR format (only IPv4), to be set as supernet.
            A NetworkEntry with that supernet value may not have that net as one of its child.
        :return: bool: True if set successfully. False if either format is invalid or nets were not added.
        """

        # If input is not valid networks
        if not all(is_network(foo) for foo in (net, supernet)):
            return False

        # If nets are not added:
        if not all(self.is_added(foo) for foo in (net, supernet)):
            return False

        # Fount entries in the hive.
        # We need to use .first methods, because .objects returns a cursor.
        added_net = NetworkEntry.objects(value=net).first()
        added_supernet = NetworkEntry.objects(value=supernet).first()

        added_net.supernet = added_supernet

        added_net.save()

        return True

    def get_supernet(self, network_address):
        """
            Return a string which shows a network in CIDR format, that was assigned to specified network as supernet.

        :param network_address: str: A string in CIDR format (only IPv4) what supernet will be looked up to.
        :return: str: A string of supernet value in CIDR format.
        """

        net = NetworkEntry.objects(value=network_address).first()
        return str(net.supernet.value)

    def get_children(self, network_address):
        """
            Return a list of children for given network.

        :param str: network_address: A string in CIDR format.
        :return: list of str: A list of strings described children in CIDR format.
        """

        net = NetworkEntry.objects(value=network_address).first()
        children = net.children

        return list(child.value for child in children)


class Aggregator:
    """

        Note:
            This class and logic are based on
            https://github.com/grelleum/supernets.git

            Also, there permissive prefix added to help the algo to find supernet with prefix in allowable range.
            See Examples section to look what it means.
            Thank you, Grem Mueller @grlleum for such good aggregation algorithm!

        Examples:
            We have two nets - 192.168.0.0/25 and 192.168.1.0/25. Let's suppose permissive prefix is 1.
            Then the algorithm works such way:
                192.168.0.0/25 -> 192.168.0.0/24
                192.168.1.0/25 -> 192.168.1.0/24
            You see it runs only once. Event prefix is /24, supernets are not same, so these nets are not aggregated.

            Let permissive prefix be 2:
                192.168.0.0/25 -> 192.168.0.0/24 -> 192.168.0.0/23
                192.168.1.0/25 -> 192.168.1.0/24 -> 192.168.0.0/23
            Now that fits /23 prefix, so networks will be aggregated. We can use 192.168.0.0/23 to describe
            these networks.

        TODO: comment it properly
    """

    def __init__(self):
        self.max_supernet_prefix = 0
        self._networks = {}
        self._prefixes = {}

    @property
    def permissive_prefix(self):
        if hasattr(self, '_permissive_interval'):
            return getattr(self, '_permissive_interval')
        else:
            return 1

    @permissive_prefix.setter
    def permissive_prefix(self, value):
        if isinstance(value, int) and value in range(1, 33):
            setattr(self, '_permissive_interval', value)
        else:
            raise ValueError('Permissive prefix must be in {1..32} range.')
        
    @property
    def swap_prefix(self):
        """
        TODO: make a unit test
        :return:
        """
        if hasattr(self, '_swap_interval'):
            return getattr(self, '_swap_interval')
        else:
            return 1
    
    @swap_prefix.setter
    def swap_prefix(self, value):
        """
        TODO: make a unit test
        :param value:
        :return:
        """
        if isinstance(value, int) and value in range(1, 32):
            setattr(self, '_swap_interval', value)
        else:
            raise ValueError('Swap prefix must be in {1..31} range.')

    @property
    def mode(self):
        """
        TODO: make a unit test
        :return:
        """
        if hasattr(self, '_mode'):
            return getattr(self, '_mode')
        else:
            return HORIZONTAL_MODE

    @mode.setter
    def mode(self, value):
        """
        TODO: make a unit test
        :param value:
        :return:
        """
        if isinstance(value, int) and value in range(VERTICAL_MODE+HORIZONTAL_MODE+MAX+1):
            setattr(self, '_mode', value)
        else:
            raise ValueError('Modes are: VERTICAL_MODE, HORIZONTAL_MODE, MAX')

    @property
    def networks(self):
        # TODO: make a unit test
        return list(str(net) for net in self._networks)

    def _add_network(self, network):
        """
            Adds network(s) to the global networks dictionary.
            Since network is a key value, duplicates are inherently removed.
        """

        def add_network_to_prefixes(net):
            """
                Adds networks to the prefix dictionary.
                The prefix dictionary is keyed by prefixes.
                Networks of the same prefix length are stored in a list.
            """
            prefixes = self._prefixes
            prefix = net.prefixlen
            if not prefixes.get(prefix, None):
                # Prepare list to safely appent
                prefixes[prefix] = []
            prefixes[prefix].append(net)

        networks = self._networks
        if network not in networks:
            networks[network] = network.prefixlen
            add_network_to_prefixes(network)

    def _delete_network(self, *args):
        """Removes one of more networks from the global networks dictionary."""
        networks = self._networks
        for network in args:
            networks.pop(network, None)


    def _prepare_input(self, argv):

        for line in argv:
            network = ipaddress.ip_network(line, strict=False)
            self._add_network(network)

    def _horizontal_aggregation(self, start_prefix: int):
        # Example
        # permissive interval is 2, then
        # 10.90.17.53/32 -> 10.90.17.52/31 -> 10.90.17.52/30 -> prefix /30 -> unite!
        # 10.90.17.55/32 -> 10.90.17.54/31 -> 10.90.17.52/30 -> prefix /30 -> unite!

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
        for current_net in self._prefixes[start_prefix]:
            if DEBUG:
                analyze(current_net)
            existing_supernet = find_existing_supernet(current_net)
            if existing_supernet:
                aggregated(current_net, '---', '---')
                self._delete_network(current_net)
            elif previous_net is None:
                previous_net = current_net
            else:
                # For prefixlen in permissive interval try to find overlapped networks. If they overlap, then combine
                # into one and immediately break.

                if self.mode & MAX:

                    is_done = False
                    # Check bound in range 1,31
                    start = current_net.prefixlen - 1
                    stop = self.permissive_prefix
                    if not 0 < start <= 31 or not 0 < stop <= 30:
                        continue

                    for prefixlen in range(start, stop, -1 ):
                        supernet1 = previous_net.supernet(new_prefix=prefixlen)
                        supernet2 = current_net.supernet(new_prefix=prefixlen)
                        if supernet1 == supernet2:
                            aggregated(previous_net, current_net, supernet1)
                            self._add_network(supernet1)
                            self._delete_network(previous_net, current_net)
                            previous_net = None

                            is_done = True

                            break
                        # else:
                        #    previous_net = current_net
                    if not is_done:
                        previous_net = current_net
                else:
                    supernet1 = previous_net.supernet(prefixlen_diff=2)
                    supernet2 = current_net.supernet(prefixlen_diff=2)
                    if supernet1 == supernet2:
                        aggregated(previous_net, current_net, supernet1)
                        self._add_network(supernet1)
                        self._delete_network(previous_net, current_net)
                        previous_net = None

    def _vertical_aggregation(self, start_prefix: int):

        # Make a copy of net keys for looping around it.
        # network_keys = sorted(self._networks.keys())
        #
        # # Take first element in net list. Compare it to others. If it overlaps the other one, then the other
        # # will be removed.
        # #
        # # Example:
        # # 1 first->192.168.0.0/24, overlaps->192.168.0.23/32, 192.168.0.24/25, 127.0.0.1/32, 8.8.8.8/24
        # # 2 first->192.168.0.0/24, overlaps->192.168.0.24/25, 127.0.0.1/32, 8.8.8.8/24
        # # 3 first->192.168.0.0/24, diffirent->127.0.0.1/32, 8.8.8.8/24
        # # 4 first->192.168.0.0/24, 127.0.0.1/32, different->8.8.8.8/24
        # # 5 192.168.0.0/24, first->127.0.0.1/32, different->8.8.8.8/24
        # # 6 192.168.0.0/24, 127.0.0.1/32, first->8.8.8.8/24
        #
        # for index, net in enumerate(network_keys):
        #     for next_net in network_keys[index + 1:]:
        #         # If current net is the same as next_net
        #         if net is next_net:
        #             continue
        #         # If overlaps then delete from left keys
        #         if net.overlaps(next_net):
        #             network_keys.remove(next_net)
        #
        # # Clean up from overlapped net
        # bunch_copy = self._networks.copy()
        # for net in bunch_copy:
        #     if net not in network_keys:
        #         self._networks.pop(net)
        prefixes = self._prefixes

        # For each net with specified prefixes
        for net in prefixes[start_prefix]:

            if DEBUG:
                analyze(net)

            # Check if net is arleady processed and deleted
            if net in self._networks:
                # Check bound in range 1,31
                start = start_prefix-1
                stop = self.swap_prefix
                if not 0 < start <= 31 or not 0 < stop <= 30:
                    continue

                # For each prefix less than net has itself
                for large_prefix in range(start, stop, -1):
                    # Check if prefix exists
                    if large_prefix in prefixes:
                        # For each new with less prefix
                        for large_net in prefixes[large_prefix]:

                            if self.mode & MAX:
                                for prefixlen in range(min(large_net.prefixlen, net.prefixlen)-1, stop, -1):
                                    supernet1 = net.supernet(new_prefix=prefixlen)
                                    supernet2 = large_net.supernet(new_prefix=prefixlen)
                                    if supernet1 == supernet2:
                                        aggregated(net, large_net, supernet1)
                                        self._add_network(supernet1)
                                        self._delete_network(net, large_net)
                                        break

                            else:
                                # Check if large_net was arleady processed
                                if large_net in self._networks:
                                    if large_net.overlaps(net):
                                        aggregated(net, large_net, large_net)
                                        self._delete_network(net)





    def _process_prefixes(self, stop_prefix=0):
        """Read each list of networks starting with the largest prefixes."""
        prefixes = self._prefixes

        def make_clean_up_after_prefix_process():

            # Make a copy of net keys for looping around it.
            network_keys = sorted(self._networks.keys())

            # Take first element in net list. Compare it to others. If it overlaps the other one, then the other
            # will be removed.
            #
            # Example:
            # 1 first->192.168.0.0/24, overlaps->192.168.0.23/32, 192.168.0.24/25, 127.0.0.1/32, 8.8.8.8/24
            # 2 first->192.168.0.0/24, overlaps->192.168.0.24/25, 127.0.0.1/32, 8.8.8.8/24
            # 3 first->192.168.0.0/24, diffirent->127.0.0.1/32, 8.8.8.8/24
            # 4 first->192.168.0.0/24, 127.0.0.1/32, different->8.8.8.8/24
            # 5 192.168.0.0/24, first->127.0.0.1/32, different->8.8.8.8/24
            # 6 192.168.0.0/24, 127.0.0.1/32, first->8.8.8.8/24

            for index, net in enumerate(network_keys):
                for next_net in network_keys[index + 1:]:
                    # If current net is the same as next_net
                    if net is next_net:
                        continue
                    # If overlaps then delete from left keys
                    if net.overlaps(next_net):
                        network_keys.remove(next_net)

            # Clean up from overlapped net
            bunch_copy = self._networks.copy()
            for net in bunch_copy:
                if net not in network_keys:
                    self._networks.pop(net)

        # To support both IPv6 and IPv4, start from prefix 128 to 1.
        # Example: 128...32...24...1
        if self.mode & HORIZONTAL_MODE:
            for x in range(128, stop_prefix, -1):
                if x in prefixes:
                    self._horizontal_aggregation(x)


        # Make clean up on hosts with similar host address but diffirent mask.
        if self.mode & VERTICAL_MODE:
            for x in range(128, stop_prefix, -1):
                if x in prefixes:
                    self._vertical_aggregation(x)

    def aggregate(self, argv):
        # Prepare networks and prefixes
        self._prepare_input(argv)
        # Process data
        self._process_prefixes()
        # Return only strings in CIDR format.
        return list(str(net) for net in self._networks)

    def to_csv(self, path='networks.csv'):
        """
            Examples:
                id, label
                1   127.0.0.1/32
                2   192.168.0.0/24
                3   192.168.0.1/32
                ...

           TODO: make a unit test

        :param path:
        :return:
        """

        with open(path,'w+') as file:

            file.write("id,label\n")

            for index, net in enumerate(self.networks):
                file.write('{},"{}"\n'.format(index,net))



class Scanner:
    """
        A class to process scanning with nmap on specified hosts using thread pool

        To use that class you should create an instance of the class, update scanning host list by add_net_to_scope.
        After use run_scan_sync function to start scanning synchronously, so that execution would be blocked until all
        scanning hosts are done. Another way is to use asynchronous way to exec, but that is not implemented.

        Notes:
            You can add ether IPv4 address or IPv4 net in CIDR format - it will be normalized to CIDR format either way.
            Also, you can specify scanning mode - TCP scanning( -sT nmap option), UDP scanning (-sU),
            Service Version detection (-sV). You can  use variables from consts.py module to specify what mode you need
            to use during scanning. After scan process is done, the result is just printed in human-readable form.

        Args:
            threads: count of threads to start simultaneously in pool during scanning. Default is 2 threads.

        Attributes:
            networks: property to return list of added networks to scan.
                Returning networks are normalized.
            threads: property to set and return count of threads to start scanning simultaneously.
            mode: property to set and return specified mode of scanning. Now TCP scanning, UDP scanning,
                Service Version detection mode are added. Constants to specify modes are in consts.py module.
                Default mode is TCP_SCAN.
            port_range: property to set and return port range list. Format of returning and setting
                s r'\d-\d' (e.g. '1-1000'). Min port is 1, max port is 65535. Min port must be less than max port.


        TODO: implement asynchronous scanning.
        TODO: implement several function to export scan result in diffirent format (CSV, XML, JSON, greppable).
        TODO: code hw to use result of scan in futher processing, not simply put on the screen.
    """

    def __init__(self, threads=2, **args):
        self._network_targets = set()
        self._thread_count = threads

    @property
    def networks(self):
        """
            Returns list of hosts to scan. Can be updated using of add_net_to_scope function.

            TODO: make a unit test

        :returns: list of str
        """

        return sorted(self._network_targets)

    @property
    def threads(self):
        """
            Returns count of threads which will be started in pool during scanning simultaneously.

            TODO: make a unit test

        :return: int
        """
        return self._thread_count

    @threads.setter
    def threads(self, value):
        """
            Set count of threads to start pool for scanning.

            TODO: make a unit test

        :param value: int
        """
        if isinstance(value, int):
            self._thread_count = value

    @property
    def mode(self):
        """
            Return mode of scanning. If it hasn't been set already, then return default TCP scan mode (TCP_SCAN const).

            TODO: make a unit test

        :return: str
        """
        if hasattr(self, '_mode'):
            mode = getattr(self, '_mode')
        else:
            mode = TCP_SCAN

        return mode

    @mode.setter
    def mode(self, value):
        """
            Set mode of scanning. Now available to set are: TCP scanning (-sT), UDP scanning (-sU) and Service
            Recognition version scanning (-sV) are allowed.

            TODO: make a unit test

        :param value: TCP_SCAN, UDP_SCAN, SERVICE_VERSION_SCAN
        """
        if value in (TCP_SCAN, UDP_SCAN, SERVICE_VERSION_SCAN):
            setattr(self, '_mode', value)

    @property
    def port_range(self):
        """
            Return port range for scanning. Ports can be in range 1 to 65535. Return format is r"\d-\d", e.g. 1-10000.

            Checks if object already has saved _ports attribute, otherwise set that to DEFAULT_PORT_RANGE.
            It could be better idea than initialize it in __init__ function, because such boundary checks requires
            a lot of coding, I considered __init__ function to be less a bit.

            TODO: make a unit test

        :return: str
        """
        if hasattr(self, '_ports'):
            range_value = getattr(self, '_ports')
        else:
            range_value = DEFAULT_PORT_RANGE

        min_val, max_val = min(range_value), max(range_value)
        return '{}-{}'.format(min_val, max_val)

    @port_range.setter
    def port_range(self, value):
        """
            Set port range for scanning. Range format is r"\d-\d", e.g. you need supply a string like "1-10000".

            Raises:
                ValueError: Min port must be strictly less than max port.
                ValueError: Min port and max port must be in range of (1,65535).
                AttributeError: A port range must be in r\'\d-\d\' form.

            TODO: make a unit test

        :param value: str
        """
        import re

        if isinstance(value, str) and re.match(r'\d-\d', str):
            # Convert from str to int
            min_val, max_val = [int(_int_value) for _int_value in str.split('-')]

            # Min port can't be less than the max one.
            if min_val >= max_val:
                raise ValueError("Min port must be strictly less than max port.")

            # Max port can't be bigger than 2**16 -1, e.g. 65535
            if not all(value in MAX_RANGE for value in (min_val, max_val)):
                raise ValueError("Min port and max port must be in range of (1,65535).")

            # If all checks are passed then save it
            setattr(self, '_ports', range(min_val, max_val))
        else:
            raise AttributeError("A port range must be in r\'\d-\d\' form.")

    def add_net_to_scope(self, net):
        """
            A function to add a net network to scope to scan further.

            Notes:
                Supplied net string will be normalized to CIDR format before processing.
                As for network list storage set data structure is used, we don't need to check for duplicates of nets.

            Examples:
                192.168.0.1 (IPv4 addr) -> 192.168.0.1/32 (CIDR IPv4 net)
                192.168.0.0/24 (IPv4 net) -> arleady CIDR IPv4 net
                192.168.0.0-192.168.0.255 (address range) -> not implemented


            TODO: make a unit test
            TODO: implement address range to CIDR IPv4 net normalization

        :param net: str
        :return: bool: True if supplied net string is successfully supplied.
        """

        normalized_net = normalize(net)
        self._network_targets.add(normalized_net)
        return True

    def run_scan_sync(self):
        """
            Start thread pool simultaneously and wait until all scans are done.
            Then it combine all results into one dict and just print it out.

            Notes:
                For each net in network list start thread and process worker function upon that.
                pool.map works like Queue, e.g. we have _thread_count threads. And if amount of hosts is bigger than
                amount of threads, then left hosts will wait until a thread is joined and ready to run worker again.

            Example:
                threads: #1th #2th #3th #4th
                hosts: 127.0.0.1, 192.168.0.1, 10.0.0.1, 8.8.8.8, 172.168.13.2

                 mapping:
                 #1th - > 127.0.0.1---------------done>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                 ---#2th -> 192.168.0.1---------------done-------------------------------
                 ------#3th -> 10.0.0.1---------------done-------------------------------
                 ---------#4th -> 8.8.8.8---------------done-----------------------------
                 ----------------------------------#1th -> 172.168.13.2---------------done

            TODO: make unit test

        :return: None
        """

        # A dict where each thread will save its scan result
        result = {}

        # Special function to start nmap with specified args in a new python thread
        def worker(net):
            nm = nmap.PortScanner()
            nm.scan(net, arguments=self.mode, ports=self.port_range)

            # Combine result in non-local variable
            for scan_net in nm.all_hosts():
                result[scan_net] = nm[scan_net]

        # Create a thread pool to scan
        pool = Pool(self.threads)
        # Start pool and join the result
        pool.map(worker, [net for net in self._network_targets])

        print(result)

    def run_scan_async(self, callback):
        pass
        raise NotImplementedError
