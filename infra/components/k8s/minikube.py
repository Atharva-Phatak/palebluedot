import pulumi
import pulumi_command as command
from helper.constant import Constants


def start_minikube():
    # Start Minikube with required settings
    minikube_start = command.local.Command(
        "start-minikube",
        create=f"minikube start --cpus {Constants.minikube_cpus} --memory {Constants.minikube_memory} --gpus {Constants.minikube_gpu} --addons={Constants.minikube_addons} --disk-size={Constants.minikube_disk_size}",
        delete="minikube delete",
        opts=pulumi.ResourceOptions(delete_before_replace=True),
    )

    pulumi.export("minikube_status", minikube_start.stdout)
    return minikube_start
