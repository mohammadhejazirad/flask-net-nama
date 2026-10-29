import pytest
from netnama.core.validation import ValidationError, domain, dns_name, prepare_inputs
from netnama.core.target_policy import allowed_ip
from netnama.tools.ip import cidr
from netnama.tools.ping import argv


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com",
        "user@example.com",
        "example.com:43",
        "a/b.com",
        "-a.com",
        "a..com",
        "x\u200e.com",
        "a.unknownsuffix",
    ],
)
def test_bad_domains(app, value):
    with pytest.raises(ValidationError):
        domain(value, app.extensions["resources"].snapshot())


def test_normalization(app):
    resource = app.extensions["resources"].snapshot()
    targets, mapping = prepare_inputs(
        "\ufeffEXAMPLE.COM.\r\nexample.com\n# comment\nمثال.com\nwww.example.co.uk", resource
    )
    assert len(targets) == 3
    assert len(mapping) == 4
    assert targets[1]["ascii"].startswith("xn--")
    assert targets[2]["status"] == "invalid"
    assert targets[2]["suggestion"] == "example.co.uk"
    assert dns_name("_sip._tcp.example.com.") == "_sip._tcp.example.com."


@pytest.mark.parametrize(
    "value",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "::1",
        "fe80::1",
        "fc00::1",
        "::ffff:8.8.8.8",
        "224.0.0.1",
        "0.0.0.0",
    ],
)
def test_public_policy(value):
    assert not allowed_ip(value)


def test_public_addresses():
    assert allowed_ip("1.1.1.1")
    assert allowed_ip("2606:4700:4700::1111")


def test_cidr_and_ping():
    assert cidr("192.0.2.0/31")["usable"] == "2"
    assert cidr("192.0.2.1/32")["usable"] == "1"
    assert cidr("2001:db8::/64")["addresses"] == str(2**64)
    assert argv("ping", "Linux", "1.1.1.1", 4) == ["ping", "-4", "-n", "-c", "4", "-W", "2", "1.1.1.1"]
    assert "-w" in argv("ping", "Windows", "::1", 2)
    assert argv("ping", "Darwin", "1.1.1.1", 4)[-2:] == ["2000", "1.1.1.1"]


def test_private_hosting_suffix_not_registry_boundary(app):
    targets, _ = prepare_inputs("foo.blogspot.com", app.extensions["resources"].snapshot())
    assert targets[0]["status"] == "invalid"
    assert targets[0]["suggestion"] == "blogspot.com"
