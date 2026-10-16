import sys

from storm import Storm, __version__
from storm.defaults import get_default
from storm.kommandr import arg, command, main
from storm.parsers.ssh_uri_parser import format_uri, parse, split_uri
from storm.utils import colored, get_formatted_message


def get_storm_instance(config_file=None):
    return Storm(config_file)


@command('version')
def version():
    """
    prints the working storm(ssh) version.
    """
    print(__version__)


@command('add')
def add(name, connection_uri, id_file="", o=[], config=None):  # noqa: B006
    """
    Adds a new entry to sshconfig.
    """
    # o=[] tells kommandr to make --o repeatable (action='append'); argparse
    # builds a fresh list per run, so the shared default is never mutated.
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
def edit(name, connection_uri, id_file="", o=[], config=None):  # noqa: B006
    """
    Edits the related entry in ssh config.
    """
    # o=[] tells kommandr to make --o repeatable (action='append'); argparse
    # builds a fresh list per run, so the shared default is never mutated.
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
def update(name, connection_uri="", id_file="", o=[], config=None):  # noqa: B006
    """
    Enhanced version of the edit command featuring multiple
    edits using regular expressions to match entries
    """
    # o=[] tells kommandr to make --o repeatable (action='append'); argparse
    # builds a fresh list per run, so the shared default is never mutated.
    storm_ = get_storm_instance(config)
    settings = {}

    try:
        if connection_uri != "":
            # Only the parts written in the uri change; "web1.example.com"
            # updates the hostname and keeps each host's user and port.
            user, host, port = split_uri(connection_uri)
            settings['hostname'] = host
            if user is not None:
                settings['user'] = user
            if port is not None:
                settings['port'] = port

        if id_file != "":
            settings['identityfile'] = id_file

        for option in o:
            if '=' not in option:
                raise ValueError(f'invalid option: "{option}" must be in key=value form.')
            k, v = option.split("=", 1)
            settings[k.lower()] = v

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
                    result += f"    {host_name} -> {format_uri(user, hostname, port)}"

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
    except (OSError, ValueError) as error:
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
    except (OSError, ValueError) as error:
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
    except (OSError, ValueError) as error:
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
    except (OSError, ValueError) as error:
        print(get_formatted_message(str(error), 'error'), file=sys.stderr)
        sys.exit(1)


@command('web')
@arg('port', nargs='?', default=9002, type=int)
@arg('theme', nargs='?', default="dark",
     choices=['dark', 'light', 'auto', 'modern', 'black', 'storm'])
@arg('debug', action='store_true', default=False)
@arg('config', '--config', '--ssh_config')
def web(port, debug=False, theme="dark", config=None):
    """Starts the web UI."""
    # --ssh_config is the pre-1.0 spelling and modern/black/storm the pre-1.2
    # theme names; both are kept so existing scripts work.
    from storm import web as _web
    _web.run(port, debug, theme, config)


if __name__ == '__main__':
    sys.exit(main())
