"""
GKE Autopilot CLI Framework

This module provides the main CLI interface for GKE Autopilot deployment operations
with comprehensive command structure, progress indicators, and error handling.
"""

import click
import logging
import sys
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import asyncio

from ..config.configuration_manager import ConfigurationManager
from ..models.app_config import AppConfig, ClusterConfig, create_sample_config
from ..deployment.cluster_manager import ClusterManager
from ..deployment.application_deployer import ApplicationDeployer, DeploymentStrategy
from ..core.validation_engine import ValidationEngine


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProgressIndicator:
    """Progress indicator for long-running operations"""
    
    def __init__(self, description: str, total_steps: int = 100):
        self.description = description
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = datetime.now()
    
    def update(self, step: int, message: str = ""):
        """Update progress"""
        self.current_step = step
        percentage = (step / self.total_steps) * 100
        
        # Create progress bar
        bar_length = 40
        filled_length = int(bar_length * step // self.total_steps)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # Calculate elapsed time
        elapsed = datetime.now() - self.start_time
        elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
        
        # Display progress
        click.echo(f'\r{self.description}: |{bar}| {percentage:.1f}% ({step}/{self.total_steps}) - {elapsed_str} - {message}', nl=False)
        
        if step >= self.total_steps:
            click.echo()  # New line when complete
    
    def complete(self, message: str = "Complete"):
        """Mark progress as complete"""
        self.update(self.total_steps, message)


class CLIContext:
    """CLI context for sharing state between commands"""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.cluster_manager = None
        self.app_deployer = None
        self.validation_engine = ValidationEngine()
        self.verbose = False
        self.dry_run = False
        self.output_format = 'text'
        self.config_file = None
    
    def initialize_clients(self, project_id: Optional[str] = None):
        """Initialize GKE clients"""
        if not self.cluster_manager:
            self.cluster_manager = ClusterManager(project_id)
        if not self.app_deployer:
            self.app_deployer = ApplicationDeployer(project_id)
    
    def setup_logging(self, verbose: bool):
        """Setup logging based on verbosity"""
        self.verbose = verbose
        level = logging.DEBUG if verbose else logging.INFO
        logging.getLogger().setLevel(level)
        
        if verbose:
            # Add more detailed formatter for verbose mode
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            )
            for handler in logging.getLogger().handlers:
                handler.setFormatter(formatter)


# Global CLI context
cli_context = CLIContext()


def handle_errors(func):
    """Decorator for handling CLI errors gracefully"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if cli_context.verbose:
                logger.exception(f"Command failed: {e}")
            else:
                logger.error(f"Error: {e}")
            
            # Exit with error code
            sys.exit(1)
    
    return wrapper


def output_result(result: Dict[str, Any], format_type: str = None):
    """Output result in specified format"""
    format_type = format_type or cli_context.output_format
    
    if format_type == 'json':
        click.echo(json.dumps(result, indent=2, default=str))
    elif format_type == 'yaml':
        import yaml
        click.echo(yaml.dump(result, default_flow_style=False))
    else:
        # Text format
        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, (dict, list)):
                    click.echo(f"{key}: {json.dumps(value, default=str)}")
                else:
                    click.echo(f"{key}: {value}")
        else:
            click.echo(str(result))


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--output', '-o', type=click.Choice(['text', 'json', 'yaml']), default='text', help='Output format')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def cli(ctx, verbose, dry_run, output, config):
    """
    GKE Autopilot Deployment Framework CLI
    
    A systematic approach to deploying applications on Google Kubernetes Engine Autopilot
    with zero infrastructure management and maximum developer productivity.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Setup CLI context
    cli_context.setup_logging(verbose)
    cli_context.dry_run = dry_run
    cli_context.output_format = output
    cli_context.config_file = config
    
    # Store in click context
    ctx.obj['cli_context'] = cli_context
    
    if verbose:
        click.echo("GKE Autopilot CLI initialized in verbose mode")


