#!/usr/bin/env python3

import sys

from storm import Storm
from storm.parsers.ssh_uri_parser import parse
from storm.utils import get_formatted_message, colored
from storm.kommandr import command, arg, main
from storm.defaults import get_default
from storm import __version__


def get_storm_instance(config_file=None):
    return Storm(config_file)


@command('version')
def version():
    """
    prints the working storm(ssh) version.
    """
    print(__version__)


@command('add')
def add(name, connection_uri, id_file="", o=[], config=None):
    """
    Adds a new entry to sshconfig.
    """
    # Note: o=[] is safe here because argparse creates a new list via action='append'
    storm_ = get_storm_instance(config)

    try:
        # validate name
        if '@' in name:
            raise ValueError('invalid value: "@" cannot be used in name.')

        user, host, port = parse(
            connection_uri,
            user=get_default("user", storm_.defaults),
            port=get_default("port", storm_.defaults)
        )

        storm_.add_entry(name, host, user, port, id_file, o)

        print(
            get_formatted_message(
                f'{name} added to your ssh config. you can connect '
                f'it by typing "ssh {name}".',
                'success')
        )

    except ValueError as error:
        print(get_formatted_message(error, 'error'), file=sys.stderr)
        sys.exit(1)


@command('clone')
def clone(name, clone_name, config=None):
    """
    Clone an entry to the sshconfig.
    """
    storm_ = get_storm_instance(config)

    try:
        # validate name
        if '@' in name:
            raise ValueError('invalid value: "@" cannot be used in name.')

        storm_.clone_entry(name, clone_name)

        print(
            get_formatted_message(
                f'{clone_name} added to your ssh config. you can connect '
                f'it by typing "ssh {clone_name}".',
                'success')
        )

    except ValueError as error:
        print(get_formatted_message(error, 'error'), file=sys.stderr)
        sys.exit(1)


@command('move')
def move(name, entry_name, config=None):
    """
    Move an entry to the sshconfig.
    """
    storm_ = get_storm_instance(config)

    try:
        if '@' in name:
            raise ValueError('invalid value: "@" cannot be used in name.')

        storm_.clone_entry(name, entry_name, keep_original=False)

        print(
            get_formatted_message(
                f'{entry_name} moved in ssh config. you can '
                f'connect it by typing "ssh {entry_name}".',
                'success')
        )

    except ValueError as error:
        print(get_formatted_message(error, 'error'), file=sys.stderr)
        sys.exit(1)


@command('edit')
def edit(name, connection_uri, id_file="", o=[], config=None):
    """
    Edits the related entry in ssh config.
    """
    # Note: o=[] is safe here because argparse creates a new list via action='append'
    storm_ = get_storm_instance(config)

    try:
        if ',' in name:
            name = " ".join(name.split(","))

        user, host, port = parse(
            connection_uri,
            user=get_default("user", storm_.defaults),
            port=get_default("port", storm_.defaults)
        )

        storm_.edit_entry(name, host, user, port, id_file, o)
        print(get_formatted_message(f'"{name}" updated successfully.', 'success'))
    except ValueError as error:
        print(get_formatted_message(error, 'error'), file=sys.stderr)
        sys.exit(1)


@command('update')
def update(name, connection_uri="", id_file="", o=[], config=None):
    """
    Enhanced version of the edit command featuring multiple
    edits using regular expressions to match entries
    """
    # Note: o=[] is safe here because argparse creates a new list via action='append'
    storm_ = get_storm_instance(config)
    settings = {}

    if id_file != "":
        settings['identityfile'] = id_file

    for option in o:
        k, v = option.split("=")
        settings[k] = v

    try:
        storm_.update_entry(name, **settings)
        print(get_formatted_message(f'"{name}" updated successfully.', 'success'))
    except ValueError as error:
        print(get_formatted_message(error, 'error'), file=sys.stderr)
        sys.exit(1)


@command('delete')
def delete(name, config=None):
    """
    Deletes a single host.
    """
    storm_ = get_storm_instance(config)

    try:
        storm_.delete_entry(name)
        print(
            get_formatted_message(
                f'hostname "{name}" deleted successfully.',
                'success')
        )
    except ValueError as error:
        print(get_formatted_message(error, 'error'), file=sys.stderr)
        sys.exit(1)


@command('list')
def list_entries(config=None):
    """
    Lists all hosts from ssh config.
    """
    storm_ = get_storm_instance(config)

    try:
        result = colored('Listing entries:', 'white', attrs=["bold"]) + "\n\n"
        result_stack = ""
        for host in storm_.list_entries(True):

            if host.get("type") == 'entry':
                if host.get("host") != "*":
                    host_name = colored(host["host"], 'green', attrs=["bold"])
                    user = host.get("options").get("user", get_default("user", storm_.defaults))
                    hostname = host.get("options").get("hostname", "[hostname_not_specified]")
                    port = host.get("options").get("port", get_default("port", storm_.defaults))
                    result += f"    {host_name} -> {user}@{hostname}:{port}"

                    extra = False
                    for key, value in host.get("options").items():
                        if key not in ["user", "hostname", "port"]:
                            if not extra:
                                custom_options = colored('\n\t[custom options] ', 'white')
                                result += f" {custom_options}"
                            extra = True

                            if isinstance(value, list):
                                value = ",".join(value)

                            result += f"{key}={value} "
                    if extra:
                        result = result[:-1]

                    result += "\n\n"
                else:
                    result_stack = colored(
                        "   (*) General options: \n", "green", attrs=["bold"]
                    )
                    for key, value in host.get("options").items():
                        if isinstance(value, list):
                            result_stack += f"\t  {colored(key, 'magenta')}: "
                            result_stack += ', '.join(value)
                            result_stack += "\n"
                        else:
                            result_stack += f"\t  {colored(key, 'magenta')}: {value}\n"
                    result_stack = result_stack[:-1] + "\n"

        result += result_stack
        print(get_formatted_message(result, ""))
    except Exception as error:
        print(get_formatted_message(str(error), 'error'), file=sys.stderr)
        sys.exit(1)


@command('search')
def search(search_text, config=None):
    """
    Searches entries by given search text.
    """
    storm_ = get_storm_instance(config)

    try:
        results = storm_.search_host(search_text)
        if len(results) == 0:
            print('no results found.')

        if len(results) > 0:
            message = f'Listing results for {search_text}:\n'
            message += "".join(results)
            print(message)
    except Exception as error:
        print(get_formatted_message(str(error), 'error'), file=sys.stderr)
        sys.exit(1)


@command('delete_all')
def delete_all(config=None):
    """
    Deletes all hosts from ssh config.
    """
    storm_ = get_storm_instance(config)

    try:
        storm_.delete_all_entries()
        print(get_formatted_message('all entries deleted.', 'success'))
    except Exception as error:
        print(get_formatted_message(str(error), 'error'), file=sys.stderr)
        sys.exit(1)


@command('backup')
def backup(target_file, config=None):
    """
    Backups the main ssh configuration into target file.
    """
    storm_ = get_storm_instance(config)
    try:
        storm_.backup(target_file)
    except Exception as error:
        print(get_formatted_message(str(error), 'error'), file=sys.stderr)
        sys.exit(1)


@command('web')
@arg('port', nargs='?', default=9002, type=int)
@arg('theme', nargs='?', default="modern", choices=['modern', 'black', 'storm'])
@arg('debug', action='store_true', default=False)
def web(port, debug=False, theme="modern", ssh_config=None):
    """Starts the web UI."""
    from storm import web as _web
    _web.run(port, debug, theme, ssh_config)


if __name__ == '__main__':
    sys.exit(main())
