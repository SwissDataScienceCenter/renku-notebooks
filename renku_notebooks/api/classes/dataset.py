from flask import current_app
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import EndpointConnectionError, ClientError, NoCredentialsError


class Dataset:
    def __init__(
        self,
        bucket,
        mount_folder,
        endpoint,
        access_key=None,
        secret_key=None,
        read_only=False,
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self.bucket = bucket
        self.read_only = read_only
        self.public = False
        if self.access_key is None and self.secret_key is None:
            self.public = True
        if self.public:
            self.client = boto3.session.Session().client(
                service_name="s3",
                endpoint_url=self.endpoint,
                config=Config(signature_version=UNSIGNED),
            )
        else:
            self.client = boto3.session.Session().client(
                service_name="s3",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint,
            )
        self.mount_folder = mount_folder

    def get_manifest_patches(
        self, k8s_res_name, k8s_namespace, labels={}, annotations={}
    ):
        secret_name = f"{k8s_res_name}-secret"
        # prepare datashim dataset spec
        dataset_spec = {
            "local": {
                "type": "COS",
                "endpoint": self.endpoint,
                "bucket": self.bucket,
                "readonly": "true" if self.read_only else "false",
            }
        }
        if not self.public:
            dataset_spec["local"]["secret-name"] = f"{secret_name}"
            dataset_spec["local"]["secret-namespace"] = k8s_namespace
        else:
            dataset_spec["local"]["accessKeyID"] = ""
            dataset_spec["local"]["secretAccessKey"] = "secret"
        patch = {
            "type": "application/json-patch+json",
            "patch": [
                # add whole datashim dataset spec
                {
                    "op": "add",
                    "path": f"/{k8s_res_name}",
                    "value": {
                        "apiVersion": "com.ie.ibm.hpsys/v1alpha1",
                        "kind": "Dataset",
                        "metadata": {
                            "name": k8s_res_name,
                            "namespace": k8s_namespace,
                            "labels": labels,
                            "annotations": {
                                **annotations,
                                current_app.config["RENKU_ANNOTATION_PREFIX"]
                                + "mount_folder": self.mount_folder,
                            },
                        },
                        "spec": dataset_spec,
                    },
                },
                # mount dataset into user session
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/0/volumeMounts/-",
                    "value": {
                        "mountPath": self.mount_folder.rstrip("/") + "/" + self.bucket,
                        "name": k8s_res_name,
                    },
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/volumes/-",
                    "value": {
                        "name": k8s_res_name,
                        "persistentVolumeClaim": {"claimName": k8s_res_name},
                    },
                },
            ],
        }
        # add secret for storing access keys for s3
        if not self.public:
            patch["patch"].append(
                {
                    "op": "add",
                    "path": f"/{secret_name}",
                    "value": {
                        "apiVersion": "v1",
                        "kind": "Secret",
                        "metadata": {
                            "name": secret_name,
                            "namespace": k8s_namespace,
                            "labels": labels,
                            "annotations": annotations,
                        },
                        "stringData": {
                            "accessKeyID": self.access_key,
                            "secretAccessKey": self.secret_key,
                        },
                    },
                },
            )
        return patch

    @property
    def bucket_exists(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except (ClientError, EndpointConnectionError, NoCredentialsError):
            current_app.logger.warning(
                f"Failed to confirm bucket {self.bucket} for endpoint {self.endpoint} exists"
            )
            return False
        else:
            return True

    @classmethod
    def datasets_from_js(cls, js):
        datasets = []
        for patch_collection in js["spec"]["patches"]:
            for patch in patch_collection["patch"]:
                if patch["op"] == "test":
                    continue
                if (
                    type(patch["value"]) is dict
                    and patch["value"].get("kind") == "Dataset"
                ):
                    dataset_args = {}
                    dataset_args.update(
                        {
                            "endpoint": patch["value"]["spec"]["local"]["endpoint"],
                            "bucket": patch["value"]["spec"]["local"]["bucket"],
                            "read_only": patch["value"]["spec"]["local"]["readonly"]
                            == "true",
                            "mount_folder": patch["value"]["metadata"]["annotations"][
                                current_app.config["RENKU_ANNOTATION_PREFIX"]
                                + "mount_folder"
                            ],
                        }
                    )
                    if "secret-name" in patch["value"]["spec"]["local"].keys():
                        secret_name = patch["value"]["spec"]["local"]["secret-name"]
                        for patch in patch_collection["patch"]:
                            if (
                                type(patch["value"]) is dict
                                and patch["value"].get("kind") == "Secret"
                                and patch["value"]["metadata"]["name"] == secret_name
                            ):
                                dataset_args.update(
                                    {
                                        "access_key": patch["value"]["stringData"][
                                            "accessKeyID"
                                        ],
                                        "secret_key": patch["value"]["stringData"][
                                            "secretAccessKey"
                                        ],
                                    }
                                )
                        datasets.append(cls(**dataset_args))
        return datasets
