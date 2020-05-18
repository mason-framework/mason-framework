"""Command line interface for mason."""

import importlib
import os

import click
import mason

_DEFAULT_CLI_PLUGS = {'mason_server.server'}
_MASON_CLI_PLUGS = set(
    filter(bool, os.environ.get('MASON_CLI_PLUGS', '').split(',')))
_MASON_CLI_PLUGS.update(_DEFAULT_CLI_PLUGS)


@click.group()
@click.option('--config', help='Mason config file.', default='')
def cli(config: str = None):
    """Mason command line interface."""
    if config:
        mason.load_config(config)


@cli.command()
def version():
    """Print out the current version."""
    print(mason.__version__)


# Initialize command plugins
for cli_plug in _MASON_CLI_PLUGS:
    try:
        module = importlib.import_module(cli_plug)
    except ImportError:
        if cli_plug not in _DEFAULT_CLI_PLUGS:
            raise
