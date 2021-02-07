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
from datetime import timezone
from pathlib import Path
from urllib.parse import urljoin

import escapism
from flask import current_app
from kubernetes import client
from kubernetes.client.rest import ApiException
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


def get_all_user_pods(user, k8s_client, k8s_namespace):
    safe_username = escapism.escape(user["name"], escape_char="-").lower()
    pods = k8s_client.list_namespaced_pod(
        k8s_namespace,
        label_selector=f"heritage=jupyterhub,renku.io/username={safe_username}",
    )
    return pods.items


def filter_pods_by_annotations(
    pods, annotations,
):
    """Fetch all the user server pods that matches the provided annotations.
    If an annotation that is not present on the pod is provided the match fails."""

    def filter_pod(pod):
        res = []
        for annotation_name in annotations.keys():
            res.append(
                pod.get("metadata", {}).get("annotations", {}).get(annotation_name)
                == annotations[annotation_name]
            )
        if len(res) == 0:
            return True
        else:
            return all(res)

    return list(filter(filter_pod, pods))


def delete_user_pod(user, pod_name, k8s_client, k8s_namespace):
    """Delete user's server with specific name"""
    try:
        k8s_client.delete_namespaced_pod(
            pod_name, k8s_namespace, grace_period_seconds=30
        )
        return True
    except ApiException as e:
        msg = f"Cannot delete server: {pod_name} for user: {user}, error: {e}"
        current_app.logger.error(msg)
        return False


def format_user_pod_data(
    pod,
    jupyterhub_path_prefix,
    default_image,
    renku_annotation_prefix,
    jupyterhub_origin,
):
    def isoformat(dt):
        """
        Render a datetime object as an ISO 8601 UTC timestamp.
        Naïve datetime objects are assumed to be UTC
        """
        if dt is None:
            return None
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.isoformat(timespec="microseconds") + "Z"

    def summarise_pod_conditions(conditions):
        def sort_conditions(conditions):
            CONDITIONS_ORDER = {
                "PodScheduled": 1,
                "Unschedulable": 2,
                "Initialized": 3,
                "ContainersReady": 4,
                "Ready": 5,
            }
            return sorted(conditions, key=lambda c: CONDITIONS_ORDER[c.type])

        if not conditions:
            return {"step": None, "message": None, "reason": None}

        for c in sort_conditions(conditions):
            if (
                (c.type == "Unschedulable" and c.status == "True")
                or (c.status != "True")
                or (c.type == "Ready" and c.status == "True")
            ):
                break
        return {"step": c.type, "message": c.message, "reason": c.reason}

    def get_pod_status(pod):
        ready = getattr(pod.metadata, "deletion_timestamp", None) is None
        try:
            for status in pod.status.container_statuses:
                ready = ready and status.ready
        except (IndexError, TypeError):
            ready = False

        status = {"phase": pod.status.phase, "ready": ready}
        conditions_summary = summarise_pod_conditions(pod.status.conditions)
        status.update(conditions_summary)
        return status

    def get_pod_resources(pod):
        try:
            for container in pod.spec.containers:
                if container.name == "notebook":
                    resources = container.resources.requests
                    # translate the cpu weird numeric string to a normal number
                    # ref: https://kubernetes.io/docs/concepts/configuration/
                    #   manage-compute-resources-container/#how-pods-with-resource-limits-are-run
                    if (
                        "cpu" in resources
                        and isinstance(resources["cpu"], str)
                        and str.endswith(resources["cpu"], "m")
                        and resources["cpu"][:-1].isdigit()
                    ):
                        resources["cpu"] = str(int(resources["cpu"][:-1]) / 1000)
        except (AttributeError, IndexError):
            resources = {}
        return resources

    def get_server_url(pod):
        url = "{jh_path_prefix}/user/{username}/{servername}/".format(
            jh_path_prefix=jupyterhub_path_prefix.rstrip("/"),
            username=pod.metadata.annotations["hub.jupyter.org/username"],
            servername=pod.metadata.annotations["hub.jupyter.org/servername"],
        )
        return urljoin(jupyterhub_origin, url)

    return {
        "annotations": {
            **pod.metadata.annotations,
            renku_annotation_prefix
            + "default_image_used": str(pod.spec.containers[0].image == default_image),
        },
        "name": pod.metadata.annotations["hub.jupyter.org/servername"],
        "state": {"pod_name": pod.metadata.name},
        "started": isoformat(pod.status.start_time),
        "status": get_pod_status(pod),
        "url": get_server_url(pod),
        "resources": get_pod_resources(pod),
        "image": pod.spec.containers[0].image,
    }


def secret_exists(name, k8s_client, k8s_namespace):
    """Check if the secret exists."""

    try:
        k8s_client.read_namespaced_secret(name, k8s_namespace)
        return True
    except client.rest.ApiException:
        pass
    return False
