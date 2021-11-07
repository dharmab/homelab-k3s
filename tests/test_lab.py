from typing import Sequence, Tuple

import kubernetes.client  # type: ignore
import kubernetes.client.models  # type: ignore
import kubernetes.config  # type: ignore
import pytest


@pytest.fixture(autouse=True, scope="session")
def load_kube_config() -> None:
    kubernetes.config.load_kube_config()


@pytest.fixture(scope="session", name="core_api")
def setup_core_api() -> kubernetes.client.CoreV1Api:
    return kubernetes.client.CoreV1Api()


@pytest.fixture(scope="session", name="apps_api")
def setup_apps_api() -> kubernetes.client.CoreV1Api:
    return kubernetes.client.AppsV1Api()


@pytest.fixture(name="all_namespaces")
def list_all_namespaces(
    core_api: kubernetes.client.CoreV1Api,
) -> Sequence[kubernetes.client.models.V1Namespace]:
    return core_api.list_namespace().items


@pytest.mark.integration
def test_all_nodes_ready(core_api: kubernetes.client.CoreV1Api) -> None:
    are_all_nodes_ready = True
    for node in core_api.list_node().items:
        for condition in node.status.conditions:
            if condition.type == "Ready" and not condition.status == "True":
                print(f"Node {node.metadata.name} is not ready")
                are_all_nodes_ready = False
    assert are_all_nodes_ready


@pytest.mark.integration
def _is_pod_ready(pod: kubernetes.client.models.V1Pod) -> Tuple[bool, str]:
    """
    Determine if the given Pod is Ready.

    :return: First value is True if the Pod is Ready and false otherwise.
    Second value is the reason for the result.
    """
    if pod.status is None:
        return (
            False,
            f"Pod {pod.metadata.name} in Namespace {pod.metadata.namespace} status is nil",
        )
    if pod.status.conditions is None:
        return (
            False,
            f"Pod {pod.metadata.name} in Namespace {pod.metadata.namespace} status.conditions is nil",
        )
    for condition in pod.status.conditions:
        if all(
            (
                condition.type == "Ready",
                condition.status != "True",
                condition.reason != "PodCompleted",
            )
        ):

            message = f"Pod {pod.metadata.name} in Namespace {pod.metadata.namespace} is not Ready: {pod.status.phase=}"
            if pod.status.message:
                message += f" {pod.status.message}"
            if pod.status.reason:
                message += f" {pod.status.reason}"
            if pod.status.container_statuses:
                for status in (s for s in pod.status.container_statuses if not s.ready):
                    if status.state.waiting:
                        if status.state.waiting.message:
                            message += f" {status.state.waiting.message=}"
                        if status.state.waiting.reason:
                            message += f" {status.state.waiting.reason=}"
                    if status.state.terminated:
                        if status.state.terminated.message:
                            message += f" {status.state.terminated.message=}"
                        if status.state.terminated.reason:
                            message += f" {status.state.terminated.reason=}"
            return False, message
    return (
        True,
        "Pod {pod.metadata.name} in Namespace {pod.metadata.namesapce} is Ready",
    )


@pytest.mark.integration
def test_all_pods_ready(
    core_api: kubernetes.client.CoreV1Api,
    all_namespaces: Sequence[kubernetes.client.models.V1Namespace],
) -> None:
    are_all_pods_ready = True
    for namespace in all_namespaces:
        for pod in core_api.list_namespaced_pod(namespace.metadata.name).items:
            is_ready, message = _is_pod_ready(pod)
            if not is_ready:
                are_all_pods_ready = False
                print(message)
    assert are_all_pods_ready


@pytest.mark.integration
def test_no_pods_in_unused_namespaces(core_api: kubernetes.client.CoreV1Api) -> None:
    for namespace in ("default", "kube-public", "kube-node-lease"):
        assert not core_api.list_namespaced_pod(namespace).items


def _is_deployment_ready(
    deployment: kubernetes.client.models.V1Deployment,
) -> Tuple[bool, str]:
    """
    Determine if the given Deployment is Ready, i.e. at least one replica Pod
    of the Deployment is Ready.

    :return: First value is True if the Deployment is Ready and false
    otherwise. Second value is the reason for the result.
    """
    identity = f"Deployment {deployment.metadata.name} in Namespace {deployment.metadata.namespace}"
    if not hasattr(deployment, "status"):
        return False, f"{identity} status is nil"
    if (
        not hasattr(deployment.status, "conditions")
        or deployment.status.conditions is None
    ):
        return False, f"{identity} status.conditions is nil"

    for condition in deployment.status.conditions:
        if condition.type in ("Ready", "Available") and condition.status != "True":
            message = f"{identity} is not Ready: {condition.type=} {condition.status=}"
            if hasattr(condition, "reason") and condition.reason:
                message += " {condition.reason=}"
            if hasattr(condition, "mssage") and condition.message:
                message += " {condition.message=}"
            return False, message
    return True, f"{identity} is Ready"


@pytest.mark.integration
def test_are_all_deployments_ready(
    apps_api: kubernetes.client.AppsV1Api,
    all_namespaces: Sequence[kubernetes.client.models.V1Namespace],
) -> None:
    are_all_deployments_ready = True
    for namespace in all_namespaces:
        for deployment in apps_api.list_namespaced_deployment(
            namespace.metadata.name
        ).items:
            is_ready, message = _is_deployment_ready(deployment)
            if not is_ready:
                are_all_deployments_ready = False
                print(message)
    assert are_all_deployments_ready


# TODO test_are_all_deployments_ready
# TODO test_are_all_statefulsets_ready
# TODO test_are_all_daemonsets_ready
# TODO test_are_all_jobs_ok
# TODO test_core_dns
# TODO test_prometheus_operator
# TODO test_prometheus
# TODO test_prometheus_adapter
# TODO test_node_exporter
# TODO test_blackbox_exporter
# TODO test_alertmanager
# TODO test_grafana
# TODO test_longhorn
# TODO test_ingress_nginx
# TODO test_arma3
# TODO test_teamspeak


@pytest.mark.integration
def test_persistent_volume_claims_bound(
    core_api: kubernetes.client.CoreV1Api,
    all_namespaces: Sequence[kubernetes.client.models.V1Namespace],
) -> None:
    are_all_claims_bound = True
    for namespace in all_namespaces:
        for claim in core_api.list_namespaced_persistent_volume_claim(
            namespace.metadata.name
        ).items:
            if claim.status.phase != "Bound":
                print(
                    f"Persistent Volume Claim {claim.metadata.name} in Namespace {claim.metadata.namespace} is not bound: {claim.status.phase=}"
                )
                are_all_claims_bound = False
    assert are_all_claims_bound
