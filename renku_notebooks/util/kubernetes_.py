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
"""Kubernetes helper functions."""

from hashlib import md5
from pathlib import Path
from typing import Optional, Tuple

import escapism
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)
import logging


def get_k8s_client() -> Tuple[Optional[client.CoreV1Api], str]:
    try:
        InClusterConfigLoader(
            token_filename=SERVICE_TOKEN_FILENAME, cert_filename=SERVICE_CERT_FILENAME
        ).load_and_set()
        namespace_path = Path(
            "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
        )
        with open(namespace_path, "rt") as f:
            namespace = f.read()
        logging.info(f"Running notebook with in-cluster config and namespace {namespace}.")
    except ConfigException:
        config.load_config()
        contexts = config.list_kube_config_contexts()
        namespace = None
        if len(contexts) == 2:
            current_context = contexts[-1]
            namespace = current_context.get("context", {}).get("namespace")
        if not namespace:
            raise ValueError("Cannot determine k8s namespace from current context.")
        logging.warning(
            f"Running notebook service locally with currently active kube context "
            f"{current_context} and namespace {namespace}."
        )

    v1 = client.CoreV1Api()
    return v1, namespace


def filter_resources_by_annotations(
    resources,
    annotations,
):
    """Fetch all the user server pods that matches the provided annotations.
    If an annotation that is not present on the pod is provided the match fails."""

    def filter_resource(resource):
        res = []
        for annotation_name in annotations.keys():
            res.append(
                resource["metadata"]["annotations"].get(annotation_name)
                == annotations[annotation_name]
            )
        if len(res) == 0:
            return True
        else:
            return all(res)

    return list(filter(filter_resource, resources))


def secret_exists(name, k8s_client, k8s_namespace):
    """Check if the secret exists."""

    try:
        k8s_client.read_namespaced_secret(name, k8s_namespace)
        return True
    except client.rest.ApiException:
        pass
    return False


def make_server_name(safe_username, namespace, project, branch, commit_sha):
    """Form a 16-digit hash server ID."""
    server_string = f"{safe_username}-{namespace}-{project}-{branch}-{commit_sha}"
    return "{username}-{project}-{hash}".format(
        username=safe_username[:10].lower(),
        project=escapism.escape(project, escape_char="-")[:24].lower(),
        hash=md5(server_string.encode()).hexdigest()[:8].lower(),
    )
