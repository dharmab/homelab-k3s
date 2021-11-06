from typing import Tuple

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
def test_all_pods_ready(core_api: kubernetes.client.CoreV1Api) -> None:
    are_all_pods_ready = True
    for namespace in core_api.list_namespace().items:
        for pod in core_api.list_namespaced_pod(namespace.metadata.name).items:
            _is_ready, message = _is_pod_ready(pod)
            if not _is_ready:
                are_all_pods_ready = False
                print(message)
    assert are_all_pods_ready


def test_no_pods_in_unused_namespaces(core_api: kubernetes.client.CoreV1Api) -> None:
    for namespace in ("default", "kube-public", "kube-node-lease"):
        assert not core_api.list_namespaced_pod(namespace).items


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
def test_persistent_volume_claims_bound(core_api: kubernetes.client.CoreV1Api) -> None:
    are_all_claims_bound = True
    for namespace in core_api.list_namespace().items:
        for claim in core_api.list_namespaced_persistent_volume_claim(
            namespace.metadata.name
        ).items:
            if claim.status.phase != "Bound":
                print(
                    f"Persistent Volume Claim {claim.metadata.name} in Namespace {claim.metadata.namespace} is not bound: {claim.status.phase=}"
                )
                are_all_claims_bound = False
    assert are_all_claims_bound
