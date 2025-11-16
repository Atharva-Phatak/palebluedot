import os
from dotenv import load_dotenv
import typer
from rich.console import Console
from omegaconf import OmegaConf
import forge.pydantic_models as pm
import sys
from zenml.client import Client
from zenml.enums import StackComponentType

app = typer.Typer()
console = Console()


class ZenMLSetup:
    def __init__(self, stack_name: str):
        self.client = Client()
        self.stack_name = stack_name
        self.load_secrets()
        self.config = self.load_stack_config()

    def load_secrets(self):
        # Load secrets
        secret_path: str = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", ".secrets")
        )
        console.print(f"🔐 Loading secrets from: {secret_path}")
        load_dotenv(os.path.join(secret_path, ".env"))

    def load_stack_config(self) -> pm.ZenMLConfig:
        """Load stack component configurations from config folder."""
        config_path: str = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", f"configs/zenml/{self.stack_name}.yaml"
            )
        )

        if not os.path.exists(config_path):
            console.print(
                f"⚠️  Config folder not found at {config_path}, using defaults",
                style="yellow",
            )
            raise FileNotFoundError(f"Config folder not found at {config_path}")

        cfg = OmegaConf.load(config_path)
        data = OmegaConf.to_container(cfg, resolve=True)
        cfg = pm.ZenMLConfig(**data)

        console.print(f"✅ Loaded configuration from: {config_path}", style="green")
        return cfg

    def check_component_exists(self, component_type: str, component_name: str) -> bool:
        """Check if a ZenML component exists."""
        try:
            if component_type == "secret":
                self.client.get_secret(component_name)
            elif component_type == "stack":
                self.client.get_stack(component_name)
            else:
                self.client.get_stack_component(
                    name_id_or_prefix=component_name,
                    component_type=component_type,
                )
            return True
        except KeyError:
            return False

    def register_github_secret(self) -> None:
        """Register GitHub secret if it doesn't exist."""
        console.print("🔐 Checking GitHub secret...")
        if self.check_component_exists("secret", "github_secret"):
            console.print("✅ GitHub secret already exists. Skipping...")
            return

        console.print("🔐 Registering GitHub secret...")
        github_token = self.config.secrets.github_secret.values.pa_token
        if not github_token:
            console.print(
                "❌ Error: GITHUB_TOKEN environment variable is not set",
                style="bold red",
            )
            sys.exit(1)

        self.client.create_secret(
            name="github_secret", values={"pa_token": github_token}
        )

    def register_slack_secret(self) -> None:
        """Register Slack secret if it doesn't exist."""
        console.print("🔐 Checking Slack secret...")
        if self.check_component_exists("secret", "slack_secret"):
            console.print("✅ Slack secret already exists. Skipping...")
            return

        console.print("🔐 Registering Slack secret...")
        slack_token = self.config.secrets.slack_secret.values.pa_token
        if not slack_token:
            console.print(
                "❌ Error: SLACK_TOKEN environment variable is not set",
                style="bold red",
            )
            sys.exit(1)

        self.client.create_secret(name="slack_secret", values={"pa_token": slack_token})

    def register_artifact_store(self) -> None:
        """Register Minio artifact store if it doesn't exist."""
        console.print("🪣 Checking Minio artifact store...")
        config: pm.ArtifactStore = self.config.artifact_store

        if self.check_component_exists(
            StackComponentType.ARTIFACT_STORE.value, config.name
        ):
            console.print(
                f"✅ Artifact store '{config.name}' already exists. Skipping..."
            )
            return

        console.print("🪣 Registering Minio artifact store...")
        self.client.create_stack_component(
            name=config.name,
            flavor=config.flavor,
            component_type=StackComponentType.ARTIFACT_STORE.value,
            configuration=config.configuration.model_dump(),
        )

    def register_orchestrator(self) -> None:
        """Register Kubernetes orchestrator if it doesn't exist."""
        console.print("⚙️ Checking Kubernetes orchestrator...")
        config: pm.Orchestrator = self.config.orchestrator

        if self.check_component_exists(
            StackComponentType.ORCHESTRATOR.value, config.name
        ):
            console.print(
                f"✅ Orchestrator '{config.name}' already exists. Skipping..."
            )
            return

        console.print("⚙️ Registering Kubernetes orchestrator...")
        self.client.create_stack_component(
            name=config.name,
            flavor=config.flavor,
            component_type=StackComponentType.ORCHESTRATOR.value,
            configuration=config.configuration.model_dump(),
        )

    def register_container_registry(self) -> None:
        """Register container registry if it doesn't exist."""
        console.print("📦 Checking container registry...")
        config: pm.ContainerRegistry = self.config.container_registry

        if self.check_component_exists(
            StackComponentType.CONTAINER_REGISTRY.value, config.name
        ):
            console.print(
                f"✅ Container registry '{config.name}' already exists. Skipping..."
            )
            return

        console.print("📦 Registering container registry...")
        self.client.create_stack_component(
            name=config.name,
            flavor=config.flavor,
            component_type=StackComponentType.CONTAINER_REGISTRY.value,
            configuration=config.configuration.model_dump(),
        )

    def register_code_repository(self) -> None:
        """Register code repository if it doesn't exist."""
        console.print("📁 Checking code repository...")
        config: pm.CodeRepository = self.config.code_repository

        if self.check_component_exists("code-repository", config.name):
            console.print(
                f"✅ Code repository '{config.name}' already exists. Skipping..."
            )
            return

        console.print("📁 Registering code repository...")
        self.client.create_stack_component(
            name=config.name,
            flavor=config.flavor,
            component_type="code-repository",
            configuration=config.configuration.model_dump(),
        )

    def register_slack_alerter(self) -> None:
        """Register Slack alerter if it doesn't exist."""
        console.print("🚨 Checking Slack alerter...")
        config: pm.Alerter = self.config.alerter

        if self.check_component_exists(StackComponentType.ALERTER.value, config.name):
            console.print(f"✅ Alerter '{config.name}' already exists. Skipping...")
            return

        console.print("🚨 Registering Slack alerter...")
        slack_channel_id = config.configuration.channel_id
        if not slack_channel_id:
            console.print(
                "❌ Error: SLACK_CHANNEL_ID environment variable is not set",
                style="bold red",
            )
            sys.exit(1)

        self.client.create_stack_component(
            name=config.name,
            flavor=config.flavor,
            component_type=StackComponentType.ALERTER.value,
            configuration=config.configuration.model_dump(),
        )

    def register_stack(self) -> None:
        """Register and set the k8s_stack as active."""
        console.print("🔧 Checking stack configuration...")
        stack_config: pm.Stack = self.config.stack

        if self.check_component_exists("stack", stack_config.name):
            console.print(
                f"✅ Stack '{stack_config.name}' already exists. Setting it as active..."
            )
            stack = self.client.get_stack(stack_config.name)
            self.client.activate_stack(stack.id)
        else:
            console.print(f"🔧 Registering stack '{stack_config.name}'...")

            # Get component IDs
            components = {}

            orchestrator = self.client.get_stack_component(
                name_id_or_prefix=stack_config.components.orchestrator,
                component_type=StackComponentType.ORCHESTRATOR.value,
            )
            components[StackComponentType.ORCHESTRATOR] = orchestrator.id

            artifact_store = self.client.get_stack_component(
                name_id_or_prefix=stack_config.components.artifact_store,
                component_type=StackComponentType.ARTIFACT_STORE.value,
            )
            components[StackComponentType.ARTIFACT_STORE] = artifact_store.id

            container_registry = self.client.get_stack_component(
                name_id_or_prefix=stack_config.components.container_registry,
                component_type=StackComponentType.CONTAINER_REGISTRY.value,
            )
            components[StackComponentType.CONTAINER_REGISTRY] = container_registry.id

            alerter = self.client.get_stack_component(
                name_id_or_prefix=stack_config.components.alerter,
                component_type=StackComponentType.ALERTER.value,
            )
            components[StackComponentType.ALERTER] = alerter.id

            # Create and activate stack
            stack = self.client.create_stack(
                name=stack_config.name, components=components
            )
            self.client.activate_stack(stack.id)

    def display_active_stack(self) -> None:
        """Display the current active stack information."""
        console.print("\n📊 Current active stack:", style="bold green")

        active_stack = self.client.active_stack
        console.print(f"\nStack: [bold cyan]{active_stack.name}[/bold cyan]")

        for component_type, component in active_stack.components.items():
            console.print(
                f"  - {component_type.value}: [yellow]{component.name}[/yellow]"
            )

    def setup(self) -> None:
        """Run the complete setup process."""
        try:
            # Register secrets
            self.register_github_secret()
            self.register_slack_secret()

            # Register stack components
            self.register_artifact_store()
            self.register_orchestrator()
            self.register_container_registry()
            # self.register_code_repository()
            self.register_slack_alerter()

            # Register and activate stack
            self.register_stack()

            console.print(
                "\n🎉 ZenML setup completed successfully!", style="bold green"
            )
            self.display_active_stack()

        except Exception as e:
            console.print(f"\n❌ Error during setup: {e}", style="bold red")
            sys.exit(1)
