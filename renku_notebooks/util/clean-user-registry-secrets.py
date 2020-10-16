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

from kubernetes import client
from kubernetes.config.config_exception import ConfigException
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)


def find_pod_by_servername(namespace, servername):
    """Find the podname based on the servername annotation used by jupyterhub"""
    try:
        pod_list = v1.list_namespaced_pod(namespace)
    except client.rest.ApiException:
        logging.warning(f'Namespace {namespace} does not exist or the cluster is unreachable.')
    else:
        for pod in pod_list.items:
            if pod.metadata.annotations is not None and \
                pod.metadata.annotations.get('hub.jupyter.org/servername') == servername:
                return pod.metadata.name
    return None


def remove_user_registry_secret(namespace, min_secret_age_hrs=0.25):
    """Used in a cronjob to periodically remove old user registry secrets"""
    secret_name_regex = "(.+)-registry$"
    logging.info(f"Checking for user registry secrets whose "
                 f"names match the regex: {secret_name_regex}")
    try:
        secret_list = v1.list_namespaced_secret(namespace)
    except client.rest.ApiException:
        logging.warning(f'Namespace {namespace} does not exist or the cluster is unreachable.')
    else:
        for secret in secret_list.items:
            # loop through secrets and find ones that match the predefined regex
            secret_name = secret.metadata.name
            servername_match = re.match(secret_name_regex, secret_name)
            # calculate secret age
            tz = secret.metadata.creation_timestamp.tzinfo
            secret_age = datetime.now(tz=tz) - secret.metadata.creation_timestamp
            min_secret_age = timedelta(hours=min_secret_age_hrs)
            if servername_match is not None and secret.type == 'kubernetes.io/dockerconfigjson':
                servername = servername_match.group(1)
                podname = find_pod_by_servername(namespace, servername)
                if podname is None:
                    # pod does not exist, delete if secret is old enough
                    if secret_age > min_secret_age:
                        logging.info(f'User pod that hosts server {servername} does not exist, '
                                    f'deleting secret {secret_name} as it is older '
                                    f'than the {min_secret_age_hrs} hours threshold')
                        v1.delete_namespaced_secret(secret_name, namespace)
                else:
                    # check if the pod has the expected annotations and is running or succeeded
                    # no need to check for secret age because we are certain secret has been used
                    try:
                        pod = v1.read_namespaced_pod(podname, namespace)
                    except client.rest.ApiException:
                        logging.warning(f'Cannot find pod {podname}, secret has not been removed.')
                    else:
                        if pod.metadata.labels.get("app") == "jupyterhub" \
                            and pod.metadata.labels.get("component") == "singleuser-server" \
                            and pod.status.phase in ["Running", "Succeeded"]:
                            logging.info(f'Found user pod {podname} that hosts '
                                         f'server {servername}, '
                                         f'deleting secret {secret_name}.')
                            v1.delete_namespaced_secret(secret_name, namespace)


def float_gt_zero(number):
    if float(number) <= 0:
        raise argparse.ArgumentTypeError(f"{number} should be a float and greater than zero.")
    else:
        return float(number)


if __name__ == '__main__':
    # set logging level
    logging.basicConfig(level=logging.INFO)

    # check arguments
    parser = argparse.ArgumentParser(description='Clean up user registry secrets.')
    parser.add_argument('-n', '--namespace', type=str,
                        help='K8s namespace where the user pods and registry secrets are located.')
    parser.add_argument('-a', '--age-hours-minimum', type=float_gt_zero, default=0.25,
                        help='The minimum age for a secret before it can be deleted if the user'
                             'pod cannot be found.')
    args = parser.parse_args()

    # initialize k8s client
    token_filename = Path(SERVICE_TOKEN_FILENAME)
    cert_filename = Path(SERVICE_CERT_FILENAME)
    InClusterConfigLoader(
        token_filename=token_filename, cert_filename=cert_filename
    ).load_and_set()
    v1 = client.CoreV1Api()
   
    # remove user registry secret
    remove_user_registry_secret(args.namespace, args.age_hours_minimum)
