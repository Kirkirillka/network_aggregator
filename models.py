import ipaddress
import nmap

from multiprocessing.pool import ThreadPool as Pool
from mongoengine import connect

from storage_models import NetworkEntry, NETWORK
from utils import validate_net_data, is_addr, is_network, is_supernet
from utils import normalize
from consts import ASYNCSCAN, SYNC_SCAN
from consts import TCP_SCAN, UDP_SCAN, SERVICE_VERSION_SCAN
from consts import DEFAULT_PORT_RANGE, MAX_RANGE


from pprint import pprint as print


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

    def is_added(self, net):
        """
            Checks if supplied net (can be both network or host address in CIDR format) is added to hive.

        :param net:  A string in CIDR format (only IPv4).
        :return: True of False whether a net exists in hive.
        """
        if any(x(net) for x in [is_network, is_addr]):
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

        if not validate_net_data(net_data):
            if is_network(net_data):
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

        if not validate_net_data(host_data):
            if not is_addr(host_data):
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
                if any(x(child) for x in [is_network, ]):
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
        if not all(is_network(foo) for foo in (net, supernet)):
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

    @property
    def permissive_prefix(self):
        if hasattr(self,'_permissive_interval'):
            return getattr(self,'_permissive_interval')
        else:
            return 1

    @permissive_prefix.setter
    def permissive_prefix(self, value):
        if isinstance(value,int) and value in range(1,33):
            setattr(self,'_permissive_interval',value)
        else:
            raise ValueError('Permissive prefix must be in {1..32} range.')

    def _add_network(self, network):
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
            if not prefixes.get(prefix, None):
                # Prepare list to safely appent
                prefixes[prefix] = []
            prefixes[prefix].append(network)

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

    def _compare_networks_of_same_prefix_length(self, prefix_list):
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
        for current_net in prefix_list:
            existing_supernet = find_existing_supernet(current_net)
            if existing_supernet:
                self._delete_network(current_net)
            elif previous_net is None:
                previous_net = current_net
            else:
                # For prefixlen in permissive interval try to find overlapped networks. If they overlap, then combine
                # into one and immediately break.
                is_done = False
                for prefixlen in range(1,self.permissive_prefix+1):
                    supernet1 = previous_net.supernet(prefixlen_diff=prefixlen)
                    supernet2 = current_net.supernet(prefixlen_diff=prefixlen)
                    if supernet1 == supernet2:
                        self._add_network(supernet1)
                        self._delete_network(previous_net, current_net)
                        previous_net = None

                        is_done = True

                        break
                    #else:
                    #    previous_net = current_net
                if not is_done:
                    previous_net = current_net

    def _process_prefixes(self, prefix=0):
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

            for index,net in enumerate(network_keys):
                for next_net in network_keys[index+1:]:
                    # If current net is the same as next_net
                    if net is next_net:
                        continue
                    # If overlaps then delete from left keys
                    if net.overlaps(next_net):
                        network_keys.remove(next_net)

            # Clean up from overlapped net
            for net in network_keys:
                if net not in network_keys:
                    self._networks.pop(net)

        # To support both IPv6 and IPv4, start from prefix 128 to 1.
        # Example: 128...32...24...1
        for x in range(128, prefix, -1):
            if x in prefixes:
                self._compare_networks_of_same_prefix_length(sorted(prefixes[x]))
                print(self._networks)
                print(len(self._networks))
                print('')

        #Make clean up on hosts with similar host address but diffirent mask.
        make_clean_up_after_prefix_process()

    def aggregate(self, argv):
        # Prepare networks and prefixes
        self._prepare_input(argv)
        # Process data
        self._process_prefixes()
        # Return only strings in CIDR format.
        return list(str(net) for net in self._networks)


