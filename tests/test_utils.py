"""Tests for utility modules."""

import getpass
import json
import os
import pytest


class TestDefaults:
    """Tests for storm/defaults.py."""

    def test_get_default_port_no_defaults(self):
        """Test get_default returns DEFAULT_PORT when no defaults provided."""
        from storm.defaults import get_default, DEFAULT_PORT
        assert get_default('port') == DEFAULT_PORT
        assert get_default('port', None) == DEFAULT_PORT
        assert get_default('port', {}) == DEFAULT_PORT

    def test_get_default_port_with_custom(self):
        """Test get_default returns custom port from defaults."""
        from storm.defaults import get_default
        assert get_default('port', {'port': 2222}) == 2222

    def test_get_default_user_no_defaults(self):
        """Test get_default returns current user when no defaults provided."""
        from storm.defaults import get_default, DEFAULT_USER
        assert get_default('user') == DEFAULT_USER
        assert get_default('user') == getpass.getuser()

    def test_get_default_user_with_custom(self):
        """Test get_default returns custom user from defaults."""
        from storm.defaults import get_default
        assert get_default('user', {'user': 'customuser'}) == 'customuser'

    def test_get_default_unknown_key(self):
        """Test get_default returns None for unknown keys."""
        from storm.defaults import get_default
        assert get_default('unknown_key') is None
        assert get_default('unknown_key', {}) is None

    def test_get_default_unknown_key_with_value(self):
        """Test get_default returns value for unknown keys if in defaults."""
        from storm.defaults import get_default
        assert get_default('custom', {'custom': 'value'}) == 'value'


class TestUtils:
    """Tests for storm/utils.py."""

    def test_fixed_width_shorter_text(self):
        """Test fixed_width pads shorter text."""
        from storm.utils import fixed_width
        result = fixed_width("test", 10)
        assert len(result) == 10
        assert result == "test      "

    def test_fixed_width_exact_length(self):
        """Test fixed_width with exact length text."""
        from storm.utils import fixed_width
        result = fixed_width("test", 4)
        assert len(result) == 4
        assert result == "test"

    def test_fixed_width_longer_text(self):
        """Test fixed_width doesn't truncate longer text."""
        from storm.utils import fixed_width
        result = fixed_width("testing", 4)
        assert result == "testing"

    def test_get_formatted_message_testmode_success(self):
        """Test get_formatted_message in test mode for success."""
        from storm.utils import get_formatted_message
        os.environ["TESTMODE"] = "1"
        try:
            result = get_formatted_message("operation completed", "success")
            assert result == "success operation completed"
            assert "\x1b[" not in result  # No color codes
        finally:
            del os.environ["TESTMODE"]

    def test_get_formatted_message_testmode_error(self):
        """Test get_formatted_message in test mode for error."""
        from storm.utils import get_formatted_message
        os.environ["TESTMODE"] = "1"
        try:
            result = get_formatted_message("something failed", "error")
            assert result == "error something failed"
            assert "\x1b[" not in result  # No color codes
        finally:
            del os.environ["TESTMODE"]

    def test_get_formatted_message_normal_mode_success(self):
        """Test get_formatted_message in normal mode for success."""
        from storm.utils import get_formatted_message
        # Ensure TESTMODE is not set
        if "TESTMODE" in os.environ:
            del os.environ["TESTMODE"]

        result = get_formatted_message("operation completed", "success")
        assert "operation completed" in result

    def test_get_formatted_message_normal_mode_error(self):
        """Test get_formatted_message in normal mode for error."""
        from storm.utils import get_formatted_message
        # Ensure TESTMODE is not set
        if "TESTMODE" in os.environ:
            del os.environ["TESTMODE"]

        result = get_formatted_message("something failed", "error")
        assert "something failed" in result


