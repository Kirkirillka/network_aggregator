# Constants to specify what mode to use in Scanner class
TCP_SCAN = '-sT'
UDP_SCAN = '-sU'
SERVICE_VERSION_SCAN = '-sV'

# Constants to constraint range of ports to scan.
# According to RFC 6335 maximum port is limited to 2 **16 -1
DEFAULT_PORT_RANGE = range(1,100)
MAX_RANGE = range(1, 2**16)


# Constants to determinate choices for NetworkEntry MongoDB class.
ADDRESS = "address"
NETWORK = "network"