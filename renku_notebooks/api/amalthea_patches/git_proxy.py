import base64
from flask import current_app

from ..classes.user import RegisteredUser
from .utils import get_certificates_volume_mounts


def main(server):
    etc_cert_volume_mount = get_certificates_volume_mounts(
        custom_certs=False,
        etc_certs=True,
        read_only_etc_certs=True,
    )
    encoded_token = base64.b64encode(
        f"oauth2:{server._user.git_token}".encode("utf-8")
    ).decode("ascii")
    patches = []

    health_check_config = """
server {
    listen 8081;
    location /health {
        add_header 'Content-Type' 'application/json';
        return 200 '{"status":"UP"}';
    }
}
    """

    anonymous_proxy_config = """
server {
    listen 8080;
    location / {
        proxy_pass $scheme://$http_host$uri$is_args$args;
    }
}
    """

    registered_proxy_config = """
map $scheme://$http_host$uri $auth {{
    default '';
    ~^{} 'Basic {}';
}}
server {{
    listen 8080;
    resolver                       8.8.8.8;
    proxy_connect;
    proxy_connect_allow            443 563;
    proxy_connect_connect_timeout  10s;
    proxy_connect_read_timeout     10s;
    proxy_connect_send_timeout     10s;
    location / {{
        proxy_pass http://$host;
        proxy_set_header Host $host;
    }}
}}
    """.format(
        server.gl_project.http_url_to_repo, encoded_token
    )

    nginx_config = f"{health_check_config}"
    if type(server._user) is RegisteredUser:
        nginx_config += "\n" + registered_proxy_config
    else:
        nginx_config += "\n" + anonymous_proxy_config

    patches.append(
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/secret/data/git-proxy-nginx-config",
                    "value": base64.b64encode(
                        nginx_config.encode("utf-8")
                    ).decode("ascii"),
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/-",
                    "value": {
                        "image": current_app.config["GIT_HTTPS_PROXY_IMAGE"],
                        "name": "git-proxy",
                        "livenessProbe": {
                            "httpGet": {"path": "/health", "port": 8081},
                            "initialDelaySeconds": 3,
                        },
                        "readinessProbe": {
                            "httpGet": {"path": "/health", "port": 8081},
                            "initialDelaySeconds": 3,
                        },
                        "volumeMounts": [
                            *etc_cert_volume_mount,
                            {
                                "name": "git-proxy-nginx-config",
                                "readOnly": True,
                                "mountPath": "/opt/bitnami/nginx/conf/server_blocks/git-proxy.conf",
                                "subPath": "git-proxy-nginx-config",
                            },
                        ],
                    },
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/volumes/-",
                    "value": {
                        "name": "git-proxy-nginx-config",
                        "secret": {
                            "secretName": server.server_name,
                        },
                    },
                },
            ],
        }
    )
    return patches