class TestStormConfigParser:
    """Tests for storm/parsers/storm_config_parser.py."""

    def test_get_storm_config_no_file(self, tmp_path, monkeypatch):
        """Test get_storm_config returns empty dict when file doesn't exist."""
        from storm.parsers.storm_config_parser import get_storm_config
        # Monkeypatch home to a temp directory without .stormssh/config
        monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
        result = get_storm_config()
        assert result == {}

    def test_get_storm_config_with_valid_file(self, tmp_path, monkeypatch):
        """Test get_storm_config reads valid JSON config."""
        from storm.parsers.storm_config_parser import get_storm_config

        # Create .stormssh/config with valid JSON
        config_dir = tmp_path / ".stormssh"
        config_dir.mkdir()
        config_file = config_dir / "config"
        config_data = {"aliases": {"ls": ["list"], "rm": ["delete"]}}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
        result = get_storm_config()
        assert result == config_data
        assert result["aliases"]["ls"] == ["list"]

    def test_get_storm_config_invalid_json(self, tmp_path, monkeypatch):
        """Test get_storm_config returns empty dict for invalid JSON."""
        from storm.parsers.storm_config_parser import get_storm_config

        # Create .stormssh/config with invalid JSON
        config_dir = tmp_path / ".stormssh"
        config_dir.mkdir()
        config_file = config_dir / "config"
        config_file.write_text("{ invalid json }")

        monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
        result = get_storm_config()
        assert result == {}


class TestSSHConfigParser:
    """Additional tests for storm/parsers/ssh_config_parser.py."""

    def test_delete_nonexistent_host(self, tmp_path):
        """Test deleting a non-existent host raises ValueError."""
        from storm.parsers.ssh_config_parser import ConfigParser

        config_file = tmp_path / "ssh_config"
        config_file.write_text("Host test\n    hostname test.com\n")

        parser = ConfigParser(str(config_file))
        parser.load()

        with pytest.raises(ValueError, match="No host found"):
            parser.delete_host("nonexistent")

    def test_dump_empty_config(self, tmp_path):
        """Test dump returns an empty string for empty config, so writing it clears the file."""
        from storm.parsers.ssh_config_parser import ConfigParser

        config_file = tmp_path / "ssh_config"
        config_file.write_text("")

        parser = ConfigParser(str(config_file))
        parser.load()
        parser.config_data = []

        result = parser.dump()
        assert result == ""

    def test_config_with_comments_and_empty_lines(self, tmp_path):
        """Test parsing config with comments and empty lines."""
        from storm.parsers.ssh_config_parser import ConfigParser

        config_content = """# This is a comment
Host test
    hostname test.com

# Another comment
Host test2
    hostname test2.com
"""
        config_file = tmp_path / "ssh_config"
        config_file.write_text(config_content)

        parser = ConfigParser(str(config_file))
        data = parser.load()

        # Should have comments, empty lines, and entries
        types = [item.get('type') for item in data]
        assert 'comment' in types
        assert 'empty_line' in types
        assert 'entry' in types

    def test_get_last_index_empty(self, tmp_path):
        """Test get_last_index returns 0 for empty config."""
        from storm.parsers.ssh_config_parser import ConfigParser

        config_file = tmp_path / "ssh_config"
        config_file.write_text("")

        parser = ConfigParser(str(config_file))
        parser.load()
        parser.config_data = []

        assert parser.get_last_index() == 0

    def test_config_creates_missing_file(self, tmp_path):
        """Test ConfigParser creates file if it doesn't exist."""
        from storm.parsers.ssh_config_parser import ConfigParser

        config_file = tmp_path / ".ssh" / "config"
        assert not config_file.exists()

        parser = ConfigParser(str(config_file))
        assert config_file.exists()

    def test_update_host_with_regex(self, tmp_path):
        """Test updating multiple hosts with regex pattern."""
        from storm.parsers.ssh_config_parser import ConfigParser

        config_content = """Host server-1
    hostname server1.com
    port 22

Host server-2
    hostname server2.com
    port 22

Host other
    hostname other.com
    port 22
"""
        config_file = tmp_path / "ssh_config"
        config_file.write_text(config_content)

        parser = ConfigParser(str(config_file))
        parser.load()
        parser.update_host(r"server-\d", {"port": "2222"}, use_regex=True)

        # Check that server-1 and server-2 were updated but not other
        for entry in parser.config_data:
            if entry.get('host') in ['server-1', 'server-2']:
                assert entry['options']['port'] == '2222'
            elif entry.get('host') == 'other':
                assert entry['options']['port'] == '22'

    def test_dump_with_list_options(self, tmp_path):
        """Test dump handles list options like multiple identity files."""
        from storm.parsers.ssh_config_parser import ConfigParser

        config_content = """Host multi-id
    hostname multi.com
    identityfile /key1.pem
    identityfile /key2.pem
"""
        config_file = tmp_path / "ssh_config"
        config_file.write_text(config_content)

        parser = ConfigParser(str(config_file))
        parser.load()
        dumped = parser.dump()

        assert "identityfile /key1.pem" in dumped
        assert "identityfile /key2.pem" in dumped


