"""
QIT CLI - Main entry point.

Command-line interface for running AMQP interoperability tests.
"""

import sys
from pathlib import Path

import click

from qit import __version__


@click.group()
@click.version_option(version=__version__, prog_name="qit")
def cli() -> None:
    """QIT - AMQP Interoperability Test Suite."""
    pass


@cli.command()
@click.option(
    "--build-shims",
    is_flag=True,
    help="Build native shims (C++, Java, etc.)",
)
def setup(build_shims: bool) -> None:
    """Set up QIT environment and dependencies."""
    click.echo("Setting up QIT environment...")

    # Check Python version
    if sys.version_info < (3, 11):
        click.echo("❌ Python 3.11+ required", err=True)
        sys.exit(1)

    click.echo("✓ Python version OK")

    # Check qpid-proton
    try:
        import proton

        click.echo(f"✓ qpid-proton found (version {proton.VERSION})")
    except ImportError:
        click.echo("❌ qpid-proton not found. Install with: pip install python-qpid-proton", err=True)
        sys.exit(1)

    # Check Docker
    import subprocess

    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        click.echo("✓ Docker found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("⚠ Docker not found (required for broker management)", err=True)

    if build_shims:
        click.echo("\nBuilding native shims...")
        click.echo("  [TODO] C++ shim build")
        click.echo("  [TODO] Java shim build")
        click.echo("  [TODO] JavaScript shim build")
        click.echo("  [TODO] .NET shim build")

    click.echo("\n✓ Setup complete!")
    click.echo("\nNext steps:")
    click.echo("  1. Start broker:  docker compose -f docker/compose.yaml up -d")
    click.echo("  2. Run tests:     qit test amqp-types")


@cli.group()
def test() -> None:
    """Run interoperability tests."""
    pass


@test.command(name="amqp-types")
@click.option(
    "--sender",
    multiple=True,
    help="Sender shim(s) to test (default: all)",
)
@click.option(
    "--receiver",
    multiple=True,
    help="Receiver shim(s) to test (default: all)",
)
@click.option(
    "--type",
    "amqp_types",
    multiple=True,
    help="AMQP type(s) to test (default: all)",
)
@click.option(
    "--broker",
    default="amqp://localhost:5672",
    help="Broker URL",
)
@click.option(
    "--mode",
    type=click.Choice(["broker", "direct"]),
    default="broker",
    help="Test mode (broker or direct peer-to-peer)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output",
)
@click.option(
    "--junit-xml",
    type=click.Path(),
    help="Generate JUnit XML report (for CI/CD integration)",
)
@click.option(
    "--extended",
    is_flag=True,
    help="Include extended tier test values for complex types",
)
def test_amqp_types(
    sender: tuple[str, ...],
    receiver: tuple[str, ...],
    amqp_types: tuple[str, ...],
    broker: str,
    mode: str,
    verbose: bool,
    junit_xml: str | None,
    extended: bool,
) -> None:
    """Test AMQP primitive and complex types interoperability."""
    from pathlib import Path

    from qit.core import BrokerConfig, BrokerManager, Orchestrator, Shim, ShimConfig
    from qit.types import AmqpComplexTypes, AmqpPrimitiveTypes

    click.echo("QIT - AMQP Types Test")
    click.echo("=" * 80)

    # Discover available shims
    project_root = Path(__file__).parent.parent.parent.parent
    shim_dir = project_root / "shims"

    available_shims = {}

    # Python shim
    python_shim_path = shim_dir / "python-proton" / "shim.sh"
    if python_shim_path.exists():
        available_shims["python-proton"] = Shim(
            ShimConfig(
                name="python-proton",
                language="python",
                client="Apache Qpid Proton Python",
                executable=python_shim_path,
            )
        )

    # JavaScript/Rhea shim
    js_shim_path = shim_dir / "javascript-rhea" / "shim.sh"
    if js_shim_path.exists():
        available_shims["javascript-rhea"] = Shim(
            ShimConfig(
                name="javascript-rhea",
                language="javascript",
                client="Rhea AMQP Client",
                executable=js_shim_path,
            )
        )

    # C++ Proton shim
    cpp_shim_path = shim_dir / "cpp-proton" / "shim.sh"
    if cpp_shim_path.exists():
        available_shims["cpp-proton"] = Shim(
            ShimConfig(
                name="cpp-proton",
                language="cpp",
                client="Apache Qpid Proton C++",
                executable=cpp_shim_path,
            )
        )

    # .NET Proton shim
    dotnet_shim_path = shim_dir / "dotnet-proton" / "shim.sh"
    if dotnet_shim_path.exists():
        available_shims["dotnet-proton"] = Shim(
            ShimConfig(
                name="dotnet-proton",
                language="csharp",
                client="Apache Qpid Proton .NET",
                executable=dotnet_shim_path,
            )
        )

    # Java ProtonJ2 shim
    java_shim_path = shim_dir / "java-protonj2" / "shim.sh"
    if java_shim_path.exists():
        available_shims["java-protonj2"] = Shim(
            ShimConfig(
                name="java-protonj2",
                language="java",
                client="Apache Qpid ProtonJ2",
                executable=java_shim_path,
            )
        )

    if not available_shims:
        click.echo("❌ No shims found!", err=True)
        click.echo(f"   Expected shims in: {shim_dir}", err=True)
        sys.exit(1)

    click.echo(f"Found {len(available_shims)} shim(s): {', '.join(available_shims.keys())}")

    # Filter shims if specified
    sender_shims = list(sender) if sender else list(available_shims.keys())
    receiver_shims = list(receiver) if receiver else list(available_shims.keys())

    # Get AMQP types to test (primitives + complex)
    all_types = {**AmqpPrimitiveTypes.get_all_types(), **AmqpComplexTypes.get_all_types(include_extended=extended)}
    if amqp_types:
        test_types = {k: all_types[k]["values"] for k in amqp_types if k in all_types}
    else:
        test_types = {k: v["values"] for k, v in all_types.items()}

    click.echo(f"Testing {len(test_types)} type(s)")
    click.echo()

    # Set up broker if needed
    broker_manager = None
    if mode == "broker":
        compose_file = project_root / "docker" / "compose.yaml"
        if not compose_file.exists():
            click.echo(f"❌ Compose file not found: {compose_file}", err=True)
            sys.exit(1)

        broker_config = BrokerConfig(
            name="artemis",
            type="artemis",
            url=broker,
            compose_file=compose_file,
        )
        broker_manager = BrokerManager(broker_config)

        # Check if broker is running (don't auto-start for now)
        click.echo("Note: Ensure broker is running:")
        click.echo(f"  docker compose -f {compose_file} up -d")
        click.echo()

    # Run tests
    orchestrator = Orchestrator(
        shims=available_shims,
        broker=broker_manager,
    )

    results = orchestrator.run_test_matrix(
        amqp_types=test_types,
        sender_shims=sender_shims,
        receiver_shims=receiver_shims,
    )

    # Print report
    click.echo()
    report = orchestrator.generate_report(results)
    click.echo(report)

    # Generate JUnit XML if requested
    if junit_xml:
        orchestrator.generate_junit_xml(results, junit_xml)
        click.echo(f"\n✓ JUnit XML report written to: {junit_xml}")

    # Exit with error if any tests failed
    if any(not r.success for r in results):
        sys.exit(1)


@cli.command()
def broker() -> None:
    """Manage test broker."""
    click.echo("Broker management commands:")
    click.echo("  Start:  docker compose -f docker/compose.yaml up -d")
    click.echo("  Stop:   docker compose -f docker/compose.yaml down")
    click.echo("  Logs:   docker compose -f docker/compose.yaml logs -f")
    click.echo("  Status: docker compose -f docker/compose.yaml ps")


if __name__ == "__main__":
    cli()
