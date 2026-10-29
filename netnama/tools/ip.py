import ipaddress


def inspect(target):
    ip = ipaddress.ip_address(target)
    return {
        "status": "success",
        "address": str(ip),
        "family": ip.version,
        "public": ip.is_global,
        "private": ip.is_private,
        "loopback": ip.is_loopback,
        "link_local": ip.is_link_local,
        "multicast": ip.is_multicast,
        "reserved": ip.is_reserved,
        "reverse_pointer": ip.reverse_pointer,
    }


def cidr(target):
    network = ipaddress.ip_network(target, strict=False)
    total = network.num_addresses
    usable = total if network.version == 6 or network.prefixlen >= 31 else max(0, total - 2)
    return {
        "status": "success",
        "network": str(network),
        "prefix": network.prefixlen,
        "family": network.version,
        "netmask": str(network.netmask),
        "first": str(network.network_address),
        "last": str(network.broadcast_address),
        "addresses": str(total),
        "usable": str(usable),
    }
