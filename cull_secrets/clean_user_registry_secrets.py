# -*- coding: utf-8 -*-
#
# Copyright 2020 - Swiss Data Science Center (SDSC)
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

import argparse
from datetime import datetime, timedelta
import logging
from pathlib import Path
import re

from kubernetes import client
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)

POD_LABELS = [  # unlikely to have invalid characters, used to quickly filter
    "renku.io/commit-sha",
    "renku.io/username",
    "renku.io/projectName",
]

POD_ANNOTATIONS = [  # most likely to have invalid characters (i.e. /, \, etc)
    "renku.io/git-host",
    "renku.io/namespace",
]


def find_pod_by_secret(secret, k8s_client):
    """Find the user jupyterhub podname based on the registry pull secret."""
    label_selector = []
    for label_key in POD_LABELS:
        label_selector.append(f"{label_key}={secret.metadata.labels[label_key]}")
    label_selector = ",".join(label_selector)

    pod_list = k8s_client.list_namespaced_pod(
        secret.metadata.namespace, label_selector=label_selector,
    )
    matching_pods = []
    for pod in pod_list:
        match = True
        for annotation in POD_ANNOTATIONS:
            match = match and (
                pod.metadata.annotations is not None
                and secret.metadata.annotations is not None
                and annotation in pod.metadata.annotations.keys()
                and annotation in secret.metadata.annotations.keys()
                and pod.metadata.annotations.get(annotation, "pod_annotation")
                == secret.metadata.annotations.get(annotation, "secret_annotation")
            )
        if match:
            matching_pods.append(pod)

    if len(matching_pods) > 1:
        raise Exception(
            "There should at most one pod that matches a secret, "
            f"found {len(matching_pods)} that match the secret {secret.metadata.name}"
        )
    elif len(matching_pods) == 1:
        return matching_pods[0].metadata.name
    return None


def remove_user_registry_secret(namespace, k8s_client, max_secret_age_hrs=0.25):
    """Used in a cronjob to periodically remove old user registry secrets"""
    secret_name_regex = ".+-registry-[a-z0-9-]{36}$"
    logging.info(
        f"Checking for user registry secrets whose "
        f"names match the regex: {secret_name_regex}"
    )
    secret_list = k8s_client.list_namespaced_secret(
        namespace, label_selector="component=singleuser-server"
    )
    max_secret_age = timedelta(hours=max_secret_age_hrs)
    for secret in secret_list.items:
        # loop through secrets and find ones that match the predefined regex
        secret_name = secret.metadata.name
        secret_name_match = re.match(secret_name_regex, secret_name)
        # calculate secret age
        tz = secret.metadata.creation_timestamp.tzinfo
        secret_age = datetime.now(tz=tz) - secret.metadata.creation_timestamp
        if (
            secret_name_match is not None
            and secret.type == "kubernetes.io/dockerconfigjson"
            and all(
                [
                    # check that label keys for sha, username, namespace are present
                    label_key in secret.metadata.labels.keys()
                    for label_key in POD_LABELS
                ]
            )
            and all(
                [
                    # check that annotation keys for project name and git-host are present
                    annotation_key in secret.metadata.annotations.keys()
                    for annotation_key in POD_ANNOTATIONS
                ]
            )
        ):
            podname = find_pod_by_secret(secret, k8s_client)
            if podname is None:
                # pod does not exist, delete if secret is old enough
                if secret_age > max_secret_age:
                    logging.info(
                        f"User pod that used secret {secret_name} does not exist, "
                        f"deleting secret as it is older "
                        f"than the {max_secret_age_hrs} hours threshold"
                    )
                    k8s_client.delete_namespaced_secret(secret_name, namespace)
            else:
                # check if the pod has the expected annotations and is running or succeeded
                # no need to check for secret age because we are certain secret has been used
                pod = k8s_client.read_namespaced_pod(podname, namespace)
                if (
                    pod.metadata.labels.get("app") == "jupyterhub"
                    and pod.metadata.labels.get("component") == "singleuser-server"
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
        help="The maximum age allowed for a registry secret to have before it is removed"
        "if the user Jupyterhub pod cannot be found.",
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
