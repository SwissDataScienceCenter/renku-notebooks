import os
import subprocess
from contextlib import AbstractContextManager


class AttributeDictionary(dict):
    """Enables accessing dictionary keys as attributes"""

    def __init__(self, dictionary):
        for key, value in dictionary.items():
            # TODO check if key is a valid identifier
            if key == "list":
                raise ValueError("'list' is not allowed as a key")
            if isinstance(value, dict):
                value = AttributeDictionary(value)
            elif isinstance(value, list):
                value = [AttributeDictionary(v) if isinstance(v, dict) else v for v in value]
            self.__setattr__(key, value)
            self[key] = value

    def list(self):
        [value for _, value in self.items()]

    def __setitem__(self, k, v):
        if k == "list":
            raise ValueError("'list' is not allowed as a key")
        self.__setattr__(k, v)
        return super().__setitem__(k, v)


class CustomList:
    def __init__(self, *args):
        self.__objects = list(args)

    def list(self):
        return self.__objects

    def items(self):
        return self.__objects

    def get(self, name):
        for i in self.__objects:
            if i.get("name") == name:
                return i


class K3DCluster(AbstractContextManager):
    """Context manager that will create and tear down a k3s cluster"""

    def __init__(self, cluster_name, k3s_image="latest", secrets_mount_image=None):
        self.cluster_name = cluster_name
        self.k3s_image = k3s_image
        self.secrets_mount_image = secrets_mount_image
        self.config_file = ".k3d-config.yaml"
        self.env = os.environ.copy()
        self.env["KUBECONFIG"] = self.config_file

    def __enter__(self):
        """create k3d cluster"""

        create_cluster = [
            "k3d",
            "cluster",
            "create",
            self.cluster_name,
            "--agents",
            "1",
            "--image",
            self.k3s_image,
            "--no-lb",
            "--verbose",
            "--wait",
            "--k3s-arg",
            "--disable=traefik@server:0",
            "--k3s-arg",
            "--disable=metrics-server@server:0",
        ]

        commands = [create_cluster]

        if self.secrets_mount_image is not None:
            upload_image = [
                "k3d",
                "image",
                "import",
                self.secrets_mount_image,
                "-c",
                self.cluster_name,
            ]

            commands.append(upload_image)

        for cmd in commands:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=self.env, check=True)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """delete k3d cluster"""

        cmd = ["k3d", "cluster", "delete", self.cluster_name]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=self.env, check=True)

        return False

    def config_yaml(self):
        with open(self.config_file) as f:
            return f.read()