class TestSSHConfigParserRegressions:
    """Round-trip and write-safety regressions for ConfigParser."""

    def _parser(self, tmp_path, content):
        from storm.parsers.ssh_config_parser import ConfigParser

        config_file = tmp_path / "ssh_config"
        config_file.write_text(content)
        parser = ConfigParser(str(config_file))
        parser.load()
        return parser, config_file

    def test_value_containing_equals_is_preserved(self, tmp_path):
        parser, config_file = self._parser(
            tmp_path, "Host a\n    SetEnv FOO=bar\n    RemoteCommand echo x=1\n")
        options = parser.config_data[0]["options"]
        assert options["setenv"] == "FOO=bar"
        assert options["remotecommand"] == "echo x=1"

        parser.write_to_ssh_config()
        assert "setenv FOO=bar" in config_file.read_text()

    def test_equals_separated_directives(self, tmp_path):
        parser, _ = self._parser(
            tmp_path,
            "Host a\n    HostName=example.com\n    Port = 2222\n"
            "    ProxyCommand=ssh -W %h:%p -o A=b gw\n")
        options = parser.config_data[0]["options"]
        assert options["hostname"] == "example.com"
        assert options["port"] == "2222"
        assert options["proxycommand"] == "ssh -W %h:%p -o A=b gw"

    def test_repeated_multi_value_directives_are_kept(self, tmp_path):
        parser, config_file = self._parser(
            tmp_path,
            "Host a\n    SendEnv A\n    SendEnv B\n"
            "    CertificateFile c1\n    CertificateFile c2\n"
            "    DynamicForward 1080\n    DynamicForward 1081\n")
        options = parser.config_data[0]["options"]
        assert options["sendenv"] == ["A", "B"]
        assert options["certificatefile"] == ["c1", "c2"]
        assert options["dynamicforward"] == ["1080", "1081"]

        parser.write_to_ssh_config()
        written = config_file.read_text()
        assert "sendenv A\n    sendenv B" in written
        assert "certificatefile c2" in written

    def test_first_value_wins_for_single_value_directives(self, tmp_path):
        parser, _ = self._parser(tmp_path, "Host a\n    User first\n    User second\n")
        assert parser.config_data[0]["options"]["user"] == "first"

    def test_directive_without_value_is_rejected(self, tmp_path):
        from storm.parsers.ssh_config_parser import ConfigParser

        config_file = tmp_path / "ssh_config"
        config_file.write_text("Host a\n    Compression\n")
        with pytest.raises(ValueError, match="Unparsable line"):
            ConfigParser(str(config_file)).load()

    def test_search_includes_integer_values(self, tmp_path):
        parser, _ = self._parser(tmp_path, "Host a\n    hostname h\n")
        parser.config_data[0]["options"]["port"] = 4242
        assert parser.search_host("4242") == [parser.config_data[0]]

    def test_search_includes_list_values(self, tmp_path):
        parser, _ = self._parser(tmp_path, "Host a\n    IdentityFile ~/.ssh/special\n")
        assert len(parser.search_host("special")) == 1

    def test_delete_removes_every_matching_entry(self, tmp_path):
        parser, config_file = self._parser(
            tmp_path, "Host a\n    hostname x\nHost a\n    hostname y\nHost b\n    hostname z\n")
        parser.delete_host("a")
        parser.write_to_ssh_config()
        assert config_file.read_text() == "Host b\n    hostname z\n"

    def test_deleting_last_entry_empties_the_file(self, tmp_path):
        parser, config_file = self._parser(tmp_path, "Host a\n    hostname x\n")
        parser.delete_host("a")
        parser.write_to_ssh_config()
        assert config_file.read_text() == ""

    def test_delete_all_hosts_empties_the_file(self, tmp_path):
        parser, config_file = self._parser(tmp_path, "Host a\n    hostname x\n")
        parser.delete_all_hosts()
        assert config_file.read_text() == ""

    def test_update_deleting_absent_field_is_harmless(self, tmp_path):
        parser, _ = self._parser(tmp_path, "Host a\n    hostname x\n")
        parser.update_host("a", {"deleted_fields": ["identityfile"], "user": "u"})
        assert parser.config_data[0]["options"] == {"hostname": "x", "user": "u"}

    def test_update_deletes_field_on_every_regex_match(self, tmp_path):
        parser, _ = self._parser(
            tmp_path,
            "Host web1\n    IdentityFile k1\nHost web2\n    IdentityFile k2\n")
        options = {"deleted_fields": ["identityfile"]}
        parser.update_host("web", options, use_regex=True)
        assert all("identityfile" not in e["options"] for e in parser.config_data)
        # the caller's dict is not consumed
        assert options == {"deleted_fields": ["identityfile"]}

    def test_write_preserves_file_mode(self, tmp_path):
        parser, config_file = self._parser(tmp_path, "Host a\n    hostname x\n")
        config_file.chmod(0o600)
        parser.write_to_ssh_config()
        assert config_file.stat().st_mode & 0o777 == 0o600

    def test_write_goes_through_symlink(self, tmp_path):
        from storm.parsers.ssh_config_parser import ConfigParser

        real = tmp_path / "dotfiles" / "ssh_config"
        real.parent.mkdir()
        real.write_text("Host a\n    hostname x\n")
        link = tmp_path / "config"
        link.symlink_to(real)

        parser = ConfigParser(str(link))
        parser.load()
        parser.add_host("b", {"hostname": "y"})
        parser.write_to_ssh_config()

        assert link.is_symlink()
        assert "Host b" in real.read_text()

    def test_write_recreates_missing_file_privately(self, tmp_path):
        parser, config_file = self._parser(tmp_path, "Host a\n    hostname x\n")
        config_file.unlink()
        parser.write_to_ssh_config()
        assert config_file.stat().st_mode & 0o777 == 0o600
        assert "Host a" in config_file.read_text()

    def test_failed_write_leaves_original_and_no_temp_file(self, tmp_path, monkeypatch):
        import os

        parser, config_file = self._parser(tmp_path, "Host a\n    hostname x\n")
        parser.add_host("b", {"hostname": "y"})

        def fail(src, dst):
            raise OSError("simulated")
        monkeypatch.setattr(os, "replace", fail)

        with pytest.raises(OSError, match="simulated"):
            parser.write_to_ssh_config()
        assert config_file.read_text() == "Host a\n    hostname x\n"
        assert [p.name for p in tmp_path.iterdir()] == ["ssh_config"]

    def test_missing_ssh_dir_is_created_private(self, tmp_path):
        from storm.parsers.ssh_config_parser import ConfigParser

        config_file = tmp_path / "newssh" / "config"
        ConfigParser(str(config_file))
        assert (tmp_path / "newssh").stat().st_mode & 0o777 == 0o700
        assert config_file.stat().st_mode & 0o777 == 0o600

    def test_default_config_path_is_in_home(self, fake_home):
        from storm.parsers.ssh_config_parser import ConfigParser

        parser = ConfigParser()
        assert parser.ssh_config_file == fake_home / ".ssh" / "config"
        assert parser.ssh_config_file.exists()
