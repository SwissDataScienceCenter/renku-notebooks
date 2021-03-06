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

import os
import warnings
from pathlib import Path

from kubernetes import client
from kubernetes.config.config_exception import ConfigException
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)


def get_k8s_client():
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
    return v1, kubernetes_namespace


def filter_pods_by_annotations(
    pods, annotations,
):
    """Fetch all the user server pods that matches the provided annotations.
    If an annotation that is not present on the pod is provided the match fails."""

    def filter_pod(pod):
        res = []
        for annotation_name in annotations.keys():
            res.append(
                pod.metadata.annotations.get(annotation_name)
                == annotations[annotation_name]
            )
        if len(res) == 0:
            return True
        else:
            return all(res)

    return list(filter(filter_pod, pods))


def secret_exists(name, k8s_client, k8s_namespace):
    """Check if the secret exists."""

    try:
        k8s_client.read_namespaced_secret(name, k8s_namespace)
        return True
    except client.rest.ApiException:
        pass
    return False
