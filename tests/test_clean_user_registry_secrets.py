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
"""Tests for cronjob that removes user registry secrets."""
from unittest.mock import patch, create_autospec
from kubernetes.client import CoreV1Api
from datetime import datetime, timedelta
import pytest

from renku_notebooks.util.clean_user_registry_secrets import remove_user_registry_secret
from tests.conftest import _AttributeDictionary

namespace = "tasko"
servername = "servername"
secretname = f"{servername}-registry"
podname = "server-pod"
min_secret_age_hrs = 0.5


@pytest.fixture
def secret_list_valid():
    yield _AttributeDictionary(
        {
            "items": [
                {
                    "type": "kubernetes.io/dockerconfigjson",
                    "metadata": {
                        "name": secretname,
                        "creation_timestamp": datetime.now() - timedelta(hours=10),
                    },
                },
                {
                    "type": "random_secret",
                    "metadata": {
                        "name": "secret1-random",
                        "creation_timestamp": datetime(2020, 1, 1),
                    },
                },
            ]
        }
    )


@pytest.fixture
def secret_list_valid_new_secret():
    yield _AttributeDictionary(
        {
            "items": [
                {
                    "type": "kubernetes.io/dockerconfigjson",
                    "metadata": {
                        "name": secretname,
                        "creation_timestamp": datetime.now() + timedelta(hours=10),
                    },
                },
                {
                    "type": "random_secret",
                    "metadata": {
                        "name": "secret1-random",
                        "creation_timestamp": datetime(2020, 1, 1),
                    },
                },
            ]
        }
    )


@pytest.fixture
def secret_list_invalid_type():
    yield _AttributeDictionary(
        {
            "items": [
                {
                    "type": "random_secret",
                    "metadata": {
                        "name": secretname,
                        "creation_timestamp": datetime(2020, 1, 1),
                    },
                },
                {
                    "type": "random_secret",
                    "metadata": {
                        "name": "secret1-random",
                        "creation_timestamp": datetime(2020, 1, 1),
                    },
                },
            ]
        }
    )


@pytest.fixture
def pod_sample_valid():
    yield _AttributeDictionary(
        {
            "metadata": {
                "name": podname,
                "labels": {"app": "jupyterhub", "component": "singleuser-server"},
            },
            "status": {"phase": "Running"},
        }
    )


@pytest.fixture
def pod_sample_pending():
    yield _AttributeDictionary(
        {
            "metadata": {
                "name": podname,
                "labels": {"app": "jupyterhub", "component": "singleuser-server"},
            },
            "status": {"phase": "Pending"},
        }
    )


@patch("renku_notebooks.util.clean_user_registry_secrets.find_pod_by_servername")
def test_remove_user_registry_secret_existing_pod(
    find_pod_by_servername, secret_list_valid, pod_sample_valid
):
    """Test deletion when server pod is still present and is running"""
    k8s_client = create_autospec(CoreV1Api)
    find_pod_by_servername.return_value = podname
    k8s_client.list_namespaced_secret.return_value = secret_list_valid
    k8s_client.read_namespaced_pod.return_value = pod_sample_valid
    remove_user_registry_secret(namespace, k8s_client, min_secret_age_hrs)
    k8s_client.list_namespaced_secret.assert_called_once_with(namespace)
    find_pod_by_servername.assert_called_once_with(namespace, servername, k8s_client)
    k8s_client.read_namespaced_pod.assert_called_once_with(podname, namespace)
    k8s_client.delete_namespaced_secret.assert_called_once_with(secretname, namespace)


@patch("renku_notebooks.util.clean_user_registry_secrets.find_pod_by_servername")
def test_remove_user_registry_secret_no_pod(
    find_pod_by_servername, secret_list_valid, pod_sample_valid
):
    """Test deletion when server pod is not present and secret is old enough"""
    k8s_client = create_autospec(CoreV1Api)
    find_pod_by_servername.return_value = None
    k8s_client.list_namespaced_secret.return_value = secret_list_valid
    remove_user_registry_secret(namespace, k8s_client, min_secret_age_hrs)
    k8s_client.list_namespaced_secret.assert_called_once_with(namespace)
    find_pod_by_servername.assert_called_once_with(namespace, servername, k8s_client)
    assert not k8s_client.read_namespaced_pod.called
    k8s_client.delete_namespaced_secret.assert_called_once_with(secretname, namespace)


@patch("renku_notebooks.util.clean_user_registry_secrets.find_pod_by_servername")
def test_secret_age_threshold(
    find_pod_by_servername, secret_list_valid_new_secret, pod_sample_valid
):
    """Ensure secret is not deleted if server pod is not around and secret is not old enough"""
    k8s_client = create_autospec(CoreV1Api)
    find_pod_by_servername.return_value = None
    k8s_client.list_namespaced_secret.return_value = secret_list_valid_new_secret
    remove_user_registry_secret(namespace, k8s_client, min_secret_age_hrs)
    k8s_client.list_namespaced_secret.assert_called_once_with(namespace)
    find_pod_by_servername.assert_called_once_with(namespace, servername, k8s_client)
    assert not k8s_client.read_namespaced_pod.called
    assert not k8s_client.delete_namespaced_secret.called


@patch("renku_notebooks.util.clean_user_registry_secrets.find_pod_by_servername")
def test_server_pod_still_pending(
    find_pod_by_servername, secret_list_valid, pod_sample_pending
):
    """Ensure secret is not deleted if server pod is in Pending phase"""
    k8s_client = create_autospec(CoreV1Api)
    find_pod_by_servername.return_value = podname
    k8s_client.list_namespaced_secret.return_value = secret_list_valid
    k8s_client.read_namespaced_pod.return_value = pod_sample_pending
    remove_user_registry_secret(namespace, k8s_client, min_secret_age_hrs)
    k8s_client.list_namespaced_secret.assert_called_once_with(namespace)
    find_pod_by_servername.assert_called_once_with(namespace, servername, k8s_client)
    k8s_client.read_namespaced_pod.assert_called_once_with(podname, namespace)
    assert not k8s_client.delete_namespaced_secret.called


@patch("renku_notebooks.util.clean_user_registry_secrets.find_pod_by_servername")
def test_no_valid_secrets(find_pod_by_servername, secret_list_invalid_type):
    """Ensure that nothing happens if only non-registry secrets are present"""
    k8s_client = create_autospec(CoreV1Api)
    k8s_client.list_namespaced_secret.return_value = secret_list_invalid_type
    remove_user_registry_secret(namespace, k8s_client, min_secret_age_hrs)
    k8s_client.list_namespaced_secret.assert_called_once_with(namespace)
    assert not find_pod_by_servername.called
    assert not k8s_client.read_namespaced_pod.called
    assert not k8s_client.delete_namespaced_secret.called
