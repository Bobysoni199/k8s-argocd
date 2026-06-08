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


def run_kubectl(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True,
            text=True,
            timeout=15,
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
    """List HPAs in an allowed namespace."""
    error = validate_namespace(namespace)
    if error:
        return error

    return run_kubectl(["get", "hpa", "-n", namespace])


@mcp.tool()
def list_argocd_apps() -> str:
    """List Argo CD Applications."""
    return run_kubectl(["get", "applications", "-n", "argocd"])


@mcp.tool()
def describe_pod(namespace: str, pod_name: str) -> str:
    """Describe a pod in an allowed namespace."""
    error = validate_namespace(namespace)
    if error:
        return error

    if not pod_name.replace("-", "").replace(".", "").isalnum():
        return "ERROR: invalid pod name"

    return run_kubectl(["describe", "pod", pod_name, "-n", namespace])


if __name__ == "__main__":
    mcp.run()