@cli.command()
@click.option('--config', '-c', type=click.Path(), help='Application configuration file')
@click.option('--cluster', type=str, help='Target cluster name')
@click.option('--region', type=str, default='us-central1', help='GCP region')
@click.option('--wait', is_flag=True, help='Wait for deployment to complete')
@click.pass_context
@handle_errors
def deploy(ctx, config, cluster, region, wait):
    """
    Deploy application to GKE Autopilot cluster.
    
    This command deploys your containerized application to a GKE Autopilot cluster
    with automatic scaling, monitoring, and HTTPS ingress configuration.
    """
    click.echo("🚀 Starting GKE Autopilot deployment...")
    
    if cli_context.dry_run:
        click.echo("DRY RUN MODE - No actual deployment will occur")
    
    # Load configuration
    if config:
        config_data = cli_context.config_manager.load_configuration(config)
        app_config = cli_context.config_manager.create_app_config(config_data)
    else:
        # Interactive configuration
        app_config = create_interactive_config()
    
    # Validate GKE Autopilot compatibility
    validation_result = cli_context.config_manager.validate_gke_autopilot_config(app_config.to_dict())
    
    if not validation_result['valid']:
        click.echo("❌ Configuration validation failed:")
        for error in validation_result['errors']:
            click.echo(f"  • {error}")
        return
    
    if validation_result['warnings']:
        click.echo("⚠️  Configuration warnings:")
        for warning in validation_result['warnings']:
            click.echo(f"  • {warning}")
    
    # Show deployment plan
    click.echo(f"\n📋 Deployment Plan:")
    click.echo(f"  Application: {app_config.name}")
    click.echo(f"  Image: {app_config.image}")
    click.echo(f"  Cluster: {cluster or 'auto-generated'}")
    click.echo(f"  Region: {region}")
    click.echo(f"  Resources: {app_config.resource_requests.cpu} CPU, {app_config.resource_requests.memory} Memory")
    click.echo(f"  Scaling: {app_config.scaling_config.min_replicas}-{app_config.scaling_config.max_replicas} replicas")
    
    if app_config.ingress_config.enabled:
        click.echo(f"  Domain: {app_config.ingress_config.domain}")
        click.echo(f"  TLS: {'Enabled' if app_config.ingress_config.tls else 'Disabled'}")
    
    if not cli_context.dry_run:
        if not click.confirm("\nProceed with deployment?"):
            click.echo("Deployment cancelled")
            return
        
        # Execute deployment
        result = asyncio.run(execute_deployment(app_config, cluster, region, wait))
        output_result(result)
    else:
        click.echo("\n✅ Dry run complete - configuration is valid")


@cli.command()
@click.option('--app', '-a', type=str, help='Application name')
@click.option('--cluster', '-c', type=str, help='Cluster name')
@click.option('--watch', '-w', is_flag=True, help='Watch status continuously')
@click.pass_context
@handle_errors
def status(ctx, app, cluster, watch):
    """
    Get deployment status and health information.
    
    Shows the current status of your application deployment including
    pod health, scaling metrics, and ingress configuration.
    """
    if not app and not cluster:
        click.echo("Please specify either --app or --cluster")
        return
    
    if watch:
        click.echo("👀 Watching deployment status (Press Ctrl+C to stop)...")
        try:
            while True:
                result = get_deployment_status(app, cluster)
                click.clear()
                click.echo(f"🔄 Status at {datetime.now().strftime('%H:%M:%S')}")
                output_result(result)
                click.echo("\nPress Ctrl+C to stop watching...")
                import time
                time.sleep(5)
        except KeyboardInterrupt:
            click.echo("\n👋 Stopped watching")
    else:
        result = asyncio.run(get_deployment_status(app, cluster))
        output_result(result)


@cli.command()
@click.option('--app', '-a', type=str, required=True, help='Application name')
@click.option('--replicas', '-r', type=int, help='Number of replicas')
@click.option('--cpu-target', type=int, help='Target CPU utilization percentage')
@click.option('--memory-target', type=int, help='Target memory utilization percentage')
@click.pass_context
@handle_errors
def scale(ctx, app, replicas, cpu_target, memory_target):
    """
    Scale application deployment.
    
    Adjust the number of replicas or autoscaling parameters for your application.
    """
    click.echo(f"⚖️  Scaling application: {app}")
    
    if cli_context.dry_run:
        click.echo("DRY RUN MODE - No actual scaling will occur")
    
    scaling_params = {}
    if replicas:
        scaling_params['replicas'] = replicas
    if cpu_target:
        scaling_params['cpu_target'] = cpu_target
    if memory_target:
        scaling_params['memory_target'] = memory_target
    
    if not scaling_params:
        click.echo("No scaling parameters specified")
        return
    
    click.echo(f"Scaling parameters: {scaling_params}")
    
    if not cli_context.dry_run:
        result = execute_scaling(app, scaling_params)
        output_result(result)
    else:
        click.echo("✅ Dry run complete - scaling parameters are valid")


