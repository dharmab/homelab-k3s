#!/usr/bin/env python3

import argparse
from typing import List, Tuple
from pathlib import Path
import yaml
import enum
import subprocess
import kubernetes.client
import kubernetes.config
from time import sleep


class Command(enum.Enum):
    DEPLOY = enum.auto()


def _parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser()
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

    return parser.parse_args()


def parse_manifests(paths: List[Path]) -> List[dict]:
    """
    Load the manifest content from the given paths.
    """
    manifests: List[dict] = []
    for path in paths:
        if path.is_dir():
            manifests.extend(parse_manifests(list(path.iterdir())))
        elif path.is_file():
            print(f"Loading manifest {path}...")
            with open(path, "r", encoding="utf-8") as f:
                documents = yaml.safe_load_all(f)
                for document in documents:
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
        message = "Applying {} {}".format(
            manifest["kind"], manifest["metadata"]["name"]
        )
        namespace = manifest["metadata"].get("namespace")
        if namespace:
            message += f" in Namespace {namespace}"
        message += "..."
        print(message)

    try:
        subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            input=yaml.dump_all(manifests).encode("utf-8"),
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("\n".join(("kubectl apply failed:", str(e.stdout), str(e.stderr))))
        raise
    print("Applied {} manifest(s) successfully".format(len(manifests)))


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


def deploy_manifests(
    manifests: List[dict], *, api_extensions_api: kubernetes.client.ApiextensionsV1Api
) -> None:
    def filter_manifests(*args) -> List[dict]:
        return [m for m in manifests if m["kind"] in args]

    kubectl_apply(filter_manifests("Namespace"))
    crd_manifests = filter_manifests("CustomResourceDefinition")
    kubectl_apply(crd_manifests)
    for crd_manifest in crd_manifests:
        _wait_for_crd(
            crd_manifest["metadata"]["name"], api_extensions_api=api_extensions_api
        )
    print("Confirmed {} CustomResourceDefinitions".format(len(crd_manifests)))
    kubectl_apply(filter_manifests("ClusterRole", "Role", "ServiceAccount"))
    kubectl_apply(filter_manifests("ClusterRoleBinding" "RoleBinding"))
    kubectl_apply(filter_manifests("ConfigMap" "Secret"))
    kubectl_apply(manifests)


def main() -> None:
    """Entrypoint function"""
    args = _parse_args()
    if args.command == "deploy":
        manifest_paths = [Path(m) for m in args.manifests]
        manifests = parse_manifests(manifest_paths)

        kubernetes.config.load_kube_config()
        api_extensions_api = kubernetes.client.ApiextensionsV1Api()

        deploy_manifests(manifests, api_extensions_api=api_extensions_api)


if __name__ == "__main__":
    main()
