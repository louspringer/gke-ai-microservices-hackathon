"""CLI commands for local registry management."""

import asyncio
import click
import json
from typing import Optional
from ..cluster.registry import LocalRegistryManager, RegistryIntegration
from .base import cli, common_options, handle_common_options, cli_context


@cli.group()
def registry():
    """Manage local Docker registry for fast image storage."""
    pass


@registry.command()
@common_options
@click.option('--wait/--no-wait', default=True, 
              help='Wait for registry to be ready')
def start(config_dir: Optional[click.Path], environment: str, verbose: bool, wait: bool):
    """Start the local Docker registry."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _start_registry():
        try:
            click.echo("🚀 Starting local Docker registry...")
            
            manager = LocalRegistryManager(cli_context.config)
            
            success = await manager.start_registry()
            
            if success:
                status = await manager.get_registry_status()
                click.echo(f"✅ Registry started successfully!")
                click.echo(f"📍 Endpoint: {status.endpoint}")
                click.echo(f"🆔 Container: {status.container_id[:12] if status.container_id else 'N/A'}")
                
                if verbose:
                    click.echo(f"\n📋 Registry Details:")
                    click.echo(f"  • Name: {status.name}")
                    click.echo(f"  • Host: {status.host}")
                    click.echo(f"  • Port: {status.port}")
                    click.echo(f"  • Running: {'Yes' if status.running else 'No'}")
                
                return True
            else:
                click.echo("❌ Failed to start registry", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error starting registry: {e}", err=True)
            return False
    
    success = asyncio.run(_start_registry())
    if not success:
        raise click.Abort()


@registry.command()
@common_options
def stop(config_dir: Optional[click.Path], environment: str, verbose: bool):
    """Stop the local Docker registry."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _stop_registry():
        try:
            click.echo("🛑 Stopping local Docker registry...")
            
            manager = LocalRegistryManager(cli_context.config)
            
            success = await manager.stop_registry()
            
            if success:
                click.echo("✅ Registry stopped successfully!")
                return True
            else:
                click.echo("❌ Failed to stop registry", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error stopping registry: {e}", err=True)
            return False
    
    success = asyncio.run(_stop_registry())
    if not success:
        raise click.Abort()


@registry.command()
@common_options
def remove(config_dir: Optional[click.Path], environment: str, verbose: bool):
    """Remove the local Docker registry container."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _remove_registry():
        try:
            click.echo("🗑️  Removing local Docker registry...")
            
            manager = LocalRegistryManager(cli_context.config)
            
            success = await manager.remove_registry()
            
            if success:
                click.echo("✅ Registry removed successfully!")
                return True
            else:
                click.echo("❌ Failed to remove registry", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error removing registry: {e}", err=True)
            return False
    
    success = asyncio.run(_remove_registry())
    if not success:
        raise click.Abort()


@registry.command()
@common_options
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def status(config_dir: Optional[click.Path], environment: str, verbose: bool, output: str):
    """Show local registry status."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _show_status():
        try:
            manager = LocalRegistryManager(cli_context.config)
            status = await manager.get_registry_status()
            
            if output == 'json':
                status_dict = {
                    'name': status.name,
                    'running': status.running,
                    'host': status.host,
                    'port': status.port,
                    'endpoint': status.endpoint,
                    'container_id': status.container_id,
                    'accessible': status.is_accessible
                }
                click.echo(json.dumps(status_dict, indent=2))
            else:
                # Table format
                click.echo(f"📊 Registry Status: {status.name}")
                click.echo(f"{'─' * 40}")
                
                if not status.running:
                    click.echo("❌ Status: Not running")
                    click.echo("\n💡 Run 'gke-local registry start' to start the registry")
                    return
                
                # Status indicators
                status_icon = "✅" if status.is_accessible else "⚠️"
                running_icon = "🟢" if status.running else "🔴"
                
                click.echo(f"{status_icon} Status: {'Accessible' if status.is_accessible else 'Not Accessible'}")
                click.echo(f"{running_icon} Running: {'Yes' if status.running else 'No'}")
                click.echo(f"📍 Endpoint: {status.endpoint}")
                
                if status.container_id:
                    click.echo(f"🆔 Container: {status.container_id[:12]}")
                
                if verbose and status.is_accessible:
                    # Show image count
                    images = await manager.list_images()
                    click.echo(f"📦 Images: {len(images)}")
                    
                    if images:
                        click.echo(f"\n📋 Recent Images:")
                        for image in images[:5]:  # Show first 5
                            click.echo(f"  • {image['full_name']}")
                        
                        if len(images) > 5:
                            click.echo(f"  ... and {len(images) - 5} more")
                
        except Exception as e:
            click.echo(f"❌ Error getting registry status: {e}", err=True)
            return False
        
        return True
    
    success = asyncio.run(_show_status())
    if not success:
        raise click.Abort()


@registry.command()
@common_options
@click.argument('image')
@click.option('--tag', '-t', help='Registry tag (defaults to same as image)')
def push(config_dir: Optional[click.Path], environment: str, verbose: bool, image: str, tag: Optional[str]):
    """Push an image to the local registry."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _push_image():
        try:
            click.echo(f"📤 Pushing image: {image}")
            
            manager = LocalRegistryManager(cli_context.config)
            
            # Check if registry is running
            status = await manager.get_registry_status()
            if not status.is_accessible:
                click.echo("❌ Registry is not running. Start it with 'gke-local registry start'", err=True)
                return False
            
            success = await manager.push_image(image, tag)
            
            if success:
                registry_tag = tag or image
                registry_url = f"{status.endpoint}/{registry_tag}"
                click.echo(f"✅ Image pushed successfully!")
                click.echo(f"📍 Registry URL: {registry_url}")
                return True
            else:
                click.echo("❌ Failed to push image", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error pushing image: {e}", err=True)
            return False
    
    success = asyncio.run(_push_image())
    if not success:
        raise click.Abort()


@registry.command()
@common_options
@click.argument('image')
@click.option('--tag', '-t', help='Local tag (defaults to same as registry image)')
def pull(config_dir: Optional[click.Path], environment: str, verbose: bool, image: str, tag: Optional[str]):
    """Pull an image from the local registry."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _pull_image():
        try:
            click.echo(f"📥 Pulling image: {image}")
            
            manager = LocalRegistryManager(cli_context.config)
            
            # Check if registry is running
            status = await manager.get_registry_status()
            if not status.is_accessible:
                click.echo("❌ Registry is not running. Start it with 'gke-local registry start'", err=True)
                return False
            
            success = await manager.pull_image(image, tag)
            
            if success:
                local_tag = tag or image
                click.echo(f"✅ Image pulled successfully!")
                click.echo(f"🏷️  Local tag: {local_tag}")
                return True
            else:
                click.echo("❌ Failed to pull image", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error pulling image: {e}", err=True)
            return False
    
    success = asyncio.run(_pull_image())
    if not success:
        raise click.Abort()


@registry.command()
@common_options
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def images(config_dir: Optional[click.Path], environment: str, verbose: bool, output: str):
    """List images in the local registry."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _list_images():
        try:
            manager = LocalRegistryManager(cli_context.config)
            
            # Check if registry is running
            status = await manager.get_registry_status()
            if not status.is_accessible:
                click.echo("❌ Registry is not running. Start it with 'gke-local registry start'", err=True)
                return False
            
            images = await manager.list_images()
            
            if output == 'json':
                click.echo(json.dumps(images, indent=2))
            else:
                if not images:
                    click.echo("📦 No images found in registry")
                    return True
                
                click.echo(f"📦 Registry Images ({len(images)} total)")
                click.echo(f"{'─' * 60}")
                
                # Group by repository
                repos = {}
                for image in images:
                    repo = image['repository']
                    if repo not in repos:
                        repos[repo] = []
                    repos[repo].append(image)
                
                for repo, repo_images in repos.items():
                    click.echo(f"\n📁 {repo}")
                    for image in repo_images:
                        click.echo(f"  • {image['tag']}")
                        if verbose:
                            click.echo(f"    Registry URL: {image['registry_url']}")
            
            return True
                
        except Exception as e:
            click.echo(f"❌ Error listing images: {e}", err=True)
            return False
    
    success = asyncio.run(_list_images())
    if not success:
        raise click.Abort()


@registry.command()
@common_options
@click.option('--keep', '-k', default=5, help='Number of latest images to keep per repository')
@click.confirmation_option(prompt='Are you sure you want to clean up old images?')
def cleanup(config_dir: Optional[click.Path], environment: str, verbose: bool, keep: int):
    """Clean up old images in the registry."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _cleanup_images():
        try:
            click.echo(f"🧹 Cleaning up registry images (keeping latest {keep})...")
            
            manager = LocalRegistryManager(cli_context.config)
            
            # Check if registry is running
            status = await manager.get_registry_status()
            if not status.is_accessible:
                click.echo("❌ Registry is not running. Start it with 'gke-local registry start'", err=True)
                return False
            
            success = await manager.cleanup_images(keep)
            
            if success:
                click.echo("✅ Registry cleanup completed!")
                return True
            else:
                click.echo("❌ Failed to cleanup registry", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error cleaning up registry: {e}", err=True)
            return False
    
    success = asyncio.run(_cleanup_images())
    if not success:
        raise click.Abort()


@registry.command()
@common_options
@click.argument('cluster_name')
def connect(config_dir: Optional[click.Path], environment: str, verbose: bool, cluster_name: str):
    """Connect registry to a Kind cluster."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _connect_registry():
        try:
            click.echo(f"🔗 Connecting registry to cluster: {cluster_name}")
            
            manager = LocalRegistryManager(cli_context.config)
            integration = RegistryIntegration(manager)
            
            # Check if registry is running
            status = await manager.get_registry_status()
            if not status.is_accessible:
                click.echo("❌ Registry is not running. Start it with 'gke-local registry start'", err=True)
                return False
            
            success = await integration.setup_cluster_registry_connection(cluster_name)
            
            if success:
                click.echo(f"✅ Registry connected to cluster: {cluster_name}")
                click.echo(f"📍 Registry endpoint: {status.endpoint}")
                click.echo(f"\n💡 You can now use images like: {status.endpoint}/your-image:tag")
                return True
            else:
                click.echo("❌ Failed to connect registry to cluster", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error connecting registry: {e}", err=True)
            return False
    
    success = asyncio.run(_connect_registry())
    if not success:
        raise click.Abort()