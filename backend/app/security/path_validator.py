import os
import ipaddress
import socket
import urllib.parse
from typing import Tuple

BLOCKED_IP_PREFIXES = [
    "127.",        # loopback
    "10.",         # private class A
    "172.16.",     # private class B (172.16.0.0/12)
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",    # private class C
    "169.254.",    # link-local
    "0.0.0.0",
]

def is_safe_url(url: str) -> Tuple[bool, str]:
    """
    Validates a URL against SSRF and non-HTTP schemes:
    - Only http and https schemes allowed
    - Blocks localhost, 127.0.0.1, internal RFC1918 private IPs
    """
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"Scheme '{parsed.scheme}' is not allowed. Only HTTP and HTTPS are permitted."

        hostname = parsed.hostname
        if not hostname:
            return False, "URL does not have a valid hostname."

        lower_host = hostname.lower()
        if lower_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False, "Access to localhost or loopback is blocked for security."

        for prefix in BLOCKED_IP_PREFIXES:
            if lower_host.startswith(prefix):
                return False, f"Access to private network IP ({lower_host}) is blocked."

        # Check resolved IP address if possible
        try:
            resolved_ip = socket.gethostbyname(lower_host)
            ip_obj = ipaddress.ip_address(resolved_ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                return False, f"Host '{hostname}' resolves to private/loopback IP {resolved_ip}."
        except Exception:
            # If resolution fails offline, do not strictly block here if it's a valid public-looking domain name
            pass

        return True, ""
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"

