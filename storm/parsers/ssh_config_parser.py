from pathlib import Path
from operator import itemgetter
import os
import re
import tempfile

from paramiko.config import SSHConfig

# Directives OpenSSH accumulates when they appear more than once in a block;
# every other directive keeps only its first value.
MULTI_VALUE_KEYS = (
    'certificatefile',
    'dynamicforward',
    'identityfile',
    'localforward',
    'remoteforward',
    'sendenv',
)

# "Key Value", "Key=Value" and "Key = Value" are all valid directive forms.
DIRECTIVE_RE = re.compile(r"^([^\s=]+)(?:\s*=\s*|\s+)(.*)$")


class StormConfig(SSHConfig):
    def parse(self, file_obj):
        """
        Read an OpenSSH config from the given file object.

        @param file_obj: a file-like object to read the config file from
        @type file_obj: file
        """
        order = 1
        host = {"host": ['*'], "config": {}}

        for line in file_obj:
            line = line.rstrip('\n').lstrip()
            if line == '':
                self._config.append({
                    'type': 'empty_line',
                    'value': line,
                    'host': '',
                    'order': order,
                })
                order += 1
                continue

            if line.startswith('#'):
                self._config.append({
                    'type': 'comment',
                    'value': line,
                    'host': '',
                    'order': order,
                })
                order += 1
                continue

            match = DIRECTIVE_RE.match(line)
            if not match:
                raise ValueError(f'Unparsable line: {line!r}')
            key, value = match.group(1).lower(), match.group(2)
            if key == 'host':
                self._config.append(host)
                value = value.split()
                host = {
                    key: value,
                    'config': {},
                    'type': 'entry',
                    'order': order
                }
                order += 1
            elif key in MULTI_VALUE_KEYS:
                if key in host['config']:
                    host['config'][key].append(value)
                else:
                    host['config'][key] = [value]
            elif key not in host['config']:
                host['config'].update({key: value})
        self._config.append(host)


class ConfigParser:
    """
    Config parser for ~/.ssh/config files.
    """

    def __init__(self, ssh_config_file=None):
        if not ssh_config_file:
            ssh_config_file = self.get_default_ssh_config_file()

        self.defaults = {}
        self.ssh_config_file = Path(ssh_config_file)

        if not self.ssh_config_file.exists():
            self.ssh_config_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.ssh_config_file.touch(mode=0o600)

        self.config_data = []

    def get_default_ssh_config_file(self):
        return str(Path.home() / ".ssh" / "config")

    def load(self):
        config = StormConfig()

        with open(self.ssh_config_file, encoding="utf-8") as fd:
            config.parse(fd)

        for entry in config.__dict__.get("_config"):
            if entry.get("host") == ["*"]:
                self.defaults.update(entry.get("config"))

            if entry.get("type") in ["comment", "empty_line"]:
                self.config_data.append(entry)
                continue

            host_item = {
                'host': entry["host"][0],
                'options': entry.get("config"),
                'type': 'entry',
                'order': entry.get("order", 0),
            }

            if len(entry["host"]) > 1:
                host_item.update({
                    'host': " ".join(entry["host"]),
                })

            # minor bug in paramiko.SSHConfig that duplicates
            # "Host *" entries.
            if entry.get("config") and len(entry.get("config")) > 0:
                self.config_data.append(host_item)

        return self.config_data

    def add_host(self, host, options):
        self.config_data.append({
            'host': host,
            'options': options,
            'type': 'entry',
            'order': self.get_last_index(),
        })

        return self

    def update_host(self, host, options, use_regex=False):
        options = dict(options)
        deleted_fields = options.pop("deleted_fields", [])

        for index, host_entry in enumerate(self.config_data):
            if host_entry.get("host") == host or \
                    (use_regex and re.match(host, host_entry.get("host"))):

                for deleted_field in deleted_fields:
                    self.config_data[index]["options"].pop(deleted_field, None)

                self.config_data[index]["options"].update(options)

        return self

    def search_host(self, search_string):
        results = []
        for host_entry in self.config_data:
            if host_entry.get("type") != 'entry':
                continue
            if host_entry.get("host") == "*":
                continue

            searchable_information = host_entry.get("host")
            for key, value in host_entry.get("options").items():
                if isinstance(value, list):
                    value = " ".join(value)
                if isinstance(value, int):
                    value = str(value)

                searchable_information += " " + value

            if search_string in searchable_information:
                results.append(host_entry)

        return results

    def delete_host(self, host):
        remaining = [
            host_entry for host_entry in self.config_data
            if host_entry.get("host") != host
        ]

        if len(remaining) == len(self.config_data):
            raise ValueError('No host found')
        self.config_data = remaining
        return self

    def delete_all_hosts(self):
        self.config_data = []
        self.write_to_ssh_config()

        return self

    def dump(self):
        file_content = ""
        self.config_data = sorted(self.config_data, key=itemgetter("order"))

        for host_item in self.config_data:
            if host_item.get("type") in ['comment', 'empty_line']:
                file_content += host_item.get("value") + "\n"
                continue
            host_item_content = f"Host {host_item.get('host')}\n"
            for key, value in host_item.get("options").items():
                if isinstance(value, list):
                    sub_content = ""
                    for value_ in value:
                        sub_content += f"    {key} {value_}\n"
                    host_item_content += sub_content
                else:
                    host_item_content += f"    {key} {value}\n"
            file_content += host_item_content

        return file_content

    def write_to_ssh_config(self):
        data = self.dump()

        # Write the real file behind a symlink (dotfile managers), and swap it
        # in atomically so a crash never leaves a truncated ssh config.
        target = self.ssh_config_file.resolve()
        try:
            mode = target.stat().st_mode & 0o777
        except FileNotFoundError:
            mode = 0o600

        fd, tmp_path = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(data)
            os.chmod(tmp_path, mode)
            os.replace(tmp_path, target)
        except BaseException:
            os.unlink(tmp_path)
            raise
        return self

    def get_last_index(self):
        indexes = [item.get("order", 0) for item in self.config_data if item.get("order")]
        return max(indexes) if indexes else 0
