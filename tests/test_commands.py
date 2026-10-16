"""In-process tests for the CLI commands in storm/__main__.py.

test_cli.py runs the installed `storm` executable as a subprocess, which is
the most realistic check but invisible to coverage. These tests dispatch the
same argument lists through the command parser inside the test process.
"""

import pytest

import storm.__main__ as cli
from storm import Storm, __version__


@pytest.fixture
def run(ssh_config_file, capsys):
    """Run a storm command against the fake ssh config.

    Returns (stdout, stderr, exit_code); exit_code is 0 when the command
    returns normally.
    """
    def _run(*args, config=True):
        argv = list(args)
        if config:
            argv.append(f"--config={ssh_config_file}")
        try:
            cli.main.execute(argv)
            code = 0
        except SystemExit as exc:
            code = exc.code
        out, err = capsys.readouterr()
        return out, err, code
    return _run


def load(ssh_config_file):
    return Storm(ssh_config_file)


class TestVersion:
    def test_version_command(self, run):
        out, _, code = run("version", config=False)
        assert out.strip() == __version__
        assert code == 0

    def test_version_flag(self, run):
        out, _, code = run("--version", config=False)
        assert out.strip() == __version__
        assert code == 0


class TestAdd:
    def test_add(self, run, ssh_config_file):
        out, _, code = run("add", "newhost", "bob@example.com:2200")
        assert code == 0
        assert "newhost added to your ssh config" in out

        entry = load(ssh_config_file).is_host_in("newhost", return_match=True)
        # values are re-read from the file, so they come back as strings
        assert entry["options"] == {"hostname": "example.com", "user": "bob", "port": "2200"}

    def test_add_uses_host_star_defaults(self, run, ssh_config_file):
        run("add", "plain", "example.com")
        entry = load(ssh_config_file).is_host_in("plain", return_match=True)
        # "Host *" in the fixture sets User nixcraft and Port 22.
        assert entry["options"]["user"] == "nixcraft"
        assert entry["options"]["port"] == "22"

    def test_add_with_id_file_and_options(self, run, ssh_config_file):
        _, _, code = run("add", "full", "a@b.com", "--id_file=/tmp/key",
                         "--o", "StrictHostKeyChecking=no", "--o", "UserKnownHostsFile=/dev/null")
        assert code == 0
        options = load(ssh_config_file).is_host_in("full", return_match=True)["options"]
        assert options["identityfile"] == ['"/tmp/key"']
        assert options["stricthostkeychecking"] == "no"
        assert options["userknownhostsfile"] == "/dev/null"

    def test_add_rejects_at_in_name(self, run):
        _, err, code = run("add", "bad@name", "example.com")
        assert code == 1
        assert '"@" cannot be used in name' in err

    def test_add_duplicate(self, run):
        _, err, code = run("add", "nas01", "example.com")
        assert code == 1
        assert "already in your sshconfig" in err

    def test_add_bad_port(self, run):
        _, err, code = run("add", "x", "example.com:http")
        assert code == 1
        assert "port must be numeric" in err

    def test_add_rejects_injected_option_value(self, run, ssh_config_file):
        _, err, code = run("add", "x", "example.com", "--o", "User=a\nProxyCommand=evil")
        assert code == 1
        assert "line breaks" in err
        assert "ProxyCommand" not in open(ssh_config_file).read().replace(
            "ProxyCommand  ssh nixcraft", "")


class TestCloneAndMove:
    def test_clone(self, run, ssh_config_file):
        out, _, code = run("clone", "nas01", "nas02")
        assert code == 0
        assert "nas02 added" in out
        storm_ = load(ssh_config_file)
        assert storm_.is_host_in("nas01")
        assert storm_.is_host_in("nas02")

    def test_clone_rejects_at_in_name(self, run):
        _, err, code = run("clone", "a@b", "c")
        assert code == 1
        assert '"@" cannot be used' in err

    def test_clone_missing(self, run):
        _, err, code = run("clone", "missing", "copy")
        assert code == 1
        assert "doesn't exist" in err

    def test_move(self, run, ssh_config_file):
        out, _, code = run("move", "nas01", "nas-renamed")
        assert code == 0
        assert "nas-renamed moved" in out
        storm_ = load(ssh_config_file)
        assert not storm_.is_host_in("nas01")
        assert storm_.is_host_in("nas-renamed")

    def test_move_rejects_at_in_name(self, run):
        _, _, code = run("move", "a@b", "c")
        assert code == 1

    def test_move_missing(self, run):
        _, err, code = run("move", "missing", "other")
        assert code == 1
        assert "doesn't exist" in err