class Scanner():
    def __init__(self, threads=2, **args):
        self._network_targets = set()
        self._thread_count = threads

    @property
    def networks(self):
        # TODO: make a unit test
        return list(self._network_targets)

    @property
    def threads(self):
        # TODO: make a unit test
        return self._thread_count

    @threads.setter
    def threads(self, value):
        # TODO: make a unit test
        if isinstance(value, int):
            self._thread_count = value

    @property
    def mode(self):
        # Return saved mode. If it hasn't been set arleady, then return default TCP scan mode (TCP_SCAN const).
        # TODO: make a unit test
        if hasattr(self, '_mode'):
            mode = getattr(self, '_mode')
        else:
            mode = TCP_SCAN

        return mode

    @mode.setter
    def mode(self, value):
        # TCP scanning (-sT), UDP scanning (-sU) and Service Recognition version scanning (-sV) are allowed.
        # TODO: make a unit test
        if value in (TCP_SCAN, UDP_SCAN, SERVICE_VERSION_SCAN):
            setattr(self, '_mode', value)

    @property
    def port_range(self):
        # Checks if object arleady has saved _ports attribute, otherwise set that to DEFAULT_PORT_RANGE.
        # It could be better idea than initilize it in __init__ function, because such boundary checks requires a lot of
        # coding, I considered __init__ function to be less a bit.
        # TODO: make a unit test
        if hasattr(self, '_ports'):
            range_value = getattr(self, '_ports')
        else:
            range_value = DEFAULT_PORT_RANGE

        min_val, max_val = min(range_value), max(range_value)
        return '{}-{}'.format(min_val, max_val)

    @port_range.setter
    def port_range(self, value):
        # TODO: make a unit test
        import re

        # Supplied net port range must be in string format and to be like 1-23 (regex checks)
        if isinstance(value, str) and re.match(r'\d-\d', str):
            # Convert from str to int
            min_val, max_val = [int(_int_value) for _int_value in str.split('-')]

            # Min port can't be less than the max one
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
        # First we need to normalize supplied string to CIDR form.
        # Both a host and a network can be represented in CIDR.
        # Examples:
        # 192.168.0.1 (IPv4 addr) -> 192.168.0.1/32 (CIDR IPv4 net)
        # 192.168.0.0/24 (IPv4 net) -> arleady CIDR IPv4 net
        # 192.168.0.0-192.168.0.255 (address range) -> not implemented
        # TODO: make a unit test
        # TODO: implement address range to CIDR IPv4 net normalization
        normalized_net = normalize(net)

        # Due to using set data structure, we don't need to worry about net duplications.
        self._network_targets.add(normalized_net)

        return True

    def run_scan_sync(self):
        """
        Start thread pool simultaneously and wait until all scans are done. Then it conclude all results into the one

        TODO: make unit test
        TODO: make a test with Pool and several scanning functions. That must run scan and add its result into one dict which is located in parent function. Using multiprocessig there might be a problem with variables in diffirent processes. If that is so we need to check how to propery use simple threads. But there could be another problem, e.g. nmap module uses nmap scanner, I don't now whether it runs another thread to make scan done or not, but we need to figure it out
        :return:
        """

        # A dict where each thread will save its scan result
        result = {}

        # # Create a Queue and full it with targets to be free of deadlock during multithreaded scanning
        # target_queue = Queue()
        # for net in self._network_targets:
        #     target_queue.put(net)

        # Special function to start nmap with specified args in a new python thread
        def worker(net):
            nm = nmap.PortScanner()
            nm.scan(net, arguments=self.mode, ports=self.port_range)

            # Combine result in non-local variable
            for scan_net in nm.all_hosts():
                result[scan_net] = nm[scan_net]

        # Create a thread pool to scan
        pool = Pool(self.threads)

        # For each net in network list start thread and process worker function upon that.
        # pool.map works like Queue, e.g. we have _thread_count threads. And if amount of hosts is bigger than amount of
        # threads, then left hosts will wait until a thread is joined and ready to run worker again.
        #
        # Example:
        # threads: #1th #2th #3th #4th
        # hosts: 127.0.0.1, 192.168.0.1, 10.0.0.1, 8.8.8.8, 172.168.13.2
        #
        # mapping:
        # #1th - > 127.0.0.1---------------done>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # ---#2th -> 192.168.0.1---------------done-------------------------------
        # ------#3th -> 10.0.0.1---------------done-------------------------------
        # ---------#4th -> 8.8.8.8---------------done-----------------------------
        # ----------------------------------#1th -> 172.168.13.2---------------done
        pool.map(worker, [net for net in self._network_targets])


        print(result)
