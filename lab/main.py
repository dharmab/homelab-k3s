#!/usr/bin/env python3

import argparse
import json
import logging
import os
import subprocess
from pathlib import Path
from time import sleep
from typing import List, Sequence
import time

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


def parse_manifests(
    paths: Sequence[Path], *, config: LabConfig, logger: logging.Logger
) -> List[dict]:
    """
    Load the manifest content from the given paths.
    """
    manifests: List[dict] = []
    for path in paths:
        if path.is_dir():
            manifests.extend(
                parse_manifests(list(path.iterdir()), config=config, logger=logger)
            )
        elif path.is_file():
            logger.info(f"Loading manifest {path}...")
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


def kubectl_apply(manifests: List[dict], *, logger: logging.Logger) -> None:
    if not manifests:
        return
    for manifest in manifests:
        message = f'Applying {manifest["kind"]} {manifest["metadata"]["name"]}'
        namespace = manifest["metadata"].get("namespace")
        if namespace:
            message += f" in Namespace {namespace}"
        message += "..."
        logger.info(message)

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
                logger.error(
                    "\n".join(
                        (
                            "kubectl apply failed:",
                            e.stdout.decode("utf-8"),
                            e.stderr.decode("utf-8"),
                        )
                    )
                )
                raise
    logger.info(f"Applied {len(manifests)} manifest(s) successfully")


def kubectl_exec(
    *,
    core_api: kubernetes.client.CoreV1Api,
    pod: kubernetes.client.models.V1Pod,
    container_name: str,
    command: List[str],
    logger: logging.Logger,
) -> str:
    logger.debug(
        f"Running command `{' '.join(command)}` in Pod {pod.metadata.name} in Namespace {pod.metadata.namespace}"
    )
    client = kubernetes.stream.stream(
        core_api.connect_get_namespaced_pod_exec,
        name=pod.metadata.name,
        namespace=pod.metadata.namespace,
        container=container_name,
        command=command,
        stdin=False,
        stdout=True,
        stderr=True,
        tty=False,
        _preload_content=False,
    )
    client.run_forever()
    output = client.read_all()
    if output:
        logger.debug(f"Output:\n{output}")

    error = yaml.safe_load(
        client.read_channel(kubernetes.stream.ws_client.ERROR_CHANNEL)
    )
    # Note sure if this works or if it broke at some point
    if error and error.get("status") != "Success":
        logger.error(f"Command `{' '.join(command)}` failed with output:\n{output}")
        raise RuntimeError(output)

    return output


def _wait_for_crd(
    crd_name: str,
    *,
    api_extensions_api: kubernetes.client.ApiextensionsV1Api,
    logger: logging.Logger,
) -> None:
    logger.info(f"Waiting for CustomResourceDefinition {crd_name}...")
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


