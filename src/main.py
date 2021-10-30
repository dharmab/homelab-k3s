#!/usr/bin/env python3

import argparse
from typing import List, Tuple
from pathlib import Path
import yaml
import enum
import subprocess


class Command(enum.Enum):
    DEPLOY = enum.auto()


def _parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True, dest="command")

    deploy_parser = subparsers.add_parser("deploy", help="Deploy Kubernetes manifests")
    deploy_parser.add_argument("-m", "--manifest", dest="manifests", action="append", metavar="FILE", help="Kubernetes YAML or JSON manifest file to deploy")

    return parser.parse_args()


def parse_manifests(paths: List[Path]) -> List[dict]:
    """
    Load the manifest content from the given paths.
    """
    manifests: List[dict] = []
    for path in paths:
        with open(path, 'r', encoding='utf-8') as f:
            manifests.extend(yaml.safe_load_all(f))
    return manifests


def kubectl_apply(manifests: List[dict]) -> None:
    if not manifests:
        return
    for manifest in manifests:
        message = "Applying {} {}".format(manifest["kind"], manifest["metadata"]["name"])
        namespace = manifest["metadata"].get("namespace")
        if namespace:
            message += f" in Namespace {namespace}"
        print(message)

    try:
        subprocess.run(["kubectl", "apply", "-f", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, input=yaml.dump_all(manifests).encode("utf-8"), check=True)
    except subprocess.CalledProcessError as e:
        print("\n".join(("kubectl apply failed:", str(e.stdout), str(e.stderr))))
        raise
    print("Applied {} manifests successfuly".format(len(manifests)))


def deploy_manifests(manifests: List[dict]) -> None:

    def filter_manifests(*args) -> List[dict]:
        return [m for m in manifests if m["kind"] in args]

    kubectl_apply(filter_manifests("Namespace"))
    kubectl_apply(filter_manifests("CustomResourceDefinition"))
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
        deploy_manifests(manifests)


if __name__ == "__main__":
    main()
