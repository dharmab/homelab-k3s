from typing import Optional, Sequence, Tuple

import kubernetes.client  # type: ignore
import kubernetes.config  # type: ignore
import pytest
from kubernetes.client import AppsV1Api, CoreV1Api
from kubernetes.client.models import (  # type: ignore
    V1DaemonSet,
    V1Deployment,
    V1Namespace,
    V1Pod,
    V1StatefulSet,
)


@pytest.fixture(autouse=True, scope="session")
def load_kube_config() -> None:
    kubernetes.config.load_kube_config()


@pytest.fixture(scope="session", name="core_api")
def setup_core_api() -> CoreV1Api:
    return CoreV1Api()


@pytest.fixture(scope="session", name="apps_api")
def setup_apps_api() -> CoreV1Api:
    return AppsV1Api()


@pytest.fixture(name="all_namespaces")
def list_all_namespaces(
    core_api: CoreV1Api,
) -> Sequence[V1Namespace]:
    return core_api.list_namespace().items


@pytest.mark.integration
def test_all_nodes_ready(core_api: CoreV1Api) -> None:
    are_all_nodes_ready = True
    for node in core_api.list_node().items:
        for condition in node.status.conditions:
            if condition.type == "Ready" and not condition.status == "True":
                print(f"Node {node.metadata.name} is not ready")
                are_all_nodes_ready = False
    assert are_all_nodes_ready


@pytest.mark.integration
def _is_pod_ready(pod: V1Pod) -> Tuple[bool, str]:
    # pylint: disable=too-many-branches,too-many-nested-blocks
    # Pods are complicated LOL!
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
    core_api: CoreV1Api,
    all_namespaces: Sequence[V1Namespace],
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
def test_no_pods_in_unused_namespaces(core_api: CoreV1Api) -> None:
    for namespace in ("default", "kube-public", "kube-node-lease"):
        assert not core_api.list_namespaced_pod(namespace).items


def _get_deployment(
    *, namespace: str, name: str, apps_api: AppsV1Api
) -> Optional[V1Deployment]:
    try:
        return apps_api.read_namespaced_deployment(name, namespace)
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            return None
        raise


