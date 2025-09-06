"""Main entry point for the GKE Local CLI."""

from .base import cli
from . import cluster_commands  # Import to register commands
from . import registry_commands  # Import to register commands

if __name__ == '__main__':
    cli()