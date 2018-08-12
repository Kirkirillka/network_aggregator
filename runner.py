from models import Hive

if __name__ == '__main__':

    net1 = "192.168.23.0/24"
    net2 = "192.168.24.0/24"

    host1 = "192.168.23.25"

    hive = Hive('192.168.149.138')

    # Must be TRUE
    print(hive.add_network(net1))
    # FALSE
    print(hive.add_host(net2))

    # FALSE
    print(hive.add_network(host1))
    # TRUE
    print(hive.add_host(host1))