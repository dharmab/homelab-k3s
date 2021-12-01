#!/usr/bin/env python3

import argparse
import enum
import json
import os
import subprocess
from pathlib import Path
from time import sleep
from typing import List, Sequence

import jinja2
import kubernetes.client  # type: ignore
import kubernetes.config  # type: ignore
import tenacity
import yaml

from config import Arma3Mod, LabConfig


def _parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        metavar="FILE",
        required=True,
        default=os.environ.get("LABCONFIG"),
        help="Lab config file",
    )
    parser.add_argument(
        "-k",
        "--kubeconfig",
        action="store",
        metavar="FILE",
        required=True,
        default=os.environ.get("KUBECONFIG"),
        help="Kubernetes config file",
    )

    subparsers = parser.add_subparsers(required=True, dest="command")

    deploy_parser = subparsers.add_parser("deploy", help="Deploy Kubernetes manifests")
    deploy_parser.add_argument(
        "-m",
        "--manifest",
        dest="manifests",
        action="append",
        metavar="FILE",
        required=True,
        help="Kubernetes YAML or JSON manifest file to deploy",
    )

    subparsers.add_parser("update-arma3-mods", help="Install or update Arma 3 mods")

    return parser.parse_args()


def parse_manifests(paths: Sequence[Path], *, config: LabConfig) -> List[dict]:
    """
    Load the manifest content from the given paths.
    """
    manifests: List[dict] = []
    for path in paths:
        if path.is_dir():
            manifests.extend(parse_manifests(list(path.iterdir()), config=config))
        elif path.is_file():
            print(f"Loading manifest {path}...")
            with open(path, "r", encoding="utf-8") as f:
                raw_document = f.read()
            try:
                template = jinja2.Template(raw_document).render(
                    json.loads(config.json_with_plaintext_secrets())
                )
            except jinja2.exceptions.TemplateSyntaxError:
                template = raw_document
            documents = yaml.safe_load_all(template)
            for document in documents:
                if document is None:
                    continue
                if document["kind"].endswith("List"):
                    # Easier to deal with unwrapped lists
                    manifests.extend(document["items"])
                else:
                    manifests.append(document)
    return manifests


