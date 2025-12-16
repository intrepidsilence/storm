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

**Testing**: Tests use pytest with fixtures defined in `tests/conftest.py`. CLI tests run the `storm` command as a subprocess with `TESTMODE=1` env var to strip ANSI color codes.

## Dependencies

- **paramiko** - SSH config parsing
- **Flask** - Web UI
- **termcolor** - Colored terminal output