class TestEdit:
    def test_edit(self, run, ssh_config_file):
        out, _, code = run("edit", "nas01", "admin@10.0.0.1:2222")
        assert code == 0
        assert '"nas01" updated successfully' in out
        options = load(ssh_config_file).is_host_in("nas01", return_match=True)["options"]
        assert options["hostname"] == "10.0.0.1"
        assert options["user"] == "admin"
        assert options["port"] == "2222"

    def test_edit_multi_pattern_host_with_commas(self, run, ssh_config_file):
        _, _, code = run("edit", "uk.gw.lan,uk.lan", "root@10.0.0.9")
        assert code == 0
        entry = load(ssh_config_file).is_host_in("uk.gw.lan uk.lan", return_match=True)
        assert entry["options"]["hostname"] == "10.0.0.9"

    def test_edit_missing(self, run):
        _, err, code = run("edit", "missing", "example.com")
        assert code == 1
        assert "doesn't exist" in err


class TestUpdate:
    def test_update_options_and_id_file(self, run, ssh_config_file):
        out, _, code = run("update", "nas01", "--id_file=/tmp/new.key",
                           "--o", "Port=2022", "--o", "LocalCommand=echo a=b")
        assert code == 0
        assert '"nas01" updated successfully' in out
        options = load(ssh_config_file).is_host_in("nas01", return_match=True)["options"]
        assert options["identityfile"] == ["/tmp/new.key"]
        # keys are lower-cased and values may contain "="
        assert options["port"] == "2022"
        assert options["localcommand"] == "echo a=b"

    def test_update_regex(self, run, ssh_config_file):
        _, _, code = run("update", "uk.*", "--o", "user=regexuser")
        assert code == 0
        entry = load(ssh_config_file).is_host_in("uk.gw.lan uk.lan", return_match=True)
        assert entry["options"]["user"] == "regexuser"

    def test_update_option_without_equals(self, run):
        _, err, code = run("update", "nas01", "--o", "Port")
        assert code == 1
        assert "key=value" in err

    def test_update_invalid_regex(self, run):
        _, err, code = run("update", "[", "--o", "user=x")
        assert code == 1
        assert "invalid regular expression" in err

    def test_update_missing(self, run):
        _, err, code = run("update", "nomatch", "--o", "user=x")
        assert code == 1
        assert "doesn't exist" in err


class TestDelete:
    def test_delete(self, run, ssh_config_file):
        out, _, code = run("delete", "nas01")
        assert code == 0
        assert 'hostname "nas01" deleted successfully' in out
        assert not load(ssh_config_file).is_host_in("nas01")

    def test_delete_missing(self, run):
        _, err, code = run("delete", "missing")
        assert code == 1
        assert "No host found" in err

    def test_delete_all(self, run, ssh_config_file):
        out, _, code = run("delete_all")
        assert code == 0
        assert "all entries deleted" in out
        assert open(ssh_config_file).read() == ""

    def test_delete_all_error(self, run, monkeypatch):
        def boom(self):
            raise OSError("disk full")
        monkeypatch.setattr(Storm, "delete_all_entries", boom)
        _, err, code = run("delete_all")
        assert code == 1
        assert "disk full" in err


class TestList:
    def test_list(self, run):
        out, _, code = run("list")
        assert code == 0
        assert out.startswith(" Listing entries:\n\n")
        assert "nas01 -> root@192.168.1.100:22" in out
        assert "server1 -> nixcraft@server1.cyberciti.biz:4242" in out
        # list-valued custom options are joined with commas
        assert "identityfile=/nfs/shared/users/nixcraft/keys/server1/id_rsa,/tmp/x.rsa" in out
        # Host * options, list-valued and scalar
        assert "(*) General options:" in out
        assert "localforward: 3128 127.0.0.1:3128, 3129 127.0.0.1:3128" in out
        assert "serveraliveinterval: 60" in out

    def test_list_host_without_hostname(self, run, tmp_path, capsys):
        config = tmp_path / "bare"
        config.write_text("Host bare\n    user someone\n")
        cli.main.execute(["list", f"--config={config}"])
        out = capsys.readouterr().out
        assert "bare -> someone@[hostname_not_specified]:22" in out

    def test_list_error(self, run, monkeypatch):
        def boom(self, *args, **kwargs):
            raise OSError("broken")
        monkeypatch.setattr(Storm, "list_entries", boom)
        _, err, code = run("list")
        assert code == 1
        assert "broken" in err


class TestSearch:
    def test_search(self, run):
        out, _, code = run("search", "aws")
        assert code == 0
        assert "Listing results for aws:" in out
        assert "aws.apache -> wwwdata@1.2.3.4:22" in out

    def test_search_no_results(self, run):
        out, _, code = run("search", "zzz-nothing")
        assert code == 0
        assert "no results found." in out

    def test_search_error(self, run, monkeypatch):
        def boom(self, text):
            raise ValueError("search broke")
        monkeypatch.setattr(Storm, "search_host", boom)
        _, err, code = run("search", "x")
        assert code == 1
        assert "search broke" in err


