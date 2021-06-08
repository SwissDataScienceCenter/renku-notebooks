from kubernetes import client
import requests


def test_smoke(k8s_namespace):
    v1 = client.CoreV1Api()
    print([p.metadata.name for p in v1.list_namespaced_pod(k8s_namespace).items])


def test_server_options(base_url, headers):
    res = requests.get(f"{base_url}/server_options", headers=headers)
    print(res.status_code)
    print(res.json())
    assert False