def customize_manifests(
    manifests: List[dict], *, config: LabConfig, logger: logging.Logger
) -> List[dict]:
    for manifest in manifests:
        identity = f"{manifest['kind']} {manifest['metadata']['name']}"
        if manifest["metadata"].get("namespace"):
            identity += f" in Namespace {manifest['metadata']['namespace']}"

        if manifest["kind"] in ("Deployment", "StatefulSet", "Job", "CronJob"):
            pod_template = manifest["spec"]["template"]

            for container in pod_template["spec"]["containers"]:
                if container.get("imagePullPolicy") != "IfNotPresent":
                    logger.info(
                        f"Customizing {identity}: Setting image pull policy to IfNotPresent to conserve network bandwidth"
                    )
                    container["imagePullPolicy"] = "IfNotPresent"
        if manifest["kind"] == "Ingress":
            # https://cert-manager.io/docs/usage/ingress/
            logger.info(
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
        if (
            config.arma3.mods
            and manifest["metadata"].get("namespace") == "arma3"
            and manifest["kind"] == "StatefulSet"
            and manifest["metadata"]["name"] in ("arma3", "arma3-headless-client")
        ):
            logger.info(
                f"Customizing {identity}: Adding Arma 3 mods to arma3server arguments"
            )
            for container in manifest["spec"]["template"]["spec"]["containers"]:
                if container["name"] == "arma3":
                    container["args"].append(
                        "-mod=" + ";".join(f"@{mod.name}" for mod in config.arma3.mods)
                    )

    return manifests


def deploy_manifests(
    manifests: List[dict],
    *,
    api_extensions_api: kubernetes.client.ApiextensionsV1Api,
    logger: logging.Logger,
) -> None:
    def filter_manifests(*args: str) -> List[dict]:
        return [m for m in manifests if m["kind"] in args]

    kubectl_apply(filter_manifests("Namespace"), logger=logger)

    crd_manifests = filter_manifests("CustomResourceDefinition")
    kubectl_apply(crd_manifests, logger=logger)
    for crd_manifest in crd_manifests:
        _wait_for_crd(
            crd_manifest["metadata"]["name"],
            api_extensions_api=api_extensions_api,
            logger=logger,
        )
    logger.info(f"Verified {len(crd_manifests)} CustomResourceDefinitions")

    kubectl_apply(
        filter_manifests("ClusterRole", "Role", "ServiceAccount"), logger=logger
    )
    kubectl_apply(filter_manifests("ClusterRoleBinding", "RoleBinding"), logger=logger)
    kubectl_apply(filter_manifests("ConfigMap", "Secret", "Service"), logger=logger)
    kubectl_apply(manifests, logger=logger)


@tenacity.retry(
    wait=tenacity.wait_fixed(1),
    stop=tenacity.stop_after_attempt(128),
)  # retry works around steamcmd segfaults and timeouts when installing large mods >_<
def _update_arma3_mod(
    *,
    pod: kubernetes.client.models.V1Pod,
    mod: Arma3Mod,
    core_api: kubernetes.client.CoreV1Api,
    logger: logging.Logger,
) -> None:
    logger.info(
        f"Updating {mod.name} ({mod.workshop_id}) in volume for Pod {pod.metadata.name}..."
    )
    output = kubectl_exec(
        core_api=core_api,
        pod=pod,
        container_name="steamcmd",
        command=[
            "bash",
            "-c",
            f"steamcmd +force_install_dir /opt/arma3 +login $STEAM_USERNAME $STEAM_PASSWORD +workshop_download_item $ARMA3_APPID {mod.workshop_id} +quit",
        ],
        logger=logger,
    )

    if "FAILED (Rate Limit Exceeded)" in output:
        logger.warning("Rate limited by Steam servers. Backing off...")
        time.sleep(60 * 5)
        raise RuntimeError("Rate limited by Steam servers")
    if "Success. Downloaded item" not in output:
        logger.error(f"Steam failed to download item {mod.workshop_id}:\n{output}")
        raise RuntimeError(
            f"Steam failed to download item {mod.workshop_id}:\n{output}"
        )

    logger.info(
        f"{mod.name} ({mod.workshop_id}) in volume for Pod {pod.metadata.name} is up to date"
    )


def update_arma3_mods(
    *,
    mods: List[Arma3Mod],
    core_api: kubernetes.client.CoreV1Api,
    logger: logging.Logger,
) -> None:
    for component in ("server", "headless-client"):
        logger.info(f"Downloading mods for Arma 3 component: {component}")
        content_directory = Path("/opt/arma3/steamapps/workshop/content/")
        pods = core_api.list_namespaced_pod(
            namespace="arma3",
            label_selector=f"app.kubernetes.io/name=arma3,app.kubernetes.io/component={component}",
        )
        for pod in pods.items:
            for mod in mods:
                _update_arma3_mod(pod=pod, mod=mod, core_api=core_api, logger=logger)

                logger.info(f"Linking {mod.name} in volume for Pod {pod.metadata.name}...")
                kubectl_exec(
                    core_api=core_api,
                    pod=pod,
                    container_name="steamcmd",
                    command=[
                        "bash",
                        "-c",
                        # Note we're linking to a "lower" directory - see below for why
                        " && ".join([
                            f"rm -f /opt/arma3/@{mod.name}",
                            f"ln -sf {content_directory}/lower/{mod.workshop_id} /opt/arma3/@{mod.name}",
                        ])
                    ],
                    logger=logger,
                )

            # SORCERY LIES WITHIN
            #
            # While the Arma 3 game itself will happily run on a case-sensitive
            # filesystem, many popular mods are coded by Windows devs and are
            # only tested on a case-insensitive filesystem. If you try to run
            # these mods out of the box, the server will fail to load any file
            # with an uppercase character in the path, causing all sorts of
            # crazy bugs like objects not appearing in game. CUP even includes
            # an apologetic note with a suggestion to recursively rename all
            # its files to lowercase on Linux. However, this would cause Steam
            # to needlessly redownload the renamed files on each invocation.
            #
            # Instead, we use cp to create a parallel directory tree where all
            # non-directory files are symbolic links to the original, then use
            # find + (perl) rename to lowercase all the filenames in the
            # parallel tree. We'll point Arma at the lowercase version and
            # Steam at the original mixed-case.
            logger.info(
                f"Rebuilding lowercase symbolic link tree in volume for Pod {pod.metadata.name}..."
            )
            kubectl_exec(
                core_api=core_api,
                pod=pod,
                container_name="steamcmd",
                command=[
                    "bash",
                    "-c",
                    " && ".join(
                        [
                            "apt-get -y update",
                            "apt-get -y install rename",
                            f"rm -rf {content_directory}/lower",
                            f"cp -asr {content_directory}/$ARMA3_APPID {content_directory}/lower",
                            # Note the use of -depth to work from the bottom up
                            # so we rename the contents of a directory before
                            # the directory. Otherwise we would change the
                            # paths of files we haven't yet processed.
                            f"find {content_directory}/lower -depth -execdir rename 'y/A-Z/a-z/' '{{}}' ';'",
                        ]
                    ),
                ],
                logger=logger,
            )

    logger.info(
        "Updated Arma 3 mods. Run `kubectl -n arma3 delete pod -l app.kubernetes.io/name=arma3` to reload mods."
    )


def main() -> None:
    """Entrypoint function"""
    args = _parse_args()

    assert args.kubeconfig
    kubernetes.config.load_kube_config(config_file=args.kubeconfig)
    assert args.config
    config: LabConfig = LabConfig.parse_file(Path(args.config))

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    logger = logging.getLogger(__name__)

    if args.command == "deploy":
        deploy_manifests(
            customize_manifests(
                manifests=parse_manifests(
                    [Path(m) for m in args.manifests], config=config, logger=logger
                ),
                config=config,
                logger=logger,
            ),
            api_extensions_api=kubernetes.client.ApiextensionsV1Api(),
            logger=logger,
        )
    elif args.command == "update-arma3-mods":
        update_arma3_mods(
            mods=config.arma3.mods,
            core_api=kubernetes.client.CoreV1Api(),
            logger=logger,
        )


if __name__ == "__main__":
    main()