class TestBackup:
    def test_backup(self, run, ssh_config_file, tmp_path):
        target = tmp_path / "backup"
        _, _, code = run("backup", str(target))
        assert code == 0
        assert target.read_text() == open(ssh_config_file).read()

    def test_backup_error(self, run, tmp_path):
        _, err, code = run("backup", str(tmp_path / "no" / "such" / "dir" / "file"))
        assert code == 1
        assert "No such file or directory" in err


class TestWeb:
    def test_web_starts_server(self, monkeypatch, ssh_config_file):
        import storm.web as web

        calls = {}
        monkeypatch.setattr(web.app, "run", lambda **kwargs: calls.update(kwargs))
        monkeypatch.setattr(web, "__THEME__", "dark")

        cli.main.execute(["web", "9100", "--theme", "black", "--ssh_config", ssh_config_file])

        assert calls == {"port": 9100, "debug": False}
        assert web.__THEME__ == "black"
        assert web.app.get_storm().ssh_config.ssh_config_file.name == "ssh_config"

    def test_web_defaults(self, monkeypatch):
        import storm.web as web

        calls = {}
        monkeypatch.setattr(web.app, "run", lambda **kwargs: calls.update(kwargs))
        monkeypatch.setattr(web, "__THEME__", "light")

        cli.main.execute(["web", "--debug"])
        assert calls == {"port": 9002, "debug": True}
        assert web.__THEME__ == "dark"

    def test_web_rejects_unknown_theme(self, capsys):
        with pytest.raises(SystemExit):
            cli.main.execute(["web", "9100", "--theme", "pink"])
        assert "invalid choice" in capsys.readouterr().err


class TestGetStormInstance:
    def test_default_config_path(self, fake_home):
        storm_ = cli.get_storm_instance()
        assert storm_.ssh_config.ssh_config_file == fake_home / ".ssh" / "config"


class TestUpdateConnectionUri:
    def test_hostname_only_keeps_user_and_port(self, run, ssh_config_file):
        _, _, code = run("update", "server1", "--connection_uri", "new.example.com")
        assert code == 0
        options = load(ssh_config_file).is_host_in("server1", return_match=True)["options"]
        assert options["hostname"] == "new.example.com"
        assert options["user"] == "nixcraft"
        assert options["port"] == "4242"

    def test_full_uri_sets_all_parts(self, run, ssh_config_file):
        _, _, code = run("update", "server1", "--connection_uri", "root@[2001:db8::1]:2200")
        assert code == 0
        options = load(ssh_config_file).is_host_in("server1", return_match=True)["options"]
        assert options["hostname"] == "2001:db8::1"
        assert options["user"] == "root"
        assert options["port"] == "2200"

    def test_regex_update_applies_to_every_match(self, run, ssh_config_file):
        _, _, code = run("update", "uk.*", "--connection_uri", "admin@10.9.9.9")
        assert code == 0
        options = load(ssh_config_file).is_host_in("uk.gw.lan uk.lan", return_match=True)["options"]
        assert options["hostname"] == "10.9.9.9"
        assert options["user"] == "admin"

    def test_invalid_uri(self, run):
        _, err, code = run("update", "server1", "--connection_uri", "host:99999")
        assert code == 1
        assert "between 1 and 65535" in err


class TestAddIPv6:
    def test_add_ipv6(self, run, ssh_config_file):
        _, _, code = run("add", "v6", "root@[2001:db8::1]:2222")
        assert code == 0
        options = load(ssh_config_file).is_host_in("v6", return_match=True)["options"]
        assert options == {"hostname": "2001:db8::1", "user": "root", "port": "2222"}

    def test_list_and_search_bracket_ipv6(self, run):
        run("add", "v6", "root@[2001:db8::1]:2222")
        out, _, _ = run("list")
        assert "v6 -> root@[2001:db8::1]:2222" in out
        out, _, _ = run("search", "db8")
        assert "v6 -> root@[2001:db8::1]:2222" in out


class TestWebConfigOption:
    @pytest.mark.parametrize("flag", ["--config", "--ssh_config"])
    def test_config_and_legacy_spelling(self, monkeypatch, ssh_config_file, flag):
        from storm import web

        monkeypatch.setattr(web.app, "run", lambda **kwargs: None)
        cli.main.execute(["web", flag, ssh_config_file])
        assert str(web.app.get_storm().ssh_config.ssh_config_file) == ssh_config_file
