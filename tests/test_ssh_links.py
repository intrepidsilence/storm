"""Tests for storm/static/js/ssh-links.js, run under Node.js.

The web UI turns hosts into ssh:// links that the OS hands to the user's
terminal. A host such as "-oProxyCommand=..." must never become a link,
because the terminal would pass it to ssh as an option.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC_JS = Path(__file__).parent.parent / "storm" / "static" / "js"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def call(function, *args):
    script = (
        f"const links = require({json.dumps(str(STATIC_JS / 'ssh-links.js'))});"
        f"process.stdout.write(JSON.stringify(links[{json.dumps(function)}]"
        f"(...{json.dumps(list(args))}) ?? null));"
    )
    result = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


class TestAliasLink:
    @pytest.mark.parametrize("host,expected", [
        ("web", "ssh://web"),
        ("web-1.prod_eu", "ssh://web-1.prod_eu"),
        ("uk.gw.lan uk.lan", "ssh://uk.gw.lan"),
        ("*.internal bastion", "ssh://bastion"),
        ("!blocked ok", "ssh://ok"),
    ])
    def test_links_first_concrete_pattern(self, host, expected):
        assert call("aliasLink", host) == expected

    @pytest.mark.parametrize("host", [
        "-oProxyCommand=touch /tmp/pwned",
        "-p",
        "*",
        "web-*",
        "host?",
        "a/b",
        "with%20space",
        "",
        "ü-host",
    ])
    def test_unsafe_or_wildcard_hosts_get_no_link(self, host):
        assert call("aliasLink", host) is None

    def test_alias_target(self):
        assert call("aliasTarget", "*.x  jump  other") == "jump"
        assert call("aliasTarget", "*") is None


class TestAddressLink:
    @pytest.mark.parametrize("args,expected", [
        (["admin", "alpha.example.com", "2200"], "ssh://admin@alpha.example.com:2200"),
        (["admin", "alpha.example.com", 22], "ssh://admin@alpha.example.com:22"),
        ([None, "10.0.0.2", None], "ssh://10.0.0.2"),
        (["", "10.0.0.2", ""], "ssh://10.0.0.2"),
        (["ops", "2001:db8::8", "2023"], "ssh://ops@[2001:db8::8]:2023"),
        (["ops", "::1", None], "ssh://ops@[::1]"),
    ])
    def test_builds_address(self, args, expected):
        assert call("addressLink", *args) == expected

    @pytest.mark.parametrize("args", [
        ["root", "-oProxyCommand=evil", "22"],
        ["-oProxyCommand=evil", "host", "22"],
        ["root", "", "22"],
        [None, None, None],
        ["root", "host name", "22"],
        ["root", "fe80::1%en0", "22"],
        ["r@t", "host", "22"],
        ["%u", "host", "22"],
        ["root", "host", "0"],
        ["root", "host", "65536"],
        ["root", "host", "22a"],
        ["root", "host", "-22"],
    ])
    def test_unsafe_values_get_no_link(self, args):
        assert call("addressLink", *args) is None


def test_main_js_parses():
    subprocess.run([NODE, "--check", str(STATIC_JS / "main.js")], check=True)


def test_ssh_links_attaches_to_window_in_browser():
    script = (
        "const vm = require('vm');"
        f"const code = require('fs').readFileSync({json.dumps(str(STATIC_JS / 'ssh-links.js'))}, 'utf8');"
        "const window = {}; vm.runInNewContext(code, window);"
        "process.stdout.write(String(typeof window.stormSshLinks.aliasLink));"
    )
    result = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    assert result.stdout == "function"
