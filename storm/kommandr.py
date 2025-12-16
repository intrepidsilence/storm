"""
Simple module helps you convert your ordinary functions into cool
command-line interfaces using argparse in backyard.
"""

import sys
import inspect
import argparse
from itertools import zip_longest
from collections.abc import Callable

from .parsers.storm_config_parser import get_storm_config
from . import __version__


class AliasedSubParsersAction(argparse._SubParsersAction):

    class _AliasedPseudoAction(argparse.Action):
        def __init__(self, name, aliases, help):
            dest = name
            if aliases:
                dest += f' ({"-".join(aliases)})'
            super().__init__(option_strings=[], dest=dest, help=help)

    def add_parser(self, name, **kwargs):
        if 'aliases' in kwargs:
            aliases = kwargs['aliases']
            del kwargs['aliases']
        else:
            aliases = []

        parser = super().add_parser(name, **kwargs)

        # Make the aliases work.
        if aliases:
            for alias in aliases:
                self._name_parser_map[alias] = parser

        # Make the help text reflect them, first removing old help entry.
        if 'help' in kwargs:
            help = kwargs.pop('help')
            self._choices_actions.pop()
            pseudo_action = self._AliasedPseudoAction(name, aliases, help)
            self._choices_actions.append(pseudo_action)

        return parser


class prog:
    """Class to hold an isolated command namespace"""

    _COMMAND_FLAG = '_command'
    _POSITIONAL = type('_positional', (), {})

    def __init__(self, **kwargs):
        """Constructor

        :param version: program version
        :param type: str

        :param **kwargs: keyword arguments those passed through to
                         argparse.ArgumentParser constructor
        :param type: dict

        """
        kwargs.update({
            'formatter_class': argparse.RawTextHelpFormatter,
            'epilog': "storm is a command line tool to manage ssh connections.\n"
                      "get more information at: github.com/emre/storm",
        })

        self.parser = argparse.ArgumentParser(**kwargs)
        self.parser.register('action', 'parsers', AliasedSubParsersAction)
        self.parser.formatter_class.width = 300
        self.parser.add_argument(
            '-v',
            '--version',
            action='version',
            version=__version__
        )

        self.subparsers = self.parser.add_subparsers(
            title="commands", metavar="COMMAND"
        )
        self.subparsers.required = True

    def command(self, *args, **kwargs):
        """Convenient decorator simply creates corresponding command"""
        if len(args) == 1 and isinstance(args[0], Callable):
            return self._generate_command(args[0])
        else:
            def _command(func):
                return self._generate_command(func, *args, **kwargs)
            return _command

    def arg(self, arg_name, *args, **kwargs):
        """Decorator function configures any arg by given ``arg_name`` with
        supplied ``args`` and ``kwargs`` passing them transparently to
        argparse.ArgumentParser.add_argument function

        :param arg_name: arg name to configure
        :param type: str

        """
        def wrapper(func):
            if not getattr(func, 'argopts', None):
                func.argopts = {}
            func.argopts[arg_name] = (args, kwargs)
            return func
        return wrapper

    def _generate_command(self, func, name=None, **kwargs):
        """Generates a command parser for given func.

        :param func: func to generate related command parser
        :param type: function

        :param name: command name
        :param type: str

        :param **kwargs: keyword arguments those passed through to
                         argparse.ArgumentParser.add_parser
        :param type: dict

        """
        func_pointer = name or func.__name__
        storm_config = get_storm_config()
        aliases = None
        if 'aliases' in storm_config:
            for command, alias_list in storm_config.get("aliases").items():
                if func_pointer == command:
                    aliases = alias_list
                    break

        func_help = func.__doc__ and func.__doc__.strip()
        subparser = self.subparsers.add_parser(name or func.__name__,
                                               aliases=aliases,
                                               help=func_help)
        spec = inspect.getfullargspec(func)
        opts = reversed(list(zip_longest(reversed(spec.args or []),
                                         reversed(spec.defaults or []),
                                         fillvalue=self._POSITIONAL())))
        for k, v in opts:
            argopts = getattr(func, 'argopts', {})
            args, kwargs = argopts.get(k, ([], {}))
            args = list(args)
            is_positional = isinstance(v, self._POSITIONAL)
            options = [arg for arg in args if arg.startswith('-')]
            if isinstance(v, list):
                kwargs.update({
                    'action': 'append',
                })
            if is_positional:
                if options:
                    args = options
                    kwargs.update({'required': True, 'dest': k})
                else:
                    args = [k]

            else:
                args = options or [f'--{k}']
                kwargs.update({'default': v, 'dest': k})

            subparser.add_argument(*args, **kwargs)

        subparser.set_defaults(**{self._COMMAND_FLAG: func})
        return func

    def execute(self, arg_list):
        """Main function to parse and dispatch commands by given ``arg_list``

        :param arg_list: all arguments provided by the command line
        :param type: list

        """
        arg_map = self.parser.parse_args(arg_list).__dict__
        command = arg_map.pop(self._COMMAND_FLAG)
        return command(**arg_map)

    def __call__(self):
        """Calls execute with sys.argv excluding script name which comes first."""
        self.execute(sys.argv[1:])


main = prog()
arg = main.arg
command = main.command
execute = main.execute
