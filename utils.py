import re
import ipaddress


def validate_net_data(net_data):
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


def is_supernet(net, supernet):
    """
        Checks for given net that it's overlapped by supplied supernet,
            e.g. 192.168.13.0/25 is subnet of 192.168.13.0/24.
        Both net and supernet must be given in CIDR format (IPv4 only).
    :param net: a string represented network address in CIDR format to validate it's overlapped by supernet.
    :param supernet: a string represented network address in CIDR format which mask prefix is less than a given one.
    :return: True if net is overlapped by supernet, e.g net is a subnet of supernet.
    """
    if not (is_network(net) and is_network(supernet)):
        return False
    foo = ipaddress.ip_network(net)
    bar = ipaddress.ip_network(supernet)
    return foo.overlaps(bar)