"""CLI commands for cluster management."""

import asyncio
import click
import json
from typing import Optional
from ..cluster.kind_manager import KindManager
from ..cluster.lifecycle import ClusterLifecycleManager, ClusterOrchestrator
from ..cluster.templates import ClusterTemplates
from .base import cli, common_options, handle_common_options, cli_context


@cli.group()
def cluster():
    """Manage Kind clusters for local development."""
    pass


@cluster.command()
@common_options
@click.option('--template', '-t', default='minimal', 
              help='Cluster template to use (minimal, ai, staging, autopilot)')
@click.option('--wait/--no-wait', default=True, 
              help='Wait for cluster to be ready')
def create(config_dir: Optional[click.Path], environment: str, verbose: bool, 
           template: str, wait: bool):
    """Create a new Kind cluster."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _create_cluster():
        try:
            # Validate template
            if template not in ClusterTemplates.list_templates():
                available = ', '.join(ClusterTemplates.list_templates())
                click.echo(f"❌ Invalid template '{template}'. Available: {available}", err=True)
                return False
            
            click.echo(f"🚀 Creating cluster '{cli_context.config.cluster.name}' with template '{template}'...")
            
            # Create lifecycle manager
            manager = ClusterLifecycleManager(cli_context.config)
            
            # Add event handlers for progress updates
            def on_creating(event):
                click.echo("📦 Creating cluster infrastructure...")
            
            def on_ready(event):
                click.echo("✅ Cluster is ready!")
            
            def on_error(event):
                click.echo(f"❌ Error: {event.data.get('error', 'Unknown error')}", err=True)
            
            manager.add_event_handler('cluster_creating', on_creating)
            manager.add_event_handler('cluster_ready', on_ready)
            manager.add_event_handler('cluster_error', on_error)
            
            # Create cluster
            success = await manager.create_and_start()
            
            if success:
                status = await manager.get_status()
                click.echo(f"🎉 Cluster '{status.name}' created successfully!")
                click.echo(f"📊 Nodes: {len(status.nodes)}")
                click.echo(f"🔧 Kubeconfig: {status.kubeconfig_path}")
                
                if verbose:
                    click.echo("\n📋 Cluster Details:")
                    for i, node in enumerate(status.nodes):
                        node_name = node.get('metadata', {}).get('name', f'node-{i}')
                        node_role = 'control-plane' if 'control-plane' in node_name else 'worker'
                        click.echo(f"  • {node_name} ({node_role})")
                
                return True
            else:
                click.echo("❌ Failed to create cluster", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error creating cluster: {e}", err=True)
            return False
    
    # Run async function
    success = asyncio.run(_create_cluster())
    if not success:
        raise click.Abort()


@cluster.command()
@common_options
def delete(config_dir: Optional[click.Path], environment: str, verbose: bool):
    """Delete the Kind cluster."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _delete_cluster():
        try:
            click.echo(f"🗑️  Deleting cluster '{cli_context.config.cluster.name}'...")
            
            manager = ClusterLifecycleManager(cli_context.config)
            
            # Check if cluster exists
            status = await manager.get_status()
            if not status.exists:
                click.echo(f"ℹ️  Cluster '{status.name}' does not exist")
                return True
            
            # Delete cluster
            success = await manager.stop_and_cleanup()
            
            if success:
                click.echo(f"✅ Cluster '{status.name}' deleted successfully!")
                return True
            else:
                click.echo("❌ Failed to delete cluster", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error deleting cluster: {e}", err=True)
            return False
    
    success = asyncio.run(_delete_cluster())
    if not success:
        raise click.Abort()


@cluster.command()
@common_options
def reset(config_dir: Optional[click.Path], environment: str, verbose: bool):
    """Reset the Kind cluster by deleting and recreating it."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _reset_cluster():
        try:
            click.echo(f"🔄 Resetting cluster '{cli_context.config.cluster.name}'...")
            
            manager = ClusterLifecycleManager(cli_context.config)
            
            # Add progress handlers
            def on_deleting(event):
                click.echo("🗑️  Deleting existing cluster...")
            
            def on_creating(event):
                click.echo("📦 Creating new cluster...")
            
            def on_ready(event):
                click.echo("✅ Cluster reset complete!")
            
            manager.add_event_handler('cluster_deleting', on_deleting)
            manager.add_event_handler('cluster_creating', on_creating)
            manager.add_event_handler('cluster_ready', on_ready)
            
            # Reset cluster
            success = await manager.reset()
            
            if success:
                status = await manager.get_status()
                click.echo(f"🎉 Cluster '{status.name}' reset successfully!")
                return True
            else:
                click.echo("❌ Failed to reset cluster", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error resetting cluster: {e}", err=True)
            return False
    
    success = asyncio.run(_reset_cluster())
    if not success:
        raise click.Abort()


@cluster.command()
@common_options
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def status(config_dir: Optional[click.Path], environment: str, verbose: bool, output: str):
    """Show cluster status."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _show_status():
        try:
            manager = ClusterLifecycleManager(cli_context.config)
            status = await manager.get_status()
            
            if output == 'json':
                status_dict = {
                    'name': status.name,
                    'exists': status.exists,
                    'running': status.running,
                    'ready': status.is_ready,
                    'nodes': len(status.nodes),
                    'kubeconfig': status.kubeconfig_path
                }
                click.echo(json.dumps(status_dict, indent=2))
            else:
                # Table format
                click.echo(f"📊 Cluster Status: {status.name}")
                click.echo(f"{'─' * 40}")
                
                if not status.exists:
                    click.echo("❌ Status: Does not exist")
                    click.echo("\n💡 Run 'gke-local cluster create' to create the cluster")
                    return
                
                # Status indicators
                status_icon = "✅" if status.is_ready else "⚠️"
                running_icon = "🟢" if status.running else "🔴"
                
                click.echo(f"{status_icon} Status: {'Ready' if status.is_ready else 'Not Ready'}")
                click.echo(f"{running_icon} Running: {'Yes' if status.running else 'No'}")
                click.echo(f"🖥️  Nodes: {len(status.nodes)}")
                
                if status.kubeconfig_path:
                    click.echo(f"🔧 Kubeconfig: {status.kubeconfig_path}")
                
                if verbose and status.nodes:
                    click.echo(f"\n📋 Node Details:")
                    for i, node in enumerate(status.nodes):
                        node_name = node.get('metadata', {}).get('name', f'node-{i}')
                        node_status = node.get('status', {})
                        conditions = node_status.get('conditions', [])
                        
                        ready_condition = next(
                            (c for c in conditions if c.get('type') == 'Ready'),
                            {'status': 'Unknown'}
                        )
                        
                        ready_status = ready_condition.get('status', 'Unknown')
                        ready_icon = "✅" if ready_status == 'True' else "❌"
                        
                        click.echo(f"  {ready_icon} {node_name}: {ready_status}")
                
                # Show next steps
                if not status.is_ready:
                    click.echo(f"\n💡 Next steps:")
                    click.echo("   • Check cluster logs: kubectl logs -n kube-system")
                    click.echo("   • Reset cluster: gke-local cluster reset")
                
        except Exception as e:
            click.echo(f"❌ Error getting cluster status: {e}", err=True)
            return False
        
        return True
    
    success = asyncio.run(_show_status())
    if not success:
        raise click.Abort()


@cluster.command()
@common_options
def kubeconfig(config_dir: Optional[click.Path], environment: str, verbose: bool):
    """Get the kubeconfig for the cluster."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _get_kubeconfig():
        try:
            manager = KindManager(cli_context.config)
            kubeconfig = await manager.get_kubeconfig()
            
            if kubeconfig:
                click.echo(kubeconfig)
                return True
            else:
                click.echo("❌ Could not get kubeconfig. Cluster may not exist.", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error getting kubeconfig: {e}", err=True)
            return False
    
    success = asyncio.run(_get_kubeconfig())
    if not success:
        raise click.Abort()


@cluster.command()
def templates():
    """List available cluster templates."""
    templates = ClusterTemplates.list_templates()
    
    click.echo("📋 Available Cluster Templates:")
    click.echo("─" * 35)
    
    template_descriptions = {
        'minimal': 'Single-node cluster for basic development',
        'ai': 'Multi-node cluster optimized for AI workloads',
        'staging': 'Multi-node cluster simulating staging environment',
        'autopilot': 'Cluster configured to simulate GKE Autopilot'
    }
    
    for template in templates:
        description = template_descriptions.get(template, 'No description available')
        click.echo(f"• {template:12} - {description}")
    
    click.echo(f"\n💡 Use with: gke-local cluster create --template <name>")


@cluster.command()
@common_options
@click.option('--timeout', '-t', default=300, help='Timeout in seconds')
def wait(config_dir: Optional[click.Path], environment: str, verbose: bool, timeout: int):
    """Wait for cluster to be ready."""
    handle_common_options(config_dir, environment, verbose)
    
    async def _wait_for_ready():
        try:
            click.echo(f"⏳ Waiting for cluster to be ready (timeout: {timeout}s)...")
            
            manager = ClusterLifecycleManager(cli_context.config)
            
            # Add progress handler
            def on_state_change(event):
                new_state = event.data.get('new_state', 'unknown')
                click.echo(f"🔄 Cluster state: {new_state}")
            
            manager.add_event_handler('state_changed', on_state_change)
            
            success = await manager.wait_for_ready(timeout)
            
            if success:
                click.echo("✅ Cluster is ready!")
                return True
            else:
                click.echo("❌ Timeout waiting for cluster to be ready", err=True)
                return False
                
        except Exception as e:
            click.echo(f"❌ Error waiting for cluster: {e}", err=True)
            return False
    
    success = asyncio.run(_wait_for_ready())
    if not success:
        raise click.Abort()