@cli.command()
@click.option('--app', '-a', type=str, help='Application name to delete')
@click.option('--cluster', '-c', type=str, help='Cluster name to delete')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
@handle_errors
def delete(ctx, app, cluster, force):
    """
    Delete application or cluster.
    
    Removes the specified application deployment or entire cluster.
    Use with caution as this operation cannot be undone.
    """
    if not app and not cluster:
        click.echo("Please specify either --app or --cluster to delete")
        return
    
    if app:
        target = f"application '{app}'"
    else:
        target = f"cluster '{cluster}'"
    
    click.echo(f"🗑️  Deleting {target}")
    
    if not force:
        if not click.confirm(f"Are you sure you want to delete {target}? This cannot be undone."):
            click.echo("Deletion cancelled")
            return
    
    if cli_context.dry_run:
        click.echo("DRY RUN MODE - No actual deletion will occur")
        click.echo(f"Would delete: {target}")
    else:
        result = execute_deletion(app, cluster)
        output_result(result)


@cli.command()
@click.option('--name', '-n', type=str, required=True, help='Cluster name')
@click.option('--region', '-r', type=str, default='us-central1', help='GCP region')
@click.option('--wait', is_flag=True, help='Wait for cluster creation to complete')
@click.pass_context
@handle_errors
def create_cluster(ctx, name, region, wait):
    """
    Create a new GKE Autopilot cluster.
    
    Creates a new GKE Autopilot cluster with optimal configuration
    for running containerized applications with zero infrastructure management.
    """
    click.echo(f"🚀 Creating GKE Autopilot cluster: {name}")
    
    if cli_context.dry_run:
        click.echo("DRY RUN MODE - No actual cluster will be created")
        click.echo(f"Would create cluster: {name} in {region}")
        return
    
    # Initialize clients
    cli_context.initialize_clients()
    
    try:
        from ..models.app_config import ClusterConfig
        cluster_config = ClusterConfig(name=name, region=region)
        
        result = asyncio.run(cli_context.cluster_manager.create_cluster(cluster_config, wait_for_completion=wait))
        
        click.echo(f"✅ Cluster created successfully: {name}")
        output_result(result.to_dict())
        
    except Exception as e:
        click.echo(f"❌ Failed to create cluster: {e}")
        sys.exit(1)


@cli.command()
@click.option('--region', '-r', type=str, default='-', help='GCP region (- for all regions)')
@click.pass_context
@handle_errors
def list_clusters(ctx, region):
    """
    List GKE clusters in the project.
    
    Shows all GKE clusters with their status, location, and configuration details.
    """
    click.echo("📋 Listing GKE clusters...")
    
    # Initialize clients
    cli_context.initialize_clients()
    
    try:
        clusters = asyncio.run(cli_context.cluster_manager.list_clusters(region))
        
        if not clusters:
            click.echo("No clusters found")
            return
        
        if cli_context.output_format == 'text':
            click.echo(f"\nFound {len(clusters)} cluster(s):")
            for cluster in clusters:
                status_icon = "🟢" if cluster.status == "RUNNING" else "🟡" if cluster.status == "PROVISIONING" else "🔴"
                autopilot_icon = "🤖" if cluster.autopilot_enabled else "⚙️"
                click.echo(f"  {status_icon} {autopilot_icon} {cluster.name} ({cluster.location}) - {cluster.status}")
                click.echo(f"    Kubernetes: {cluster.kubernetes_version}, Nodes: {cluster.node_count}")
        else:
            output_result([cluster.to_dict() for cluster in clusters])
            
    except Exception as e:
        click.echo(f"❌ Failed to list clusters: {e}")
        sys.exit(1)


