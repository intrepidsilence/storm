"""Tests for the Storm CLI commands."""

import os
import shlex
import subprocess
import pytest

from storm import __version__


class TestStormCli:
    """Tests for Storm CLI commands."""

    @pytest.fixture(autouse=True)
    def setup(self, ssh_config_file):
        """Set up test fixtures."""
        self.config_file = ssh_config_file
        self.config_arg = f'--config={self.config_file}'

    def run_cmd(self, cmd):
        """Run a storm command and return output."""
        cmd = f'storm {cmd}'
        cmd = shlex.split(cmd)
        env = os.environ.copy()
        env["TESTMODE"] = "1"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        out, err = process.communicate()
        rc = process.returncode
        return out, err, rc

    def test_list_command(self):
        out, err, rc = self.run_cmd(f'list {self.config_arg}')

        assert out.startswith(b" Listing entries:\n\n")

        hosts = [
            "aws.apache -> wwwdata@1.2.3.4:22",
            "nas01 -> root@192.168.1.100:22",
            "proxyus -> breakfree@vps1.cyberciti.biz:22",
            "server1 -> nixcraft@server1.cyberciti.biz:4242",
            "uk.gw.lan uk.lan -> nixcraft@192.168.0.251:22",
        ]
        custom_options = [
            "[custom options] identityfile=~/.ssh/aws.apache.key",
            "[custom options] identityfile=~/.ssh/nas01.key",
            "identityfile=~/.ssh/vps1.cyberciti.biz.key",
            "localforward=3128 127.0.0.1:3128",
            "[custom options] identityfile=/nfs/shared/users/nixcraft/keys/server1/id_rsa,/tmp/x.rsa",
            "[custom options] proxycommand=ssh nixcraft@gateway.uk.cyberciti.biz nc %h %p 2> /dev/null",
        ]

        for host in hosts:
            assert host.encode('ascii') in out

        for custom_option in custom_options:
            assert custom_option.encode('ascii') in out

        assert err == b''
        assert rc == 0

    def test_version_command(self):
        out, err, rc = self.run_cmd('version')
        assert __version__.encode('ascii') in out
        assert rc == 0

    def test_basic_add(self):
        out, err, rc = self.run_cmd(f'add netscaler ns@42.42.42.42 {self.config_arg}')

        assert b"success" in out
        assert rc == 0

    def test_add_duplicate(self):
        out, err, rc = self.run_cmd(f'add aws.apache test@test.com {self.config_arg}')

        assert out == b''
        assert b'error' in err
        assert rc != 0

    def test_add_invalid_host(self):
        out, err, rc = self.run_cmd(f'add @_@ test.com {self.config_arg}')

        assert out == b''
        assert b'error' in err
        assert rc != 0

    def test_advanced_add(self):
        out, err, rc = self.run_cmd(
            f'add postgresql-server postgres@192.168.1.1 '
            f'--id_file=/tmp/idfilecheck.rsa '
            f'--o "StrictHostKeyChecking=yes" --o "UserKnownHostsFile=/dev/advanced_test" '
            f'{self.config_arg}'
        )

        assert b"success" in out
        assert rc == 0

        with open(self.config_file, encoding="utf-8") as f:
            content = f.read().encode('ascii')
            assert b'identityfile "/tmp/idfilecheck.rsa"' in content
            assert b"stricthostkeychecking yes" in content
            assert b"userknownhostsfile /dev/advanced_test" in content

    def test_add_with_idfile(self):
        out, err, rc = self.run_cmd(
            f'add postgresql-server postgres@192.168.1.1 '
            f'--id_file=/tmp/idfileonlycheck.rsa '
            f'{self.config_arg}'
        )

        assert b"success" in out
        assert rc == 0

        with open(self.config_file, encoding="utf-8") as f:
            content = f.read().encode('ascii')
            assert b'identityfile "/tmp/idfileonlycheck.rsa"' in content

    def test_basic_edit(self):
        out, err, rc = self.run_cmd(
            f'edit aws.apache basic_edit_check@10.20.30.40 {self.config_arg}'
        )

        assert b"success" in out
        assert rc == 0

        with open(self.config_file, encoding="utf-8") as f:
            content = f.read().encode('ascii')
            assert b"basic_edit_check" in content
            assert b"10.20.30.40" in content

    def test_edit_invalid_host(self):
        out, err, rc = self.run_cmd(f'edit @missing_host test.com {self.config_arg}')

        assert out == b''
        assert b'error' in err
        assert rc != 0

    def test_edit_missing_host(self):
        out, err, rc = self.run_cmd(f'edit missing_host test.com {self.config_arg}')

        assert out == b''
        assert b'error' in err
        assert rc != 0

    def test_update(self):
        out, err, rc = self.run_cmd(
            f'update aws.apache --o "user=daghan" --o port=42000 {self.config_arg}'
        )

        assert b"success" in out
        assert rc == 0

        with open(self.config_file, encoding="utf-8") as f:
            content = f.read().encode('ascii')
            assert b"user daghan" in content
            assert b"port 42000" in content

    def test_update_regex(self):
        self.run_cmd(f'add worker alphaworker.com {self.config_arg}')

        # add three machines -- hostnames starts with worker-N
        self.run_cmd(f'add worker-1 worker1.com {self.config_arg}')
        self.run_cmd(f'add worker-2 worker2.com {self.config_arg}')
        self.run_cmd(f'add worker-4 worker4.com {self.config_arg}')

        # another one -- regex shouldn't capture that one though.
        self.run_cmd(f'add worker3 worker3.com {self.config_arg}')

        out, err, rc = self.run_cmd(
            f"update 'worker-[1-5]' --o hostname=boss.com {self.config_arg}"
        )

        assert b"success" in out
        assert rc == 0

        # edit the alphaworker
        out, err, rc = self.run_cmd(f'edit worker alphauser@alphaworker.com {self.config_arg}')
        assert rc == 0

        with open(self.config_file, encoding="utf-8") as f:
            content = f.read().encode('ascii')
            assert b"worker1.com" not in content
            assert b"worker2.com" not in content
            assert b"worker4.com" not in content
            assert b"worker3.com" in content
            assert b"alphauser" in content

    def test_update_invalid_regex(self):
        out, err, rc = self.run_cmd(
            f"update 'drogba-[0-5]' --o hostname=boss.com {self.config_arg}"
        )

        assert out == b''
        assert b'error' in err
        assert rc != 0

    def test_delete(self):
        out, err, rc = self.run_cmd(f"delete server1 {self.config_arg}")
        assert b"success" in out
        assert rc == 0

    def test_delete_invalid_hostname(self):
        out, err, rc = self.run_cmd("delete unknown_server")

        assert out == b''
        assert b'error' in err
        assert rc != 0

    def test_search(self):
        out, err, rc = self.run_cmd(f"search aws {self.config_arg}")

        assert out.startswith(b'Listing results for aws:')
        assert b'aws.apache' in out
        assert rc == 0

    def test_backup(self, tmp_path):
        backup_file = tmp_path / "ssh_backup"
        out, err, rc = self.run_cmd(f"backup {backup_file} {self.config_arg}")

        assert backup_file.exists()
        assert rc == 0

    def test_invalid_search(self):
        out, err, rc = self.run_cmd(f"search THEREISNOTHINGRELATEDWITHME {self.config_arg}")

        assert b'no results found.' in out
        assert rc == 0

    def test_delete_all(self):
        out, err, rc = self.run_cmd(f'delete_all {self.config_arg}')

        assert b'all entries deleted' in out
        assert rc == 0
