import pulumi
import pulumi_command as command


def start_minikube(n_cpus:str,
                memory:str,
                addons:str,
                gpus:str,
                disk_size:str) -> command.local.Command:
    # Start Minikube with required settings
    minikube_start = command.local.Command(
        "start-minikube",
        create=f"minikube start --cpus {n_cpus} --memory {memory} --gpus {gpus} --addons={addons} --disk-size={disk_size}",
        delete="minikube delete",
        opts=pulumi.ResourceOptions(delete_before_replace=True),
    )

    pulumi.export("minikube_status", minikube_start.stdout)
    return minikube_start