def kubectl_apply(manifests: List[dict]) -> None:
    if not manifests:
        return
    for manifest in manifests:
        message = f'Applying {manifest["kind"]} {manifest["metadata"]["name"]}'
        namespace = manifest["metadata"].get("namespace")
        if namespace:
            message += f" in Namespace {namespace}"
        message += "..."
        print(message)

    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_delay(300),
        wait=tenacity.wait_exponential(multiplier=2, max=10),
    ):
        with attempt:
            try:
                subprocess.run(
                    ["kubectl", "apply", "-f", "-"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    input=yaml.dump_all(manifests).encode("utf-8"),
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                print(
                    "\n".join(
                        (
                            "kubectl apply failed:",
                            e.stdout.decode("utf-8"),
                            e.stderr.decode("utf-8"),
                        )
                    )
                )
                raise
    print(f"Applied {len(manifests)} manifest(s) successfully")


def _wait_for_crd(
    crd_name: str, *, api_extensions_api: kubernetes.client.ApiextensionsV1Api
) -> None:
    print(f"Waiting for CustomResourceDefinition {crd_name}...")
    while True:
        try:
            api_extensions_api.read_custom_resource_definition(crd_name)
            return
        except ValueError:
            # https://github.com/kubernetes-client/gen/issues/52
            pass
        except kubernetes.client.rest.ApiException as e:
            if e.status == 404:
                pass
            else:
                raise
        sleep(1)


def customize_manifests(manifests: List[dict], *, config: LabConfig) -> List[dict]:
    for manifest in manifests:
        identity = f"{manifest['kind']} {manifest['metadata']['name']}"
        if manifest["metadata"].get("namespace"):
            identity += f" in Namespace {manifest['metadata']['namespace']}"

        if manifest["kind"] in ("Deployment", "StatefulSet", "Job", "CronJob"):
            pod_template = manifest["spec"]["template"]

            for container in pod_template["spec"]["containers"]:
                if container.get("imagePullPolicy") != "IfNotPresent":
                    print(
                        f"Customizing {identity}: Setting image pull policy to IfNotPresent to conserve network bandwidth"
                    )
                    container["imagePullPolicy"] = "IfNotPresent"
        if manifest["kind"] == "Ingress":
            # https://cert-manager.io/docs/usage/ingress/
            print(
                f"Customizing {identity}: Configuring TLS using ClusterIssuer {config.cert_manager.issuer.value}"
            )
            manifest["spec"]["ingressClassName"] = "nginx"
            if "annotations" not in manifest["metadata"]:
                manifest["metadata"]["annotations"] = {}
            manifest["metadata"]["annotations"].update(
                {
                    "cert-manager.io/cluster-issuer": config.cert_manager.issuer.value,
                }
            )
            manifest["spec"]["tls"] = [
                {
                    "hosts": [config.nginx.base_url.host],
                    "secretName": f"{manifest['metadata']['name']}-ingress-tls",
                }
            ]
            for rule in manifest["spec"].get("rules", []):
                rule["host"] = config.nginx.base_url.host
        if config.arma3.mods and manifest["metadata"].get("namespace") == "arma3" and manifest["kind"] == "StatefulSet" and manifest["metadata"]["name"] in ("arma3", "arma3-headless-client"):
            print(f"Customizing {identity}: Adding Arma 3 mods to arma3server arguments")
            for container in manifest["spec"]["template"]["spec"]["containers"]:
                if container["name"] == "arma3":
                    container["args"].append("-mod=" + ";".join(f"@{mod.name}" for mod in config.arma3.mods))

    return manifests


def deploy_manifests(
    manifests: List[dict], *, api_extensions_api: kubernetes.client.ApiextensionsV1Api
) -> None:
    def filter_manifests(*args: str) -> List[dict]:
        return [m for m in manifests if m["kind"] in args]

    kubectl_apply(filter_manifests("Namespace"))

    crd_manifests = filter_manifests("CustomResourceDefinition")
    kubectl_apply(crd_manifests)
    for crd_manifest in crd_manifests:
        _wait_for_crd(
            crd_manifest["metadata"]["name"], api_extensions_api=api_extensions_api
        )
    print(f"Verified {len(crd_manifests)} CustomResourceDefinitions")

    kubectl_apply(filter_manifests("ClusterRole", "Role", "ServiceAccount"))
    kubectl_apply(filter_manifests("ClusterRoleBinding", "RoleBinding"))
    kubectl_apply(filter_manifests("ConfigMap", "Secret", "Service"))
    kubectl_apply(manifests)


@tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(32))  # retry works around segfaults
def update_arma3_mods(
    *, mods: List[Arma3Mod], core_api: kubernetes.client.CoreV1Api
) -> None:
    for component in ("server", "headless-client"):
        print(f"Downloading mods for Arma 3 component: {component}")
        pods = core_api.list_namespaced_pod(
            namespace="arma3",
            label_selector=f"app.kubernetes.io/name=arma3,app.kubernetes.io/component={component}",
        )
        for pod in pods.items:
            for mod in mods:
                print(
                    f"Downloading {mod.name} ({mod.workshop_id}) in volume for Pod {pod.metadata.name}..."
                )
                try:
                    response = kubernetes.stream.stream(
                        core_api.connect_get_namespaced_pod_exec,
                        name=pod.metadata.name,
                        namespace=pod.metadata.namespace,
                        container="steamcmd",
                        command=[
                            "bash",
                            "-c",
                            f"steamcmd +force_install_dir /opt/arma3 +login $STEAM_USERNAME $STEAM_PASSWORD +workshop_download_item $ARMA3_APPID {mod.workshop_id} +quit",
                        ],
                        stdin=False,
                        stdout=True,
                        stderr=True,
                        tty=True,
                    )
                    if response:
                        print(response)

                    print(f"Linking {mod.name} in Pod {pod.metadata.name}...")
                    response = kubernetes.stream.stream(
                        core_api.connect_get_namespaced_pod_exec,
                        name=pod.metadata.name,
                        namespace=pod.metadata.namespace,
                        container="steamcmd",
                        command=[
                            "bash",
                            "-c",
                            f"ln -sf /opt/arma3/steamapps/workshop/content/$ARMA3_APPID/{mod.workshop_id} /opt/arma3/@{mod.name}",
                        ],
                        stdin=False,
                        stdout=True,
                        stderr=True,
                        tty=False,
                    )
                    if response:
                        print(response)
                except kubernetes.client.rest.ApiException as e:
                    print(f"error: {e}")
                    raise e
    print("Updated Arma 3 mods. Run `kubectl -n arma3 delete pod -l app.kubernetes.io/name=arma3` to reload mods.")


def main() -> None:
    """Entrypoint function"""
    args = _parse_args()

    assert args.kubeconfig
    kubernetes.config.load_kube_config(config_file=args.kubeconfig)
    assert args.config
    config: LabConfig = LabConfig.parse_file(Path(args.config))

    if args.command == "deploy":
        deploy_manifests(
            customize_manifests(
                manifests=parse_manifests(
                    [Path(m) for m in args.manifests], config=config
                ),
                config=config,
            ),
            api_extensions_api=kubernetes.client.ApiextensionsV1Api(),
        )
    elif args.command == "update-arma3-mods":
        update_arma3_mods(
            mods=config.arma3.mods, core_api=kubernetes.client.CoreV1Api()
        )


if __name__ == "__main__":
    main()
