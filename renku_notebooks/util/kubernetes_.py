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

import escapism
from flask import current_app
from kubernetes import client
from kubernetes.client.models.v1_resource_requirements import V1ResourceRequirements
from kubernetes.config.config_exception import ConfigException
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)

from .file_size import parse_file_size


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


def create_pvc(
    name,
    username,
    git_namespace,
    project_id,
    project,
    branch,
    commit_sha,
    git_host,
    storage_size,
    storage_class="default",
):
    """Create a PVC."""
    v1, kubernetes_namespace = get_k8s_client()

    # check if we already have this PVC
    pvc = _get_pvc(name)
    if pvc:
        status = "existing"

        # if the requested size is bigger than the original PVC, resize
        if parse_file_size(
            pvc.spec.resources.requests.get("storage")
        ) < parse_file_size(storage_size):

            pvc.spec.resources.requests["storage"] = storage_size
            v1.patch_namespaced_persistent_volume_claim(
                name=pvc.metadata.name, namespace=kubernetes_namespace, body=pvc
            )

    if not pvc:
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(
                name=name,
                annotations={
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "git-host": git_host,
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "namespace": git_namespace,
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "username": username,
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "commit-sha": commit_sha,
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "branch": branch,
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "projectName": project,
                },
                labels={
                    "component": "singleuser-server",
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "username": username,
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "commit-sha": commit_sha,
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "gitlabProjectId": str(project_id),
                },
            ),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                volume_mode="Filesystem",
                storage_class_name=storage_class,
                resources=V1ResourceRequirements(requests={"storage": storage_size}),
            ),
        )
        v1.create_namespaced_persistent_volume_claim(kubernetes_namespace, pvc)
        status = "created"
    return {"status": status, "pvc": pvc}


def delete_pvc(name):
    """Delete a specified PVC."""
    v1, kubernetes_namespace = get_k8s_client()
    pvc = _get_pvc(name)
    if pvc:
        v1.delete_namespaced_persistent_volume_claim(
            name=pvc.metadata.name, namespace=kubernetes_namespace
        )
        return pvc


def _get_pvc(name):
    """Fetch the PVC for the given username, project, commit combination."""
    v1, kubernetes_namespace = get_k8s_client()
    try:
        return v1.read_namespaced_persistent_volume_claim(name, kubernetes_namespace)
    except client.ApiException:
        return None


def make_pvc_name(username, namespace, server_name):
    """Form a PVC name from a username and servername."""
    safe_username = escapism.escape(username, escape_char="-").lower()
    return f"{safe_username}-{namespace}-{server_name}-pvc"
