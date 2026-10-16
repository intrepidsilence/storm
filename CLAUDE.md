# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Storm is a command-line tool for managing SSH connections via `~/.ssh/config`. It provides commands for adding, editing, deleting, listing, and searching SSH host entries. The package is published to PyPI as `stormssh`.

**Version:** 1.0.0
**Python:** 3.11+

## Installation from Source

```bash
# Clone the repository
git clone https://github.com/intrepidsilence/storm.git
cd storm

# Install directly from source
pip install .

# Or install in development/editable mode (changes to source are reflected immediately)
pip install -e .
```

## Build & Development Commands

```bash
# Install in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=storm --cov-report=term-missing

# Run a specific test
pytest tests/test_storm.py::TestStorm::test_add_host -v
pytest tests/test_cli.py::TestStormCli::test_list_command -v

# Run with tox (multi-version testing)
tox

# Lint with ruff
ruff check storm/
```

## Architecture

### Entry Point
- `storm/__main__.py` - CLI entry point, defines all commands using decorators from `kommandr.py`
- `storm/kommandr.py` - Custom argument parser framework built on argparse that converts decorated functions into CLI commands

### Core Library
- `storm/__init__.py` - Main `Storm` class that provides the Python API for managing SSH config entries (add, edit, delete, clone, search, backup)

### Parsers (`storm/parsers/`)
- `ssh_config_parser.py` - `ConfigParser` class that reads/writes `~/.ssh/config` files; extends paramiko's `SSHConfig` via `StormConfig` to preserve comments and empty lines
- `ssh_uri_parser.py` - Parses SSH connection URIs like `user@host:port`
- `storm_config_parser.py` - Reads storm's own config from `~/.stormssh/config` (JSON format for command aliases)

### Web UI
- `storm/web.py` - Flask-based web interface for managing SSH connections

## Key Patterns

**Command Registration**: Commands are registered via `@command('name')` decorator in `__main__.py`. The `@arg` decorator configures argument parsing. Command aliases are loaded from `~/.stormssh/config`.

**Config Data Structure**: SSH entries are stored as dicts with `host`, `options`, `type`, and `order` keys. The `order` field preserves entry sequence in the config file.

**Testing**: Tests use pytest with fixtures defined in `tests/conftest.py`. An autouse `fake_home` fixture points `HOME` at a temp dir so no test touches the real `~/.ssh/config` or `~/.stormssh/config`. `tests/test_cli.py` runs `python -m storm` as a subprocess (end-to-end, invisible to coverage); `tests/test_commands.py` dispatches the same commands in-process via `storm.__main__.main.execute([...])` so coverage sees them. `TESTMODE=1` strips ANSI color codes. Line coverage is 100%; keep it there.

**Security invariants**: every value written to the ssh config goes through `validate_value` / `validate_option_name` in `storm/__init__.py` (no control characters, so no directive injection). The web UI (`storm/web.py`) whitelists `?theme=` against `THEMES` and rejects requests whose `Host` is not in `ALLOWED_HOSTS`. `ConfigParser.write_to_ssh_config` writes atomically through symlinks and preserves file mode.

## Dependencies

- **paramiko** - SSH config parsing
- **Flask** - Web UI
- **termcolor** - Colored terminal output