@cli.command()
@click.option('--output-dir', '-o', type=click.Path(), default='config', help='Output directory for sample configs')
@click.pass_context
@handle_errors
def init(ctx, output_dir):
    """
    Initialize GKE Autopilot configuration.
    
    Creates sample configuration files and directory structure
    to help you get started with GKE Autopilot deployments.
    """
    click.echo("🎯 Initializing GKE Autopilot configuration...")
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create configuration manager with output directory
    config_manager = ConfigurationManager(output_path)
    config_manager.create_sample_configs()
    
    # Create additional helpful files
    create_gitignore(output_path)
    create_readme(output_path)
    
    click.echo(f"✅ Configuration initialized in {output_path}")
    click.echo("\nNext steps:")
    click.echo(f"  1. Edit {output_path}/samples/app-config.yaml")
    click.echo(f"  2. Edit {output_path}/samples/cluster-config.yaml")
    click.echo("  3. Run: gke-autopilot deploy --config config/samples/app-config.yaml")


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Configuration file to validate')
@click.pass_context
@handle_errors
def validate(ctx, config):
    """
    Validate configuration file.
    
    Checks your configuration file for syntax errors, GKE Autopilot
    compatibility, and provides optimization recommendations.
    """
    click.echo(f"🔍 Validating configuration: {config}")
    
    try:
        # Load and validate configuration
        config_data = cli_context.config_manager.load_configuration(config)
        app_config = cli_context.config_manager.create_app_config(config_data)
        
        # Comprehensive validation using validation engine
        validation_result = asyncio.run(cli_context.validation_engine.validate_app_config(app_config))
        
        # Convert to old format for compatibility
        validation_dict = {
            'valid': validation_result.valid,
            'errors': [error.message for error in validation_result.get_errors()],
            'warnings': [warning.message for warning in validation_result.get_warnings()],
            'recommendations': [rec.message for rec in validation_result.get_recommendations()]
        }
        
        if validation_dict['valid']:
            click.echo("✅ Configuration is valid")
        else:
            click.echo("❌ Configuration validation failed")
            for error in validation_dict['errors']:
                click.echo(f"  Error: {error}")
        
        if validation_dict['warnings']:
            click.echo("\n⚠️  Warnings:")
            for warning in validation_dict['warnings']:
                click.echo(f"  • {warning}")
        
        if validation_dict['recommendations']:
            click.echo("\n💡 Recommendations:")
            for rec in validation_dict['recommendations']:
                click.echo(f"  • {rec}")
        
        # Output detailed validation result
        if cli_context.output_format != 'text':
            output_result(validation_dict)
        else:
            # Show human-readable summary
            summary = cli_context.validation_engine.generate_validation_summary(validation_result)
            click.echo(f"\n{summary}")
            
    except Exception as e:
        click.echo(f"❌ Validation failed: {e}")
        sys.exit(1)


def create_interactive_config() -> AppConfig:
    """Create application configuration interactively"""
    click.echo("\n📝 Interactive Configuration Setup")
    
    name = click.prompt("Application name", type=str)
    image = click.prompt("Container image", type=str)
    port = click.prompt("Application port", type=int, default=8080)
    
    # Optional configurations
    if click.confirm("Configure custom resources?", default=False):
        cpu = click.prompt("CPU request", type=str, default="250m")
        memory = click.prompt("Memory request", type=str, default="512Mi")
    else:
        cpu, memory = "250m", "512Mi"
    
    if click.confirm("Configure ingress?", default=True):
        domain = click.prompt("Domain name", type=str)
        tls = click.confirm("Enable TLS?", default=True)
    else:
        domain, tls = None, False
    
    # Create configuration
    from ..models.app_config import ResourceRequests, IngressConfig
    
    return AppConfig(
        name=name,
        image=image,
        port=port,
        resource_requests=ResourceRequests(cpu=cpu, memory=memory),
        ingress_config=IngressConfig(enabled=bool(domain), domain=domain, tls=tls)
    )


