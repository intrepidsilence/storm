"""Tests for the Storm class."""

import getpass
import os
import pytest

from storm import Storm
from storm.parsers.ssh_uri_parser import parse
from storm import __version__


class TestStorm:
    """Tests for the Storm class."""

    def test_config_load(self, storm_instance):
        assert storm_instance.ssh_config.config_data[1]["options"]["identitiesonly"] == 'yes'

    def test_config_dump(self, storm_instance):
        storm_instance.ssh_config.write_to_ssh_config()

        config_path = storm_instance.ssh_config.ssh_config_file
        with open(config_path) as fd:
            content = fd.read()

        assert "hostname 1.1.1.1" in content
        assert "Host netscaler" in content
        assert "Host *" in content

    def test_update_host(self, storm_instance):
        storm_instance.ssh_config.update_host("netscaler", {"hostname": "2.2.2.2"})
        # Find the netscaler entry in config_data
        netscaler_entry = None
        for entry in storm_instance.ssh_config.config_data:
            if entry.get("host") == "netscaler":
                netscaler_entry = entry
                break
        assert netscaler_entry is not None
        assert netscaler_entry["options"]["hostname"] == '2.2.2.2'

    def test_add_host(self, storm_instance):
        storm_instance.add_entry('google', 'google.com', 'root', '22', '/tmp/tmp.pub')
        storm_instance.add_entry('goog', 'google.com', 'root', '22', '/tmp/tmp.pub')
        storm_instance.ssh_config.write_to_ssh_config()

        for item in storm_instance.ssh_config.config_data:
            if item.get("host") in ('google', 'goog'):
                assert item.get("options").get("port") == '22'
                assert item.get("options").get("identityfile") == '"/tmp/tmp.pub"'

    def test_clone_host(self, storm_instance):
        storm_instance.add_entry('google', 'google.com', 'ops', '24', '/tmp/tmp.pub')
        storm_instance.clone_entry('google', 'yahoo')

        has_yahoo = False
        for item in storm_instance.ssh_config.config_data:
            if item.get("host") == 'yahoo':
                has_yahoo = True
                assert item.get("options").get("port") == '24'
                assert item.get("options").get("identityfile") == '"/tmp/tmp.pub"'
                assert item.get("options").get("user") == 'ops'
                break

        assert has_yahoo

    def test_move_host(self, storm_instance):
        storm_instance.add_entry('google', 'google.com', 'ops', '24', '/tmp/tmp.pub')
        storm_instance.clone_entry('google', 'yahoo', keep_original=False)

        has_yahoo = False
        has_google = False
        yahoo_item = None
        for item in storm_instance.ssh_config.config_data:
            if item.get("host") == 'yahoo':
                has_yahoo = True
                yahoo_item = item
            if item.get("host") == 'google':
                has_google = True

        assert has_yahoo
        assert not has_google
        assert yahoo_item.get("options").get("port") == '24'
        assert yahoo_item.get("options").get("identityfile") == '"/tmp/tmp.pub"'
        assert yahoo_item.get("options").get("user") == 'ops'

    def test_backup(self, storm_instance, tmp_path):
        backup_file = tmp_path / "storm_backup"
        storm_instance.backup(str(backup_file))
        assert backup_file.exists()

    def test_double_clone_exception(self, storm_instance):
        storm_instance.add_entry('google', 'google.com', 'ops', '24', '/tmp/tmp.pub')
        storm_instance.clone_entry('google', 'yahoo')

        with pytest.raises(ValueError):
            storm_instance.clone_entry('google', 'yahoo')

    def test_edit_host(self, storm_instance):
        storm_instance.add_entry('google', 'google.com', 'root', '22', '/tmp/tmp.pub')
        storm_instance.ssh_config.write_to_ssh_config()

        storm_instance.edit_entry('google', 'google.com', 'root', '23', '/tmp/tmp.pub')
        storm_instance.ssh_config.write_to_ssh_config()

        for item in storm_instance.ssh_config.config_data:
            if item.get("host") == 'google':
                assert item.get("options").get("port") == '23'

    def test_edit_by_hostname_regexp(self, storm_instance):
        import re
        storm_instance.add_entry('google-01', 'google.com', 'root', '22', '/tmp/tmp.pub')
        storm_instance.add_entry('google-02', 'google.com', 'root', '23', '/tmp/tmp.pub')
        storm_instance.ssh_config.write_to_ssh_config()

        storm_instance.update_entry('google-[0-2]', port='24', identityfile='/tmp/tmp.pub1')

        for item in storm_instance.ssh_config.config_data:
            if re.match(r"google*", item.get("host")):
                assert item.get("options").get("identityfile") == '/tmp/tmp.pub1'
                assert item.get("options").get("port") == '24'

    def test_delete_host(self, storm_instance):
        storm_instance.delete_entry('netscaler')
        for host in storm_instance.ssh_config.config_data:
            assert host.get("host") != 'netscaler'

    def test_delete_all(self, storm_instance):
        storm_instance.delete_all_entries()
        assert len(storm_instance.ssh_config.config_data) == 0

    def test_search_host(self, storm_instance):
        results = storm_instance.ssh_config.search_host("netsca")
        assert len(results) == 1

    def test_custom_options(self, storm_instance):
        custom_options = (
            "StrictHostKeyChecking=no",
            "UserKnownHostsFile=/dev/null",
        )
        storm_instance.add_entry(
            'host_with_custom_option',
            'emre.io', 'emre', 22,
            None, custom_options=custom_options
        )
        storm_instance.ssh_config.write_to_ssh_config()

        for item in storm_instance.ssh_config.config_data:
            if item.get("host") == 'host_with_custom_option':
                assert item.get("options").get("stricthostkeychecking") == 'no'
                assert item.get("options").get("userknownhostsfile") == '/dev/null'

        custom_options = (
            "StrictHostKeyChecking=yes",
            "UserKnownHostsFile=/home/emre/foo",
        )
        storm_instance.edit_entry(
            'host_with_custom_option',
            'emre.io', 'emre', 22,
            None, custom_options=custom_options
        )
        storm_instance.ssh_config.write_to_ssh_config()

        for item in storm_instance.ssh_config.config_data:
            if item.get("host") == 'host_with_custom_option':
                assert item.get("options").get("stricthostkeychecking") == 'yes'
                assert item.get("options").get("userknownhostsfile") == '/home/emre/foo'


class TestUriParser:
    """Tests for the SSH URI parser."""

    def test_uri_parser(self):
        user = getpass.getuser()
        test_cases = [
            ('root@emreyilmaz.me:22', ('root', 'emreyilmaz.me', 22)),
            ('emreyilmaz.me', (user, 'emreyilmaz.me', 22)),
            ('emreyilmaz.me:22', (user, 'emreyilmaz.me', 22)),
            ('root@emreyilmaz.me', ('root', 'emreyilmaz.me', 22))
        ]

        for uri, expected in test_cases:
            assert parse(uri) == expected

    def test_invalid_port(self):
        with pytest.raises(ValueError, match="port must be numeric"):
            parse('root@emreyilmaz.me:string-port')


class TestVersion:
    """Tests for version."""

    def test_version_exists(self):
        assert __version__ is not None
        assert isinstance(__version__, str)
