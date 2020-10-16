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

import os
import warnings
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import re
import logging

from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)


def remove_user_registry_secret(namespace, min_secret_age_hrs=0.25):
    """Used in a cronjob to periodically remove old user registry secrets"""
    secret_name_regex = "(.+)-registry$"
    try:
        secret_list = v1.list_namespaced_secret(namespace)
    except client.rest.ApiException:
        logging.warning(f'Namespace {namespace} does not exist or the cluster is unreachable.')
    else:
        for secret in secret_list.items:
            secret_name = secret.metadata.name
            server_name_match = re.match(secret_name_regex, secret_name)
            tz = secret.metadata.creation_timestamp.tzinfo
            secret_age = datetime.now(tz=tz) - secret.metadata.creation_timestamp
            min_secret_age = timedelta(hours=min_secret_age_hrs)
            if server_name_match is not None and secret.type == 'kubernetes.io/dockerconfigjson':
                server_name = server_name_match.group(1)
                try:
                    pod = v1.read_namespaced_pod(server_name, namespace)
                except client.rest.ApiException:
                    # pod does not exist, delete if secret is old enough
                    if secret_age > min_secret_age:
                        logging.info(f'Corresponding pod {server_name} does not exist, '
                                     f'deleting secret {secret_name} as it is older '
                                     f'than the {min_secret_age_hrs} threshold')
                        v1.delete_namespaced_secret(secret_name, namespace)
                else:
                    # check if the pod has the expected annotations and is running or succeeded
                    # no need to check for secret age because we are certain secret has been used
                    if pod.metadata.labels.get("app") == "jupyter" \
                        and pod.metadata.labels.get("component") == "singleuser-server" \
                        and pod.status.phase in ["Running", "Succeeded"]:
                        logging.info(f'Found related pod {server_name}, '
                                     f'deleting secret {secret_name}.')
                        v1.delete_namespaced_secret(secret_name, namespace)


def float_gt_zero(number):
    if float(number) <= 0:
        raise argparse.ArgumentTypeError(f"{number} should be a float and greater than zero.")
    else:
        return float(number)


if __name__ == '__main__':
    # adjust k8s service account paths if running inside telepresence
    tele_root = Path(os.getenv("TELEPRESENCE_ROOT", "/"))

    token_filename = tele_root / Path(SERVICE_TOKEN_FILENAME).relative_to("/")
    cert_filename = tele_root / Path(SERVICE_CERT_FILENAME).relative_to("/")
    namespace_path = tele_root / Path(
        "var/run/secrets/kubernetes.io/serviceaccount/namespace"
    )

    try:
        InClusterConfigLoader(
            token_filename=token_filename, cert_filename=cert_filename
        ).load_and_set()
        v1 = client.CoreV1Api()
    except ConfigException:
        v1 = None
        warnings.warn("Unable to configure the kubernetes client.")

    try:
        with open(namespace_path, "rt") as f:
            kubernetes_namespace = f.read()
    except FileNotFoundError:
        kubernetes_namespace = ""
        warnings.warn(
            "No k8s service account found - not running inside a kubernetes cluster?"
        )
    
    # check arguments
    parser = argparse.ArgumentParser(description='Clean up user registry secrets.')
    parser.add_argument('-n', '--namespace', type=str,
                        help='K8s namespace where the user pods and registry secrets are located.')
    parser.add_argument('-a', '--age-hours-minimum', type=float_gt_zero, default=0.25,
                        help='The minimum age for a secret before it can be deleted if the user'
                             'pod cannot be found.')
    args = parser.parse_args()
    # remove user registry secret
    remove_user_registry_secret(args.namespace, args.age_hours_minimum)
