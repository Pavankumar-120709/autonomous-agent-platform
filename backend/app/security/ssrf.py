import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple


BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::ffff:0:0/96"),
    ipaddress.ip_network("100::/64"),
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("2001::/32"),
    ipaddress.ip_network("2001:db8::/32"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443, 8080, 8443}


class SSRFValidationError(ValueError):
    """Raised when URL violates SSRF safety rules."""
    pass


def validate_url_safe(url: str) -> Tuple[bool, str]:
    """
    Validates a URL against SSRF vulnerabilities.
    Returns (True, canonical_url) or raises SSRFValidationError.
    """
    if not url or not isinstance(url, str):
        raise SSRFValidationError("URL cannot be empty")

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise SSRFValidationError(f"Invalid URL structure: {e}")

    if not parsed.scheme or parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise SSRFValidationError(
            f"Invalid URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL must include a valid hostname.")

    hostname_lower = hostname.lower()

    if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        raise SSRFValidationError(f"Access to private/internal hostname '{hostname}' is blocked.")

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise SSRFValidationError(f"Port {port} is not in allowed HTTP/HTTPS ports.")

    # Resolve IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise SSRFValidationError(f"Could not resolve host '{hostname}': {e}")
    except Exception as e:
        raise SSRFValidationError(f"DNS resolution failure for '{hostname}': {e}")

    if not addr_info:
        raise SSRFValidationError(f"Could not resolve any IP addresses for host '{hostname}'.")

    for family, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise SSRFValidationError(f"Resolved invalid IP address '{ip_str}'")

        # Check against private / loopback / link-local
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise SSRFValidationError(
                f"URL resolves to restricted IP {ip_str} (private, loopback, or reserved)."
            )

        for blocked in BLOCKED_NETWORKS:
            if ip in blocked:
                raise SSRFValidationError(
                    f"URL resolves to blocked network {blocked} via IP {ip_str}."
                )

    return True, url