async def execute_deployment(app_config: AppConfig, cluster: str, region: str, wait: bool) -> Dict[str, Any]:
    """Execute the actual deployment"""
    
    # Initialize clients
    cli_context.initialize_clients()
    
    progress = ProgressIndicator("Deploying application", 6)
    
    try:
        # Check if cluster exists, create if needed
        progress.update(1, "Checking cluster...")
        
        cluster_name = cluster or f"{app_config.name}-cluster"
        
        try:
            cluster_info = await cli_context.cluster_manager.get_cluster_info(cluster_name, region)
            click.echo(f"Using existing cluster: {cluster_name}")
        except:
            # Cluster doesn't exist, create it
            progress.update(2, "Creating cluster...")
            click.echo(f"Creating new cluster: {cluster_name}")
            
            from ..models.app_config import ClusterConfig
            cluster_config = ClusterConfig(name=cluster_name, region=region)
            cluster_info = await cli_context.cluster_manager.create_cluster(cluster_config, wait_for_completion=True)
        
        progress.update(3, "Validating configuration...")
        
        # Validate application configuration
        validation_report = await cli_context.validation_engine.validate_app_config(app_config)
        if not validation_report.valid:
            errors = [error.message for error in validation_report.get_errors()]
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        progress.update(4, "Deploying application...")
        
        # Deploy application
        deployment_result = await cli_context.app_deployer.deploy_application(
            app_config, cluster_name, region, 
            strategy=DeploymentStrategy.ROLLING_UPDATE,
            wait_for_completion=wait
        )
        
        progress.update(5, "Configuring services...")
        
        if not deployment_result.success:
            raise ValueError(f"Deployment failed: {deployment_result.error_message}")
        
        progress.update(6, "Deployment complete!")
        
        return {
            'success': True,
            'application': app_config.name,
            'cluster': cluster_name,
            'region': region,
            'url': deployment_result.application_url,
            'deployment_time': deployment_result.deployment_time.isoformat(),
            'monitoring_dashboard': deployment_result.monitoring_dashboard
        }
        
    except Exception as e:
        progress.complete(f"Failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'application': app_config.name,
            'cluster': cluster or f"{app_config.name}-cluster",
            'region': region
        }


async def get_deployment_status(app: str, cluster: str) -> Dict[str, Any]:
    """Get deployment status"""
    
    # Initialize clients
    cli_context.initialize_clients()
    
    try:
        if app:
            # Get application status
            status = await cli_context.app_deployer.get_deployment_status(app, cluster, "us-central1")
            return status
        elif cluster:
            # Get cluster health
            health = await cli_context.cluster_manager.get_cluster_health(cluster, "us-central1")
            return health.to_dict()
        else:
            return {'error': 'Either app or cluster must be specified'}
            
    except Exception as e:
        return {
            'application': app,
            'cluster': cluster,
            'status': 'Error',
            'error': str(e),
            'last_updated': datetime.now().isoformat()
        }


def execute_scaling(app: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute scaling operation (placeholder for now)"""
    return {
        'application': app,
        'scaling_applied': params,
        'status': 'Scaling in progress',
        'timestamp': datetime.now().isoformat()
    }


def execute_deletion(app: str, cluster: str) -> Dict[str, Any]:
    """Execute deletion operation (placeholder for now)"""
    target = app or cluster
    target_type = 'application' if app else 'cluster'
    
    return {
        'deleted': target,
        'type': target_type,
        'status': 'Deletion complete',
        'timestamp': datetime.now().isoformat()
    }


def create_gitignore(config_dir: Path) -> None:
    """Create .gitignore file for configuration directory"""
    gitignore_content = """# GKE Autopilot Configuration
*.log
.env
secrets/
*.key
*.pem
.gcp-credentials.json
"""
    
    with open(config_dir / ".gitignore", "w") as f:
        f.write(gitignore_content)


def create_readme(config_dir: Path) -> None:
    """Create README file for configuration directory"""
    readme_content = """# GKE Autopilot Configuration

This directory contains configuration files for GKE Autopilot deployments.

## Files

- `samples/app-config.yaml` - Sample application configuration
- `samples/cluster-config.yaml` - Sample cluster configuration
- `templates/` - Configuration templates (if any)

## Usage

1. Copy and modify the sample configurations:
   ```bash
   cp samples/app-config.yaml my-app-config.yaml
   cp samples/cluster-config.yaml my-cluster-config.yaml
   ```

2. Edit the configurations for your application

3. Validate the configuration:
   ```bash
   gke-autopilot validate --config my-app-config.yaml
   ```

4. Deploy your application:
   ```bash
   gke-autopilot deploy --config my-app-config.yaml
   ```

## Environment Variables

You can override configuration values using environment variables:

- `GKE_AUTOPILOT_NAME` - Application name
- `GKE_AUTOPILOT_IMAGE` - Container image
- `GKE_AUTOPILOT_RESOURCES__CPU` - CPU request
- `GKE_AUTOPILOT_RESOURCES__MEMORY` - Memory request

## Documentation

For more information, see the GKE Autopilot documentation.
"""
    
    with open(config_dir / "README.md", "w") as f:
        f.write(readme_content)


if __name__ == '__main__':
    cli()