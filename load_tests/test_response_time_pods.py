from collections import OrderedDict
from kubernetes import client, config
import yaml
import logging
import timeit
from time import sleep

import numpy as np
import pandas as pd


def launch_pod(id, manifest, namespace, k8s_api: client.CoreV1Api):
    manifest["metadata"]["namespace"] = namespace
    manifest["metadata"]["name"] = id
    manifest["metadata"]["labels"]["testId"] = id
    k8s_api.create_namespaced_pod(
        namespace=namespace,
        body=manifest,
    )
    return True


def measure_list_response_time(k8s_namespace, selector=None, ntimes=30):
    test_setup = (
        "from kubernetes import client, config; "
        "config.load_config(); k8s_client = client.CoreV1Api();"
    )
    if selector:
        test_statement = (
            f"k8s_client.list_namespaced_pod(namespace='{k8s_namespace}', "
            f"label_selector='{selector}', "
            ")"
        )
    else:
        test_statement = f"k8s_client.list_namespaced_pod(namespace='{k8s_namespace}')"
    return (
        np.array(
            timeit.repeat(test_statement, number=1, repeat=ntimes, setup=test_setup)
        )
        * 1000
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    k8s_namespace = "amalthea"
    config.load_config()
    v1 = client.CoreV1Api()
    batches = 20
    sessions_per_batch = 10
    manifest_fin = "pod.yaml"
    output = OrderedDict()
    output_lagged = OrderedDict()
    with open(manifest_fin, "r") as f:
        manifest = yaml.safe_load(f)

    res_ms = measure_list_response_time(k8s_namespace, "testId=session-0-0", ntimes=50)
    output[0] = res_ms

    for ibatch in range(batches):
        logging.info(f"Starting batch {ibatch}")
        for isession in range(sessions_per_batch):
            id = f"session-{ibatch}-{isession}"
            logging.info(f"Starting pod id {id}")
            launch_pod(id, manifest, k8s_namespace, v1)

        res_ms = measure_list_response_time(
            k8s_namespace, "testId=session-0-0", ntimes=50
        )
        output[ibatch + 1] = res_ms

        logging.info(
            f"Ran tests {res_ms.shape[0]} times, mean: {res_ms.mean()}, "
            f"median: {np.median(res_ms)}, max: {res_ms.max()}, min:{res_ms.min()}"
        )

        # sleep(2)
        # res_ms = measure_list_response_time(k8s_namespace, "testId=session-0-0", ntimes=50)
        # logging.info(
        #     f"Lagged results {res_ms.shape[0]} times, mean: {res_ms.mean()}, "
        #     f"median: {np.median(res_ms)}, max: {res_ms.max()}, min:{res_ms.min()}"
        # )
        # output_lagged[ibatch + 1] = res_ms

    output = pd.DataFrame(output)
    output.T.to_csv("test_personal_cluster_pods_20batch_10sessperbatch.csv")
    # output_lagged = pd.DataFrame(output_lagged)
    # output_lagged.T.to_csv("test_personal_cluster_20batch_10sessperbatch_lagged.csv")

    res_ms = measure_list_response_time(k8s_namespace, "testId=session-0-0", ntimes=50)
    logging.info(
        f"Check at the end {res_ms.shape[0]} times, mean: {res_ms.mean()}, "
        f"median: {np.median(res_ms)}, max: {res_ms.max()}, min:{res_ms.min()}"
    )
