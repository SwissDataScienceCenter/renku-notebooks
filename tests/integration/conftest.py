import pytest
import os
import json
import base64
from kubernetes.config.incluster_config import (
    SERVICE_CERT_FILENAME,
    SERVICE_TOKEN_FILENAME,
    InClusterConfigLoader,
)


@pytest.fixture(scope="session", autouse=True)
def load_k8s_config():
    InClusterConfigLoader(
        token_filename=SERVICE_TOKEN_FILENAME, cert_filename=SERVICE_CERT_FILENAME,
    ).load_and_set()


@pytest.fixture()
def k8s_namespace():
    return os.environ["KUBERNETES_NAMESPACE"]


@pytest.fixture()
def headers():
    parsed_jwt = {
        "sub": "userid",
        "email": "email",
        "iss": os.environ["OIDC_ISSUER"],
    }
    git_params = {
        os.environ["GITLAB_URL"]: {
            "AuthorizationHeader": f"bearer {os.environ['GITLAB_TOKEN']}"
        }
    }
    headers = {
        "Renku-Auth-Id-Token": ".".join(
            [
                base64.b64encode(json.dumps({}).encode()).decode(),
                base64.b64encode(json.dumps(parsed_jwt).encode()).decode(),
                base64.b64encode(json.dumps({}).encode()).decode(),
            ]
        ),
        "Renku-Auth-Git-Credentials": base64.b64encode(
            json.dumps(git_params).encode()
        ).decode(),
        "Renku-Auth-Access-Token": "test",
    }
    return headers


@pytest.fixture
def base_url():
    return os.environ["NOTEBOOKS_SERVICE_URL"]
