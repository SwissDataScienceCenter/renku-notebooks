import os

import escapism
from flask import request, current_app
import gitlab
from jupyterhub.services.auth import HubOAuth
import json
import requests

from ...util.kubernetes_ import get_k8s_client


class User:
    def __init__(self):
        self.auth = HubOAuth(
            api_token=os.environ.get("JUPYTERHUB_API_TOKEN", "token"), cache_max_age=60
        )

    @property
    def gitlab(self):
        return gitlab.Gitlab(
            os.environ.get("GITLAB_URL"), api_version=4, oauth_token=self.oauth_token
        )

    @property
    def prefix(self):
        return self.auth.api_url

    @property
    def headers(self):
        return {self.auth.auth_header_name: f"token {self.auth.api_token}"}

    @property
    def user(self):
        token = (
            request.cookies.get(self.auth.cookie_name)
            or request.headers.get("Authorization", "")[len("token") :].strip()
        )
        if token:
            _user = self.auth.user_for_token(token)
        else:
            _user = None
        return _user

    @property
    def safe_username(self):
        return escapism.escape(self.user.get("name"), escape_char="-").lower()

    @property
    def user_info(self):
        response = requests.get(
            f"{self.prefix}/users/{self.user['name']}", headers=self.headers
        )
        return json.loads(response.text)

    @property
    def oauth_token(self):
        """Retrieve the user's GitLab token from the oauth metadata."""
        auth_state = self.user_info.get("auth_state", None)
        return None if not auth_state else auth_state.get("access_token")

    @property
    def pods(self):
        k8s_client, k8s_namespace = get_k8s_client()
        pods = k8s_client.list_namespaced_pod(
            k8s_namespace,
            label_selector=f"heritage=jupyterhub,renku.io/username={self.safe_username}",
        )
        return pods.items

    def get_renku_project(self, namespace_project):
        """Retrieve the GitLab project."""
        try:
            return self.gitlab.projects.get("{0}".format(namespace_project))
        except Exception as e:
            current_app.logger.error(
                f"Cannot get project: {namespace_project} for user: {self.user['name']}, error: {e}"
            )