def _is_deployment_ready(
    deployment: V1Deployment,
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
                message += f" {condition.reason=}"
            if hasattr(condition, "mssage") and condition.message:
                message += f" {condition.message=}"
            return False, message
    return True, f"{identity} is Ready"


@pytest.mark.integration
def test_are_all_deployments_ready(
    apps_api: AppsV1Api,
    all_namespaces: Sequence[V1Namespace],
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


def _get_stateful_set(
    *, namespace: str, name: str, apps_api: AppsV1Api
) -> Optional[V1StatefulSet]:
    try:
        return apps_api.read_namespaced_stateful_set(name, namespace)
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            return None
        raise


def _is_stateful_set_ready(stateful_set: V1StatefulSet) -> Tuple[bool, str]:
    """
    Determine if the given StatefulSet is Ready, i.e. at least one replica Pod
    of the StatefulSet is Ready.

    :return: First value is True if the StatefulSet is Ready and false
    otherwise. Second value is the reason for the result.
    """
    identity = f"StatefulSet {stateful_set.metadata.name} in Namespace {stateful_set.metadata.namespace}"
    if not hasattr(stateful_set, "status"):
        return False, f"{identity} status is nil"
    if (
        not hasattr(stateful_set.status, "ready_replicas")
        or stateful_set.status.ready_replicas is None
    ):
        return False, f"{identity} status.ready_replicas is nil"

    if stateful_set.status.ready_replicas == 0:
        return False, f"{identity} is not Ready: {stateful_set.status.ready_replicas=}"

    return True, f"{identity} is Ready"


@pytest.mark.integration
def test_are_all_stateful_sets_ready(
    apps_api: AppsV1Api, all_namespaces: Sequence[V1Namespace]
) -> None:
    are_all_stateful_sets_ready = True
    for namespace in all_namespaces:
        for stateful_set in apps_api.list_namespaced_stateful_set(
            namespace.metadata.name
        ).items:
            is_ready, message = _is_stateful_set_ready(stateful_set)
            if not is_ready:
                are_all_stateful_sets_ready = False
                print(message)
    assert are_all_stateful_sets_ready


def _get_daemon_set(
    *, namespace: str, name: str, apps_api: AppsV1Api
) -> Optional[V1DaemonSet]:
    try:
        return apps_api.read_namespaced_daemon_set(name, namespace)
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            return None
        raise


def _is_daemon_set_ready(
    daemon_set: V1DaemonSet,
    *,
    minimum_ratio_scheduled: float = 1.0,
    minimum_ratio_ready: float = 1.0,
) -> Tuple[bool, str]:
    """
    Determine if the given DaemonSet is scheduled, up to date and ready.

    :param: minimum_ratio_ready: Percentage of DaemonSet Pods which must be
    scheduled (in range 0.0-1.0)
    :param: minimum_ratio_ready: Percentage of DaemonSet Pods which must be
    ready (in range 0.0-1.0)
    :return: First value is True if the given percentage of DaemonSet Pods are
    Ready and false otherwise. Second value is the reason for the result.
    """
    identity = f"DaemonSet {daemon_set.metadata.name} in Namespace {daemon_set.metadata.namespace}"
    if not hasattr(daemon_set, "status"):
        return False, f"{identity} status is nil"

    current_number_scheduled = daemon_set.status.current_number_scheduled or 0
    if (
        minimum_ratio_scheduled > 0
        and current_number_scheduled / daemon_set.status.desired_number_scheduled
        < minimum_ratio_scheduled
    ):
        return (
            False,
            f"{identity} is not Ready: daemon_set.status.{current_number_scheduled=} {daemon_set.status.desired_number_scheduled=}",
        )

    number_ready = daemon_set.status.number_ready or 0
    if (
        minimum_ratio_ready > 0
        and number_ready / daemon_set.status.desired_number_scheduled
        < minimum_ratio_ready
    ):
        return (
            False,
            f"{identity} is not Ready: daemon_set.status.{number_ready=} {daemon_set.status.desired_number_scheduled=}",
        )

    return True, f"{identity} is Ready"


@pytest.mark.integration
def test_are_all_daemon_sets_ready(
    apps_api: AppsV1Api, all_namespaces: Sequence[V1Namespace]
) -> None:
    are_all_daemon_sets_ready = True
    for namespace in all_namespaces:
        for daemon_set in apps_api.list_namespaced_daemon_set(
            namespace.metadata.name
        ).items:
            is_ready, message = _is_daemon_set_ready(daemon_set)
            if not is_ready:
                are_all_daemon_sets_ready = False
                print(message)
    assert are_all_daemon_sets_ready


@pytest.mark.integration
def test_core_dns(apps_api: AppsV1Api) -> None:
    assert _get_deployment(namespace="kube-system", name="coredns", apps_api=apps_api)


@pytest.mark.integration
def test_metrics_server(apps_api: AppsV1Api) -> None:
    assert _get_deployment(
        namespace="kube-system", name="metrics-server", apps_api=apps_api
    )


@pytest.mark.integration
def test_local_path_provisioner(apps_api: AppsV1Api) -> None:
    assert _get_deployment(
        namespace="kube-system", name="local-path-provisioner", apps_api=apps_api
    )


@pytest.mark.integration
def test_prometheus_operator(apps_api: AppsV1Api) -> None:
    for deployment_name in (
        "prometheus-operator",
        "prometheus-adapter",
        "kube-state-metrics",
        "blackbox-exporter",
        "grafana",
    ):
        assert _get_deployment(
            namespace="monitoring", name=deployment_name, apps_api=apps_api
        )
    for stateful_set_name in ("prometheus-k8s", "alertmanager-main"):
        assert _get_stateful_set(
            namespace="monitoring", name=stateful_set_name, apps_api=apps_api
        )
    assert _get_daemon_set(
        namespace="monitoring", name="node-exporter", apps_api=apps_api
    )


@pytest.mark.integration
def test_longhorn(apps_api: AppsV1Api) -> None:
    for deployment_name in (
        "longhorn-ui",
        "longhorn-driver-deployer",
        "csi-attacher",
        "csi-provisioner",
        "csi-snapshotter",
        "csi-resizer",
    ):
        assert _get_deployment(
            namespace="longhorn-system", name=deployment_name, apps_api=apps_api
        )
    for daemon_set_name in ("longhorn-manager", "longhorn-csi-plugin"):
        assert _get_daemon_set(
            namespace="longhorn-system", name=daemon_set_name, apps_api=apps_api
        )


@pytest.mark.integration
def test_ingress_nginx(apps_api: AppsV1Api) -> None:
    assert _get_deployment(
        namespace="ingress-nginx", name="ingress-nginx-controller", apps_api=apps_api
    )


@pytest.mark.integration
def test_arma3(apps_api: AppsV1Api) -> None:
    assert _get_stateful_set(namespace="arma3", name="arma3", apps_api=apps_api)
    assert _get_stateful_set(
        namespace="arma3-headless-client", name="arma3", apps_api=apps_api
    )


@pytest.mark.integration
def test_teamspeak(apps_api: AppsV1Api) -> None:
    assert _get_stateful_set(namespace="teamspeak", name="teamspeak", apps_api=apps_api)


# TODO test_are_all_jobs_ok


@pytest.mark.integration
def test_persistent_volume_claims_bound(
    core_api: CoreV1Api,
    all_namespaces: Sequence[V1Namespace],
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
