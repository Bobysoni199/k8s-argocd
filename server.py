import subprocess
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kubernetes-mcp-server")

ALLOWED_NAMESPACES = {
    "default",
    "dev",
    "staging",
    "prod",
    "argocd",
    "ingress-nginx",
    "kube-system",
    "monitoring",
    "logging",
}

ALLOWED_DEPLOYMENTS = {
    "frontend",
    "backend",
}


def run_kubectl(args: list[str], timeout: int = 20) -> str:
    try:
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        if result.returncode != 0:
            return f"ERROR:\n{result.stderr.strip()}"

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        return "ERROR: kubectl command timed out"
    except Exception as e:
        return f"ERROR: {str(e)}"


def validate_namespace(namespace: str) -> Optional[str]:
    if namespace not in ALLOWED_NAMESPACES:
        return (
            f"ERROR: namespace '{namespace}' is not allowed. "
            f"Allowed namespaces: {', '.join(sorted(ALLOWED_NAMESPACES))}"
        )
    return None


def validate_name(name: str) -> bool:
    allowed_chars_removed = name.replace("-", "").replace(".", "").replace("_", "")
    return allowed_chars_removed.isalnum()


@mcp.tool()
def list_namespaces() -> str:
    """List Kubernetes namespaces."""
    return run_kubectl(["get", "namespaces"])


@mcp.tool()
def list_pods(namespace: str = "dev") -> str:
    """List pods in an allowed namespace."""
    error = validate_namespace(namespace)
    if error:
        return error

    return run_kubectl(["get", "pods", "-n", namespace, "-o", "wide"])


@mcp.tool()
def list_services(namespace: str = "dev") -> str:
    """List services in an allowed namespace."""
    error = validate_namespace(namespace)
    if error:
        return error

    return run_kubectl(["get", "svc", "-n", namespace])


@mcp.tool()
def list_hpa(namespace: str = "dev") -> str:
    """List HorizontalPodAutoscalers in an allowed namespace."""
    error = validate_namespace(namespace)
    if error:
        return error

    return run_kubectl(["get", "hpa", "-n", namespace])


@mcp.tool()
def list_argocd_apps() -> str:
    """List Argo CD Applications."""
    return run_kubectl(["get", "applications", "-n", "argocd", "-o", "wide"])


@mcp.tool()
def describe_pod(namespace: str, pod_name: str) -> str:
    """Describe a pod in an allowed namespace."""
    error = validate_namespace(namespace)
    if error:
        return error

    if not validate_name(pod_name):
        return "ERROR: invalid pod name"

    return run_kubectl(["describe", "pod", pod_name, "-n", namespace])


@mcp.tool()
def get_pod_logs(namespace: str, pod_name: str, tail: int = 100) -> str:
    """Get recent logs from a pod in an allowed namespace."""
    error = validate_namespace(namespace)
    if error:
        return error

    if not validate_name(pod_name):
        return "ERROR: invalid pod name"

    if tail < 1 or tail > 500:
        return "ERROR: tail must be between 1 and 500"

    return run_kubectl(["logs", pod_name, "-n", namespace, "--tail", str(tail)])


@mcp.tool()
def get_recent_events(namespace: str = "dev") -> str:
    """Get recent Kubernetes events in an allowed namespace."""
    error = validate_namespace(namespace)
    if error:
        return error

    return run_kubectl([
        "get",
        "events",
        "-n",
        namespace,
        "--sort-by=.lastTimestamp",
    ])


@mcp.tool()
def get_deployment_status(namespace: str = "dev", deployment: str = "backend") -> str:
    """Get deployment rollout and current status."""
    error = validate_namespace(namespace)
    if error:
        return error

    if deployment not in ALLOWED_DEPLOYMENTS:
        return f"ERROR: deployment '{deployment}' is not allowed"

    deployment_info = run_kubectl([
        "get",
        "deployment",
        deployment,
        "-n",
        namespace,
        "-o",
        "wide",
    ])

    rollout_status = run_kubectl([
        "rollout",
        "status",
        f"deployment/{deployment}",
        "-n",
        namespace,
        "--timeout=10s",
    ], timeout=15)

    return f"DEPLOYMENT:\n{deployment_info}\n\nROLLOUT:\n{rollout_status}"


@mcp.tool()
def get_argocd_app_status(app_name: str = "backend-dev") -> str:
    """Get Argo CD application status."""
    if not validate_name(app_name):
        return "ERROR: invalid Argo CD app name"

    return run_kubectl([
        "get",
        "application",
        app_name,
        "-n",
        "argocd",
        "-o",
        "wide",
    ])


@mcp.tool()
def restart_deployment_safe(namespace: str = "dev", deployment: str = "backend") -> str:
    """
    Safely restart an allowed deployment.
    Only predefined deployments are allowed.
    """
    error = validate_namespace(namespace)
    if error:
        return error

    if deployment not in ALLOWED_DEPLOYMENTS:
        return f"ERROR: deployment '{deployment}' is not allowed"

    restart_output = run_kubectl([
        "rollout",
        "restart",
        f"deployment/{deployment}",
        "-n",
        namespace,
    ])

    status_output = run_kubectl([
        "rollout",
        "status",
        f"deployment/{deployment}",
        "-n",
        namespace,
        "--timeout=30s",
    ], timeout=35)

    return f"RESTART:\n{restart_output}\n\nSTATUS:\n{status_output}"


@mcp.tool()
def diagnose_namespace(namespace: str = "dev") -> str:
    """
    Run a read-only diagnosis for pods, services, HPA, events, and Argo CD apps.
    """
    error = validate_namespace(namespace)
    if error:
        return error

    pods = run_kubectl(["get", "pods", "-n", namespace, "-o", "wide"])
    services = run_kubectl(["get", "svc", "-n", namespace])
    hpa = run_kubectl(["get", "hpa", "-n", namespace])
    events = run_kubectl([
        "get",
        "events",
        "-n",
        namespace,
        "--sort-by=.lastTimestamp",
    ])
    apps = run_kubectl(["get", "applications", "-n", "argocd", "-o", "wide"])

    return f"""
NAMESPACE: {namespace}

PODS:
{pods}

SERVICES:
{services}

HPA:
{hpa}

RECENT EVENTS:
{events}

ARGO CD APPS:
{apps}
""".strip()


if __name__ == "__main__":
    mcp.run()
