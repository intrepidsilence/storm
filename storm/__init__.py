from operator import itemgetter
import re
from shutil import copyfile

from .parsers.ssh_config_parser import ConfigParser
from .defaults import get_default


__version__ = '1.0.0'

ERRORS = {
    "already_in": "{name} is already in your sshconfig. "
                  "use storm edit or storm update to modify.",
    "not_found": "{name} doesn't exist in your sshconfig. "
                 "use storm add command to add.",
}

DELETED_SIGN = "DELETED"


class Storm:

    def __init__(self, ssh_config_file=None):
        self.ssh_config = ConfigParser(ssh_config_file)
        self.ssh_config.load()
        self.defaults = self.ssh_config.defaults

    def add_entry(self, name, host, user, port, id_file, custom_options=None):
        if custom_options is None:
            custom_options = []
        if self.is_host_in(name):
            raise ValueError(ERRORS["already_in"].format(name=name))

        options = self.get_options(host, user, port, id_file, custom_options)

        self.ssh_config.add_host(name, options)
        self.ssh_config.write_to_ssh_config()

        return True

    def clone_entry(self, name, clone_name, keep_original=True):
        host = self.is_host_in(name, return_match=True)
        if not host:
            raise ValueError(ERRORS["not_found"].format(name=name))

        # check if an entry with the clone name already exists
        if name == clone_name \
                or self.is_host_in(clone_name, return_match=True) is not None:
            raise ValueError(ERRORS["already_in"].format(name=clone_name))

        self.ssh_config.add_host(clone_name, host.get('options'))
        if not keep_original:
            self.ssh_config.delete_host(name)
        self.ssh_config.write_to_ssh_config()

        return True

    def edit_entry(self, name, host, user, port, id_file, custom_options=None):
        if custom_options is None:
            custom_options = []
        if not self.is_host_in(name):
            raise ValueError(ERRORS["not_found"].format(name=name))

        options = self.get_options(host, user, port, id_file, custom_options)
        self.ssh_config.update_host(name, options, use_regex=False)
        self.ssh_config.write_to_ssh_config()

        return True

    def update_entry(self, name, **kwargs):
        if not self.is_host_in(name, regexp_match=True):
            raise ValueError(ERRORS["not_found"].format(name=name))

        self.ssh_config.update_host(name, kwargs, use_regex=True)
        self.ssh_config.write_to_ssh_config()

        return True

    def delete_entry(self, name):
        self.ssh_config.delete_host(name)
        self.ssh_config.write_to_ssh_config()

        return True

    def list_entries(self, order=False, only_servers=False):
        config_data = self.ssh_config.config_data

        # required for the web api.
        if only_servers:
            config_data = [
                entry for entry in config_data
                if entry.get("type") == 'entry' and entry.get("host") != '*'
            ]

        if order:
            config_data = sorted(config_data, key=itemgetter("host"))
        return config_data

    def delete_all_entries(self):
        self.ssh_config.delete_all_hosts()

        return True

    def search_host(self, search_string):
        results = self.ssh_config.search_host(search_string)
        formatted_results = []
        for host_entry in results:
            host = host_entry.get("host")
            user = host_entry.get("options").get("user", get_default("user", self.defaults))
            hostname = host_entry.get("options").get("hostname", "[hostname_not_specified]")
            port = host_entry.get("options").get("port", get_default("port", self.defaults))
            formatted_results.append(f"    {host} -> {user}@{hostname}:{port}\n")

        return formatted_results

    def get_options(self, host, user, port, id_file, custom_options):
        options = {
            'hostname': host,
            'user': user,
            'port': port,
        }

        if id_file == DELETED_SIGN:
            options['deleted_fields'] = ["identityfile"]
        elif id_file:
            options['identityfile'] = id_file

        if custom_options:
            for custom_option in custom_options:
                if '=' in custom_option:
                    key, value = custom_option.split("=", 1)
                    options[key.lower()] = value
        options = self._quote_options(options)

        return options

    def is_host_in(self, host, return_match=False, regexp_match=False):
        for host_ in self.ssh_config.config_data:
            if host_.get("host") == host \
                    or (regexp_match and re.match(host, host_.get("host"))):
                return host_ if return_match else True
        return None if return_match else False

    def backup(self, target_file):
        return copyfile(self.ssh_config.ssh_config_file, target_file)

    def _quote_options(self, options):
        keys_should_be_quoted = ["identityfile"]
        for key in keys_should_be_quoted:
            if key in options:
                options[key] = f'"{options[key].strip(chr(34))}"'

        return options
