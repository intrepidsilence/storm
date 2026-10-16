"""Tests for the kommandr command-line framework."""

import pytest

from storm import kommandr, __version__


@pytest.fixture
def program(monkeypatch):
    """A fresh, isolated command namespace with no storm config aliases."""
    monkeypatch.setattr(kommandr, "get_storm_config", lambda: {})
    return kommandr.prog(prog="test")


class TestCommandRegistration:
    def test_bare_decorator_uses_function_name(self, program):
        @program.command
        def greet(name):
            """Says hello."""
            return f"hello {name}"

        assert program.execute(["greet", "bob"]) == "hello bob"

    def test_named_decorator(self, program):
        @program.command("say-hi")
        def anything(name):
            return name

        assert program.execute(["say-hi", "amy"]) == "amy"

    def test_defaults_become_options(self, program):
        @program.command("opts")
        def opts(flag="x", items=[]):
            return flag, items

        assert program.execute(["opts"]) == ("x", [])
        assert program.execute(["opts", "--flag", "y", "--items", "a", "--items", "b"]) == \
            ("y", ["a", "b"])

    def test_arg_decorator_configures_argument(self, program):
        @program.command("num")
        @program.arg("count", type=int)
        def num(count):
            return count

        assert program.execute(["num", "5"]) == 5

    def test_positional_with_option_string_is_required(self, program, capsys):
        @program.command("req")
        @program.arg("target", "-t", "--target")
        def req(target):
            return target

        assert program.execute(["req", "-t", "here"]) == "here"
        with pytest.raises(SystemExit):
            program.execute(["req"])
        assert "required" in capsys.readouterr().err

    def test_keyword_with_option_string(self, program):
        @program.command("kw")
        @program.arg("level", "-l")
        def kw(level="low"):
            return level

        assert program.execute(["kw"]) == "low"
        assert program.execute(["kw", "-l", "high"]) == "high"

    def test_missing_command_is_an_error(self, program, capsys):
        with pytest.raises(SystemExit):
            program.execute([])
        assert "required" in capsys.readouterr().err

    def test_version_flag(self, program, capsys):
        with pytest.raises(SystemExit) as exc:
            program.execute(["--version"])
        assert exc.value.code == 0
        assert capsys.readouterr().out.strip() == __version__


class TestAliases:
    def test_aliases_from_storm_config(self, monkeypatch, capsys):
        monkeypatch.setattr(
            kommandr, "get_storm_config",
            lambda: {"aliases": {"other": ["o"], "list": ["ls", "l"]}},
        )
        program = kommandr.prog(prog="test")

        @program.command("list")
        def list_():
            """Lists things."""
            return "listed"

        @program.command("plain")
        def plain():
            return "plain"

        assert program.execute(["plain"]) == "plain"
        assert program.execute(["list"]) == "listed"
        assert program.execute(["ls"]) == "listed"
        assert program.execute(["l"]) == "listed"

        with pytest.raises(SystemExit):
            program.execute(["--help"])
        assert "list (ls-l)" in capsys.readouterr().out

    def test_command_without_help_text(self, program):
        @program.command("nodoc")
        def nodoc():
            return "ok"

        assert program.execute(["nodoc"]) == "ok"

    def test_add_parser_without_help_keeps_choices(self, program):
        before = list(program.subparsers._choices_actions)
        program.subparsers.add_parser("plain")
        assert program.subparsers._choices_actions == before


class TestCall:
    def test_call_uses_sys_argv(self, program, monkeypatch):
        seen = []

        @program.command("echo")
        def echo(word):
            seen.append(word)

        monkeypatch.setattr("sys.argv", ["storm", "echo", "hi"])
        program()
        assert seen == ["hi"]
