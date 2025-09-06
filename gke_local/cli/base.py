"""Base CLI framework with command parsing and help system."""

import click
import sys
from pathlib import Path
from typing import Optional
from ..config.manager import ConfigManager
from ..config.models import GKELocalConfig, LogLevel
import logging


class CLIContext:
    """Shared context for CLI commands."""
    
    def __init__(self):
        self.config_manager: Optional[ConfigManager] = None
        self.config: Optional[GKELocalConfig] = None
        self.verbose: bool = False
        self.config_dir: Optional[Path] = None
    
    def load_config(self, environment: str = "local") -> GKELocalConfig:
        """Load configuration for the given environment."""
        if not self.config_manager:
            self.config_manager = ConfigManager(self.config_dir)
        
        self.config = self.config_manager.load_config(environment)
        self._setup_logging()
        return self.config
    
    def _setup_logging(self):
        """Setup logging based on configuration."""
        if not self.config:
            return
        
        level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR
        }
        
        log_level = level_map.get(self.config.log_level, logging.INFO)
        if self.verbose:
            log_level = logging.DEBUG
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


# Global CLI context
cli_context = CLIContext()


def common_options(f):
    """Decorator to add common CLI options to commands."""
    f = click.option(
        '--config-dir', '-c',
        type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
        help='Directory containing configuration files'
    )(f)
    f = click.option(
        '--environment', '-e',
        default='local',
        help='Environment to use (local, staging, production)'
    )(f)
    f = click.option(
        '--verbose', '-v',
        is_flag=True,
        help='Enable verbose output'
    )(f)
    return f


def handle_common_options(config_dir: Optional[Path], environment: str, verbose: bool):
    """Handle common CLI options and setup context."""
    cli_context.config_dir = config_dir
    cli_context.verbose = verbose
    
    try:
        cli_context.load_config(environment)
        if verbose:
            click.echo(f"Loaded configuration from: {cli_context.config_manager.get_loaded_files()}")
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)


@click.group()
@click.version_option()
@click.pass_context
def cli(ctx):
    """
    GKE Local Development Environment
    
    A comprehensive local development platform that simulates Google Cloud Run 
    and GKE Autopilot locally with integrated CI/CD pipeline.
    """
    ctx.ensure_object(dict)


@cli.command()
@common_options
def init(config_dir: Optional[Path], environment: str, verbose: bool):
    """Initialize a new GKE Local project."""
    handle_common_options(config_dir, environment, verbose)
    
    click.echo("🚀 Initializing GKE Local project...")
    
    # Create project structure
    project_dirs = [
        "src",
        "services", 
        "configs",
        "scripts",
        "tests"
    ]
    
    for dir_name in project_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            click.echo(f"Created directory: {dir_name}")
    
    # Create default configuration if it doesn't exist
    config_path = Path("gke-local.yaml")
    if not config_path.exists():
        cli_context.config_manager._create_default_config(config_path)
        click.echo(f"Created default configuration: {config_path}")
    
    # Create example service
    example_service_dir = Path("services/example-service")
    if not example_service_dir.exists():
        example_service_dir.mkdir(parents=True)
        
        # Create example FastAPI service
        example_code = '''"""Example FastAPI service for GKE Local."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Example Service")


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", service="example-service")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello from GKE Local!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        
        with open(example_service_dir / "main.py", "w") as f:
            f.write(example_code)
        
        click.echo(f"Created example service: {example_service_dir}")
    
    click.echo("✅ GKE Local project initialized successfully!")
    click.echo("\nNext steps:")
    click.echo("1. Review and customize gke-local.yaml")
    click.echo("2. Run 'gke-local start' to start the local environment")
    click.echo("3. Deploy services with 'gke-local deploy <service-name>'")


@cli.command()
@common_options
def config(config_dir: Optional[Path], environment: str, verbose: bool):
    """Show current configuration."""
    handle_common_options(config_dir, environment, verbose)
    
    click.echo(f"Configuration for environment: {environment}")
    click.echo(f"Project: {cli_context.config.project_name}")
    click.echo(f"Cluster: {cli_context.config.cluster.name}")
    click.echo(f"Kubernetes version: {cli_context.config.cluster.kubernetes_version}")
    click.echo(f"Nodes: {cli_context.config.cluster.nodes}")
    
    click.echo("\nSimulation settings:")
    click.echo(f"  Cloud Run: {'enabled' if cli_context.config.simulation.cloud_run.enabled else 'disabled'}")
    click.echo(f"  Autopilot: {'enabled' if cli_context.config.simulation.autopilot.enabled else 'disabled'}")
    
    click.echo("\nServices:")
    click.echo(f"  Monitoring: {'enabled' if cli_context.config.services.monitoring.prometheus else 'disabled'}")
    click.echo(f"  AI support: {'enabled' if cli_context.config.services.ai.model_serving else 'disabled'}")
    
    if verbose:
        click.echo(f"\nConfiguration files loaded:")
        for file_path in cli_context.config_manager.get_loaded_files():
            click.echo(f"  {file_path}")


@cli.command()
@common_options
def validate(config_dir: Optional[Path], environment: str, verbose: bool):
    """Validate configuration files."""
    handle_common_options(config_dir, environment, verbose)
    
    click.echo("🔍 Validating configuration...")
    
    try:
        # Configuration is already loaded and validated in handle_common_options
        click.echo("✅ Configuration is valid!")
        
        # Additional validation checks
        warnings = []
        
        # Check for common issues
        if cli_context.config.cluster.nodes < 1:
            warnings.append("Cluster should have at least 1 node")
        
        if not cli_context.config.watch_paths:
            warnings.append("No watch paths configured for hot reload")
        
        if warnings:
            click.echo("\n⚠️  Warnings:")
            for warning in warnings:
                click.echo(f"  - {warning}")
        
    except Exception as e:
        click.echo(f"❌ Configuration validation failed: {e}", err=True)
        sys.exit(1)


# Import cluster commands to register them
try:
    from . import cluster_commands
except ImportError:
    pass

if __name__ == '__main__':
    cli()