import pulumi
import pulumi_command as command


def start_minikube():
    # Start Minikube with required settings
    minikube_start = command.local.Command(
        "start-minikube",
        create="minikube start --cpus 8 --memory 15g --gpus all --addons=ingress,metrics-servers,yakd --disk-size=100GB",
        delete="minikube delete",
        opts=pulumi.ResourceOptions(delete_before_replace=True),
    )

    pulumi.export("minikube_status", minikube_start.stdout)
    return minikube_start
