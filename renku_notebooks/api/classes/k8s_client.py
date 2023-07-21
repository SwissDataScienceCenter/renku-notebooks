"""An abstraction over the k8s client and the k8s-watcher."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from kubernetes import client
from kubernetes.client.exceptions import ApiException
from kubernetes.client.models import V1DeleteOptions
from kubernetes.config import load_config
from kubernetes.config.config_exception import ConfigException
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)

from ...errors.intermittent import (
    CannotStartServerError,
    DeleteServerError,
    HibernateServerError,
    IntermittentError,
    JSCacheError,
    ResumeHibernatedServerError,
)
from ...errors.programming import ProgrammingError
from ...errors.user import MissingResourceError
from ...util.retries import retry_with_exponential_backoff


class NamespacedK8sClient:
    def __init__(
        self,
        namespace: str,
        amalthea_group: str,
        amalthea_version: str,
        amalthea_plural: str,
    ):
        self.namespace = namespace
        self.amalthea_group = amalthea_group
        self.amalthea_version = amalthea_version
        self.amalthea_plural = amalthea_plural
        # NOTE: Try to load in-cluster config first, if that fails try to load kube config
        try:
            InClusterConfigLoader(
                token_filename=SERVICE_TOKEN_FILENAME,
                cert_filename=SERVICE_CERT_FILENAME,
            ).load_and_set()
        except ConfigException:
            load_config()
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
        return output

    def get_secret(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            secret = self._core_v1.read_namespaced_secret(name, self.namespace)
        except client.rest.ApiException:
            return None
        return secret

    def create_server(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        server_name = manifest.get("metadata", {}).get("name")
        try:
            self._custom_objects.create_namespaced_custom_object(
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
        # before we send the response from the POST request out. Exponential backoff
        # is used to avoid overwhelming the cache.
        server = retry_with_exponential_backoff(lambda x: x is None)(self.get_server)(
            server_name
        )
        return server

    def hibernate_server(self, server_name: str, access_token: str):
        from renku_notebooks.config import config

        def get_status() -> Dict[str, Any]:
            hostname = config.sessions.ingress.host  # TODO: Is this always set?
            url = f"https://{hostname}/sessions/{server_name}/sidecar/jsonrpc"
            try:
                response = requests.post(
                    url=url,
                    json={"jsonrpc": "2.0", "id": 0, "method": "git/get_status"},
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                logging.warning(
                    f"RPC call to get git status at {url} from "
                    f"the k8s API failed with status code: {response.status_code} "
                    f"and error: {e}"
                )
                raise HibernateServerError(
                    f"Getting git status produced an unexpected status code: {e}"
                ) from e
            except requests.RequestException as e:
                logging.warning(f"RPC sidecar at {url} cannot be reached: {e}")
                raise HibernateServerError("The RPC sidecar is not available") from e
            else:
                logging.error(f"GOT RESPONSE {response.json()} {response.text}")
                return response.json().get("result", {})

        status = get_status()
        if status:
            dirty = not status.get("clean", True)
            synchronized = status.get("ahead", 0) == status.get("behind", 0) == 0
            hibernation = {
                "branch": status.get("branch"),
                "commit": status.get("commit"),
                "dirty": str(dirty).lower(),
                "synchronized": str(synchronized).lower(),
            }
        else:
            hibernation = {"branch": "", "commit": "", "dirty": "", "synchronized": ""}

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        hibernation["date"] = now

        try:
            status = self._custom_objects.patch_namespaced_custom_object(
                group=self.amalthea_group,
                version=self.amalthea_version,
                namespace=self.namespace,
                plural=self.amalthea_plural,
                name=server_name,
                body={
                    "metadata": {
                        "annotations": {
                            "renku.io/hibernation": json.dumps(hibernation),
                            "renku.io/hibernation-branch": hibernation["branch"],
                            "renku.io/hibernation-commit-sha": hibernation["commit"],
                            "renku.io/hibernation-dirty": hibernation["dirty"],
                            "renku.io/hibernation-synchronized": hibernation[
                                "synchronized"
                            ],
                            "renku.io/hibernation-date": hibernation["date"],
                        },
                    },
                    "spec": {
                        "jupyterServer": {
                            "hibernated": True,
                        },
                    },
                },
            )
        except ApiException as e:
            logging.exception(f"Cannot hibernate server {server_name} because of {e}")
            raise HibernateServerError()

        return status

    def resume_hibernated_server(self, server_name: str):
        try:
            self._custom_objects.patch_namespaced_custom_object(
                group=self.amalthea_group,
                version=self.amalthea_version,
                namespace=self.namespace,
                plural=self.amalthea_plural,
                name=server_name,
                body={
                    "metadata": {
                        "annotations": {
                            "renku.io/hibernation": "",
                            "renku.io/hibernation-branch": "",
                            "renku.io/hibernation-commit-sha": "",
                            "renku.io/hibernation-dirty": "",
                            "renku.io/hibernation-synchronized": "",
                            "renku.io/hibernation-date": "",
                        },
                    },
                    "spec": {
                        "jupyterServer": {
                            "hibernated": False,
                        },
                    },
                },
            )
        except ApiException as e:
            logging.exception(
                f"Cannot resume hibernated server {server_name} because of {e}"
            )
            raise ResumeHibernatedServerError()

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
        """Get a specific JupyterServer object"""
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

    def list_servers(
        self, label_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get a list of k8s jupyterserver objects for a specific user."""
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
                logging.exception(f"Cannot list servers because of {err}")
                raise IntermittentError(
                    f"Cannot list servers from the k8s API with selector {label_selector}."
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
            res.raise_for_status()
        except requests.HTTPError as err:
            logging.warning(
                f"Listing servers at {url} from "
                f"jupyter server cache failed with status code: {res.status_code} "
                f"and error: {err}"
            )
            raise JSCacheError(
                f"The JSCache produced an unexpected status code: {err}"
            ) from err
        except requests.RequestException as err:
            logging.warning(f"Jupyter server cache at {url} cannot be reached: {err}")
            raise JSCacheError("The jupyter server cache is not available") from err
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
        username_label: str,
        session_ns_client: Optional[NamespacedK8sClient] = None,
    ):
        self.js_cache = js_cache
        self.renku_ns_client = renku_ns_client
        self.username_label = username_label
        self.session_ns_client = session_ns_client
        if not self.username_label:
            raise ProgrammingError("username_label has to be provided to K8sClient")

    def list_servers(self, safe_username: str) -> List[Dict[str, Any]]:
        """Get a list of servers that belong to a user. Attempt to use the cache
        first but if the cache fails then use the k8s API."""
        try:
            return self.js_cache.list_servers(safe_username)
        except JSCacheError:
            logging.warning(
                f"Skipping the cache to list servers for user: {safe_username}"
            )
            label_selector = f"{self.username_label}={safe_username}"
            return self.renku_ns_client.list_servers(label_selector) + (
                self.session_ns_client.list_servers(label_selector)
                if self.session_ns_client is not None
                else []
            )

    def get_server(self, name: str, safe_username: str) -> Optional[Dict[str, Any]]:
        """Attempt to get a specific server by name from the cache. If the request
        to the cache fails, fallback to the k8s API."""
        server = None
        try:
            server = self.js_cache.get_server(name)
        except JSCacheError:
            output = []
            res = None
            if self.session_ns_client is not None:
                res = self.session_ns_client.get_server(name)
                if res:
                    output.append(res)
            res = self.renku_ns_client.get_server(name)
            if res:
                output.append(res)
            if len(output) > 1:
                raise ProgrammingError(
                    "Expected less than two results for searching for "
                    f"server {name}, but got {len(output)}"
                )
            if len(output) == 0:
                return
            server = output[0]

        if server:
            if (
                server.get("metadata", {}).get("labels", {}).get(self.username_label)
                != safe_username
            ):
                return
        return server

    def get_server_logs(
        self, server_name: str, safe_username: str, max_log_lines: Optional[int] = None
    ) -> Dict[str, str]:
        server = self.get_server(server_name, safe_username)
        if server is None:
            raise MissingResourceError(
                f"Cannot find server {server_name} for user {safe_username} to read the logs from."
            )
        containers = list(
            server.get("status", {}).get("containerStates", {}).get("init", {}).keys()
        ) + list(
            server.get("status", {})
            .get("containerStates", {})
            .get("regular", {})
            .keys()
        )
        namespace = server.get("metadata", {}).get("namespace")
        pod_name = f"{server_name}-0"
        if namespace == self.renku_ns_client.namespace:
            return self.renku_ns_client.get_pod_logs(
                pod_name, containers, max_log_lines
            )
        return self.session_ns_client.get_pod_logs(pod_name, containers, max_log_lines)

    def get_secret(self, name: str) -> Optional[Dict[str, Any]]:
        if self.session_ns_client is not None:
            secret = self.session_ns_client.get_secret(name)
            if secret:
                return secret
        return self.renku_ns_client.get_secret(name)

    def create_server(self, manifest: Dict[str, Any], safe_username: str):
        server_name = manifest.get("metadata", {}).get("name")
        server = self.get_server(server_name, safe_username)
        if server:
            # NOTE: server already exists
            return server
        if not self.session_ns_client:
            return self.renku_ns_client.create_server(manifest)
        return self.session_ns_client.create_server(manifest)

    def hibernate_server(self, server_name: str, access_token: str, safe_username: str):
        server = self.get_server(server_name, safe_username)
        if not server:
            raise MissingResourceError(
                f"Cannot find server {server_name} for user "
                f"{safe_username} in order to hibernate it."
            )

        # NOTE: Do nothing if server is already hibernated
        if server.get("spec", {}).get("jupyterServer", {}).get("hibernated", False):
            logging.warning(f"Server {server_name} is already hibernated.")
            return

        namespace = server.get("metadata", {}).get("namespace")

        if namespace == self.renku_ns_client.namespace:
            self.renku_ns_client.hibernate_server(
                server_name=server_name, access_token=access_token
            )
        else:
            self.session_ns_client.hibernate_server(
                server_name=server_name, access_token=access_token
            )

    def resume_hibernated_server(self, server_name: str, safe_username: str):
        # NOTE: Try to resume the server if it is hibernated
        server = self.get_server(server_name, safe_username)
        if not server:
            raise MissingResourceError(
                f"Cannot find server hibernated {server_name} for user "
                f"{safe_username} in order to resume it."
            )

        # NOTE: Do nothing if the server isn't hibernated
        if not server.get("spec", {}).get("jupyterServer", {}).get("hibernated", False):
            logging.warning(f"Server {server_name} is not hibernated.")
            return

        namespace = server.get("metadata", {}).get("namespace")

        if namespace == self.renku_ns_client.namespace:
            self.renku_ns_client.resume_hibernated_server(server_name)
        else:
            self.session_ns_client.resume_hibernated_server(server_name)

    def delete_server(self, server_name: str, safe_username: str, forced: bool = False):
        server = self.get_server(server_name, safe_username)
        if not server:
            raise MissingResourceError(
                f"Cannot find server {server_name} for user "
                f"{safe_username} in order to delete it."
            )
        namespace = server.get("metadata", {}).get("namespace")
        if namespace == self.renku_ns_client.namespace:
            self.renku_ns_client.delete_server(server_name, forced)
        else:
            self.session_ns_client.delete_server(server_name, forced)

    @property
    def preferred_namespace(self) -> str:
        if self.session_ns_client is not None:
            return self.session_ns_client.namespace
        return self.renku_ns_client.namespace
