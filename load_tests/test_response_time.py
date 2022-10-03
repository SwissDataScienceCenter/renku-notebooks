from collections import OrderedDict
from kubernetes import client, config
import yaml
import logging
import timeit

import numpy as np
import pandas as pd


def launch_session(id, manifest, namespace, k8s_api: client.CustomObjectsApi):
    manifest["metadata"]["namespace"] = namespace
    manifest["metadata"]["name"] = id
    manifest["metadata"]["labels"]["testId"] = id
    k8s_api.create_namespaced_custom_object(
        group="amalthea.dev",
        version="v1alpha1",
        namespace=namespace,
        plural="jupyterservers",
        body=manifest,
    )
    return True


def measure_list_response_time(k8s_namespace, selector=None, ntimes=30):
    test_setup = (
        "from kubernetes import client, config; "
        "config.load_config(); k8s_client = client.CoreV1Api(); "
        "k8s_api_instance = client.CustomObjectsApi(client.ApiClient())"
    )
    if selector:
        test_statement = (
            "k8s_api_instance.list_namespaced_custom_object(group='amalthea.dev', "
            f"version='v1alpha1', namespace='{k8s_namespace}', plural='jupyterservers', "
            f"label_selector='{selector}'"
            ")"
        )
    else:
        test_statement = (
            "k8s_api_instance.list_namespaced_custom_object(group='amalthea.dev', "
            f"version='v1alpha1', namespace='{k8s_namespace}', plural='jupyterservers', "
            ")"
        )
    return np.array(timeit.repeat(test_statement, number=1, repeat=ntimes, setup=test_setup)) * 1000


def measure_get_response_time(k8s_namespace, name, ntimes=30):
    test_setup = (
        "from kubernetes import client, config; "
        "config.load_config(); k8s_client = client.CoreV1Api(); "
        "k8s_api_instance = client.CustomObjectsApi(client.ApiClient())"
    )
    test_statement = (
        "k8s_api_instance.get_namespaced_custom_object(group='amalthea.dev', "
        f"version='v1alpha1', namespace='{k8s_namespace}', plural='jupyterservers', "
        f"name='{name}', "
        ")"
    )
    return np.array(timeit.repeat(test_statement, number=1, repeat=ntimes, setup=test_setup)) * 1000


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    k8s_namespace = "tasko"
    config.load_config()
    k8s_client = client.CoreV1Api()
    k8s_api_instance = client.CustomObjectsApi(client.ApiClient())
    batches = 20
    sessions_per_batch = 10
    manifest_fin = "session.yaml"
    output = OrderedDict()
    with open(manifest_fin, "r") as f:
        manifest = yaml.safe_load(f)

    res_ms = measure_list_response_time(k8s_namespace, "testId=session-0-0", ntimes=50)
    output[0] = res_ms

    for ibatch in range(batches):
        logging.info(f"Starting batch {ibatch}")
        for isession in range(sessions_per_batch):
            id = f"session-{ibatch}-{isession}"
            logging.info(f"Starting session id {id}")
            launch_session(id, manifest, k8s_namespace, k8s_api_instance)

        res_ms = measure_list_response_time(k8s_namespace, "testId=session-0-0", ntimes=50)
        output[ibatch + 1] = res_ms

        logging.info(
            f"Ran tests {res_ms.shape[0]} times, mean: {res_ms.mean()}, "
            f"median: {np.median(res_ms)}, max: {res_ms.max()}, min:{res_ms.min()}"
        )

    output = pd.DataFrame(output)
    output.T.to_csv("test_gcp_cluster_20batch_10sessperbatch.csv")

    res_ms = measure_get_response_time(k8s_namespace, "session-0-0", ntimes=50)
    logging.info(
        f"Ran tests {res_ms.shape[0]} times, mean: {res_ms.mean()}, "
        f"median: {np.median(res_ms)}, max: {res_ms.max()}, min:{res_ms.min()}"
    )
