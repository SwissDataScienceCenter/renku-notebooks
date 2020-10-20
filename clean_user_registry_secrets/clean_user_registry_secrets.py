# -*- coding: utf-8 -*-
#
# Copyright 2019 - Swiss Data Science Center (SDSC)
# A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
# Eidgenössische Technische Hochschule Zürich (ETHZ).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Scripts used to remove user registry secrets in k8s"""

from datetime import datetime, timedelta
from pathlib import Path
import argparse
import re
import logging
from functools import reduce

from kubernetes import client
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)


def find_pod_by_secret(secret, k8s_client):
    """Find the user jupyterhub podname based on the registry pull secret."""
    label_keys = ['renku.io/commit-sha', 'renku.io/projectName', 'renku.io/username']
    label_selector = []
    for label_key in label_keys:
        label_selector.append(f"{label_key}={secret.metadata.labels[label_key]}")
    label_selector = ",".join(label_selector)

    pod_list = k8s_client.list_namespaced_pod(
        secret.metadata.namespace,
        label_selector=label_selector,
    )
    if len(pod_list.items) > 0:
        return pod_list.items[0].metadata.name
    return None


def remove_user_registry_secret(namespace, k8s_client, min_secret_age_hrs=0.25):
    """Used in a cronjob to periodically remove old user registry secrets"""
    secret_name_regex = "[a-z0-9-]{36}-registry$"
    label_keys = ['renku.io/commit-sha', 'renku.io/projectName', 'renku.io/username']
    logging.info(
        f"Checking for user registry secrets whose "
        f"names match the regex: {secret_name_regex}"
    )
    secret_list = k8s_client.list_namespaced_secret(namespace)
    logging.warning(
        f"Namespace {namespace} does not exist or the cluster is unreachable."
    )
    for secret in secret_list.items:
        # loop through secrets and find ones that match the predefined regex
        secret_name = secret.metadata.name
        secret_name_match = re.match(secret_name_regex, secret_name)
        # calculate secret age
        tz = secret.metadata.creation_timestamp.tzinfo
        secret_age = datetime.now(tz=tz) - secret.metadata.creation_timestamp
        min_secret_age = timedelta(hours=min_secret_age_hrs)
        if (
            secret_name_match is not None
            and secret.type == "kubernetes.io/dockerconfigjson"
            and secret.metadata.labels.get("component") == "singleuser-server"
            and reduce(  # check that label keys for sha, project and username are present
                lambda acc, val: acc and (val in secret.metadata.labels.keys()),
                label_keys,
                True,
            )
        ):
            podname = find_pod_by_secret(secret, k8s_client)
            if podname is None:
                # pod does not exist, delete if secret is old enough
                if secret_age > min_secret_age:
                    logging.info(
                        f"User pod that used secret {secret_name} does not exist, "
                        f"deleting secret as it is older "
                        f"than the {min_secret_age_hrs} hours threshold"
                    )
                    k8s_client.delete_namespaced_secret(secret_name, namespace)
            else:
                # check if the pod has the expected annotations and is running or succeeded
                # no need to check for secret age because we are certain secret has been used
                pod = k8s_client.read_namespaced_pod(podname, namespace)
                if (
                    pod.metadata.labels.get("app") == "jupyterhub"
                    and pod.metadata.labels.get("component")
                    == "singleuser-server"
                    and pod.status.phase in ["Running", "Succeeded"]
                ):
                    logging.info(
                        f"Found user pod {podname} that used the secret, "
                        f"deleting secret {secret_name}."
                    )
                    k8s_client.delete_namespaced_secret(secret_name, namespace)


def float_gt_zero(number):
    if float(number) <= 0:
        raise argparse.ArgumentTypeError(
            f"{number} should be a float and greater than zero."
        )
    else:
        return float(number)


def main():
    # set logging level
    logging.basicConfig(level=logging.INFO)

    # check arguments
    parser = argparse.ArgumentParser(description="Clean up user registry secrets.")
    parser.add_argument(
        "-n",
        "--namespace",
        type=str,
        required=True,
        help="K8s namespace where the user pods and registry secrets are located.",
    )
    parser.add_argument(
        "-a",
        "--age-hours-minimum",
        type=float_gt_zero,
        default=0.25,
        help="The minimum age for a secret before it can be deleted if the user"
        "pod cannot be found.",
    )
    args = parser.parse_args()

    # initialize k8s client
    token_filename = Path(SERVICE_TOKEN_FILENAME)
    cert_filename = Path(SERVICE_CERT_FILENAME)
    InClusterConfigLoader(
        token_filename=token_filename, cert_filename=cert_filename
    ).load_and_set()
    k8s_client = client.CoreV1Api()

    # remove user registry secret
    remove_user_registry_secret(args.namespace, k8s_client, args.age_hours_minimum)


if __name__ == "__main__":
    main()
