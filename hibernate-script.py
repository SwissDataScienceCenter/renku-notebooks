import logging
import sys
from logging import StreamHandler, FileHandler
from datetime import datetime 
from argparse import ArgumentParser

from kubernetes import config, dynamic
from kubernetes.client import api_client

now = datetime.utcnow()
log_file = f"patching-sessions-log-{now.isoformat()}.txt"
logging.basicConfig(level=logging.INFO, handlers=[StreamHandler(sys.stdout), FileHandler(log_file)])


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Will patch juyterservers to hibernate. "
        "WARNING: The currently active K8s context is used to authenticate.",
    )
    parser.add_argument(
        "-n",
        "--namespace",
        type=str,
        default="renku",
        help="The K8s namespace where Renku is deployed",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="With this flag none of the sessions are patched.",
    )
    parser.add_argument(
        "-f",
        "--only-failing",
        action="store_true",
        help="Hibernate only sessions that are not in a fully ready status.",
    )
    parser.add_argument(
        "-u",
        "--user",
        type=str,
        default=None,
        help="Filter sessions by Keycloak user ID, if omitted run for all users.",
    )
    args = parser.parse_args()
    logging.info(f"Starting with args {args}")

    client = dynamic.DynamicClient(api_client.ApiClient(configuration=config.load_kube_config()))
    js_api = client.resources.get(api_version="amalthea.dev/v1alpha1", kind="JupyterServer")
    label_selector = ""
    if args.user:
        label_selector += f"renku.io/userId={args.user}"
    js_list = js_api.get(
        namespace=args.namespace,
        label_selector=label_selector,
    )
    logging.info(f"Found {len(js_list.items)} total sessions")
    for ijs, js in enumerate(js_list.items):
        js_name: str = js.metadata.name
        logging.info(f"Checking {ijs}/{len(js_list.items)} with name {js_name}")
        starting_since = (
            datetime.fromisoformat(js.status.startingSince).timestamp()
            if js.status.startingSince
            else None
        )
        starting_for_secs = (
            datetime.utcnow().timestamp() - starting_since if starting_since else None
        )
        if js.status.state == "starting" and starting_for_secs > 3600:
            logging.info(f"Preparing to hibernate {js_name}")
            if not args.dry_run:
                js_api.patch(
                    name=js_name,
                    namespace=args.namespace,
                    body={"spec": {"jupyterServer": {"hibernated": True}}},
                    content_type="application/merge-patch+json",
                )
                logging.info(f"{js_name} was successfully hibernated.")
