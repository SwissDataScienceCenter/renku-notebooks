"""An abstraction over the k8s client and the js-watcher."""

import logging
from time import sleep
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)
from kubernetes.client.exceptions import ApiException
from kubernetes.client.models import V1DeleteOptions

from ...errors.intermittent import (
    IntermittentError,
    CannotStartServerError,
    DeleteServerError,
    JSCacheError,
)
from ...errors.user import MissingResourceError
from ...errors.programming import ProgrammingError


class NamespacedK8sClient:
    def __init__(
        self,
        namespace: str,
        amalthea_group: str,
        amalthea_version: str,
        amalthea_plural: str,
        username_label: str,
    ):
        self.namespace = namespace
        self.amalthea_group = amalthea_group
        self.amalthea_version = amalthea_version
        self.amalthea_plural = amalthea_plural
        self.username_label = username_label
        # NOTE: Try to load in-cluster config first, if that fails try to load kube config
        try:
            InClusterConfigLoader(
                token_filename=SERVICE_TOKEN_FILENAME,
                cert_filename=SERVICE_CERT_FILENAME,
            ).load_and_set()
        except ConfigException:
            config.load_config()
        self._custom_objects = client.CustomObjectsApi(client.ApiClient())
        self._core_v1 = client.CoreV1Api()

    def _get_container_logs(
        self, pod_name: str, container_name: str, max_log_lines: Optional[int] = None
    ) -> Optional[str]:
        try:
            logs = self._core_v1.read_namespaced_pod_log(
                pod_name,
                self.namespace,
                container=container_name,
                tail_lines=max_log_lines,
                timestamps=True,
            )
        except ApiException as err:
            if err.status in [400, 404]:
                return  # container does not exist or is not ready yet
            else:
                raise IntermittentError(
                    f"Logs cannot be read for pod {pod_name}, container {container_name}."
                )
        else:
            return logs

    def get_pod_logs(
        self, name: str, containers: List[str], max_log_lines: Optional[int] = None
    ) -> Dict[str, str]:
        output = {}
        for container in containers:
            logs = self._get_container_logs(
                pod_name=name, container_name=container, max_log_lines=max_log_lines
            )
            if logs:
                output[container] = logs
        return logs

    def get_secret(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            secret = self._core_v1.read_namespaced_secret(name, self.namespace)
        except client.rest.ApiException:
            return None
        return secret

    def create_server(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        server_name = manifest.get("metadata", {}).get("name")
        try:
            server = self._custom_objects.create_namespaced_custom_object(
                group=self.amalthea_group,
                version=self.amalthea_version,
                namespace=self.namespace,
                plural=self.amalthea_plural,
                body=manifest,
            )
        except ApiException as e:
            logging.exception(f"Cannot start server {server_name} because of {e}")
            raise CannotStartServerError(
                message=f"Cannot start the session {server_name}",
            )
        # NOTE: We wait for the cache to sync with the newly created server
        # If not then the user will get a non-null response from the POST request but
        # then immediately after a null response because the newly created server has
        # not made it into the cache. With this we wait for the cache to catch up
        # before we send the response from the POST request out. Wait at most 5s
        # for this to avoid adding too much latency to the response.
        retries = 500
        for _ in range(retries):
            cached_server = self.get_server(server_name)
            if cached_server is not None:
                return cached_server
            sleep(0.01)
        logging.warning(
            f"Timed out waiting for cache sync for server {server_name} creation"
        )
        return server

    def delete_server(self, server_name: str, forced: bool = False):
        try:
            status = self._custom_objects.delete_namespaced_custom_object(
                group=self.amalthea_group,
                version=self.amalthea_version,
                namespace=self.namespace,
                plural=self.amalthea_plural,
                name=server_name,
                grace_period_seconds=0 if forced else None,
                body=V1DeleteOptions(propagation_policy="Foreground"),
            )
        except ApiException as e:
            logging.exception(f"Cannot delete server {server_name} because of {e}")
            raise DeleteServerError()
        return status

    def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific jupyterserver object"""
        try:
            js = self._custom_objects.get_namespaced_custom_object(
                name=name,
                group=self.amalthea_group,
                version=self.amalthea_version,
                namespace=self.namespace,
                plural=self.amalthea_plural,
            )
        except ApiException as err:
            if err.status not in [400, 404]:
                logging.exception(f"Cannot get server {name} because of {err}")
                raise IntermittentError(f"Cannot get server {name} from the k8s API.")
            return
        return js

    def list_servers(self, safe_username: str) -> List[Dict[str, Any]]:
        """Get a list of k8s jupyterserver objects for a specific user."""
        label_selector = f"{self.username_label}={safe_username}"
        try:
            jss = self._custom_objects.list_namespaced_custom_object(
                group=self.amalthea_group,
                version=self.amalthea_version,
                namespace=self.namespace,
                plural=self.amalthea_plural,
                label_selector=label_selector,
            )
        except ApiException as err:
            if err.status not in [400, 404]:
                logging.exception(
                    f"Cannot list servers of user {safe_username} because of {err}"
                )
                raise IntermittentError(
                    f"Cannot list servers for user {safe_username} from the k8s API."
                )
            return []
        return jss.get("items", [])


class JsServerCache:
    def __init__(self, url: str):
        self.url = url

    def list_servers(self, safe_username: str) -> List[Dict[str, Any]]:
        url = urljoin(self.url, f"/users/{safe_username}/servers")
        try:
            res = requests.get(url)
        except requests.RequestException as err:
            logging.warning(f"Jupyter server cache at {url} cannot be reached: {err}")
            raise JSCacheError("The jupyter server cache is not available")
        if res.status_code != 200:
            logging.warning(
                f"Listing servers at {url} from "
                f"jupyter server cache failed with status code: {res.status_code} "
                f"and body: {res.text}"
            )
            raise JSCacheError(
                f"The JSCache produced an unexpected status code: {res.status_code}"
            )
        return res.json()

    def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        url = urljoin(self.url, f"/servers/{name}")
        try:
            res = requests.get(url)
        except requests.exceptions.RequestException as err:
            logging.warning(f"Jupyter server cache at {url} cannot be reached: {err}")
            raise JSCacheError("The jupyter server cache is not available")
        if res.status_code != 200:
            logging.warning(
                f"Reading server at {url} from "
                f"jupyter server cache failed with status code: {res.status_code} "
                f"and body: {res.text}"
            )
            raise JSCacheError(
                f"The JSCache produced an unexpected status code: {res.status_code}"
            )
        output = res.json()
        if len(output) == 0:
            return
        if len(output) > 1:
            raise ProgrammingError(
                f"Expected to find 1 server when getting server {name}, "
                f"found {len(output)}."
            )
        return output[0]


class K8sClient:
    def __init__(
        self,
        js_cache: JsServerCache,
        renku_ns_client: NamespacedK8sClient,
        session_ns_client: NamespacedK8sClient = None,
    ):
        self.js_cache = js_cache
        self.renku_ns_client = renku_ns_client
        self.session_ns_client = session_ns_client

    def list_servers(self, safe_username: str) -> List[Dict[str, Any]]:
        """Get a list of servers that belong to a user. Attempt to use the cache
        first but if the cache fails then use the k8s API."""
        try:
            return self.js_cache.list_servers(safe_username)
        except JSCacheError:
            logging.warning(
                f"Skipping the cache to list servers for user: {safe_username}"
            )
            return self.renku_ns_client.list_servers(safe_username) + (
                self.session_ns_client.list_servers(safe_username)
                if self.session_ns_client is not None
                else []
            )

    def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        """Attempt to get a specific server by name from the cache. If the request
        to the cache fails, fallback to the k8s API."""
        try:
            return self.js_cache.get_server(name)
        except JSCacheError:
            output = []
            res = self.renku_ns_client.get_server(name)
            if res:
                output.append(res)
            if self.session_ns_client is not None:
                res = self.session_ns_client.get_server(name)
                if res:
                    output.append(res)
            if len(output) > 1:
                raise ProgrammingError(
                    "Expected less than two results for searching for "
                    f"server {name}, but got {len(output)}"
                )
            if len(output) == 0:
                return
            return output[0]

    def get_server_logs(
        self, name: str, max_log_lines: Optional[int] = None
    ) -> Dict[str, str]:
        server = self.get_server(name)
        if server is None:
            raise MissingResourceError(
                f"Cannot find server {name} to read the logs from."
            )
        containers = (
            server.get("status", {}).get("containerStates").get("init", {}).keys()
            + server.get("status", {}).get("containerStates").get("regular", {}).keys()
        )
        namespace = server.get("metadata", {}).get("namespace")
        if namespace == self.renku_ns_client.namespace:
            return self.renku_ns_client.get_pod_logs(name, containers, max_log_lines)
        return self.session_ns_client.get_pod_logs(name, containers, max_log_lines)

    def get_secret(self, name: str) -> Optional[Dict[str, Any]]:
        if self.session_ns_client is not None:
            secret = self.session_ns_client.get_secret(name)
        if not secret:
            secret = self.renku_ns_client.get_secret(name)
        return secret

    def create_server(self, manifest: Dict[str, Any]):
        server_name = manifest.get("metadata", {}).get("name")
        server = self.get_server(server_name)
        if server:
            # NOTE: server already exists
            return server
        if not self.session_ns_client:
            return self.renku_ns_client.create_server(manifest)
        return self.session_ns_client.create_server(manifest)

    def delete_server(self, server_name: str, forced: bool = False):
        server = self.get_server(server_name)
        if not server:
            raise MissingResourceError(
                f"Cannot find server {server_name} in order to delete it."
            )
        namespace = server.get("metadata", {}).get("namespace")
        logging.warning(f"Namespace: {namespace}")
        logging.warning(server)
        if namespace == self.renku_ns_client.namespace:
            self.renku_ns_client.delete_server(server_name, forced)
        else:
            self.session_ns_client.delete_server(server_name, forced)

    @property
    def preferred_namespace(self) -> str:
        if self.session_ns_client is not None:
            return self.session_ns_client.namespace
        return self.renku_ns_client.namespace
