import argparse
import os
import re

import config
import migration_1


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--namespace",
        required=False,
        default=os.environ.get("K8S_NAMESPACE", "default"),
        type=str,
        help="The k8s namespace where to run.",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        required=False,
        help="If set, no changes are made at all.",
    )
    parser.add_argument(
        "-g",
        "--group",
        type=str,
        required=False,
        default=os.environ.get("CRD_GROUP", "amalthea.dev"),
        help="The group for the jupyterserver CRD.",
    )
    parser.add_argument(
        "-a",
        "--api-version",
        type=str,
        required=False,
        default=os.environ.get("CRD_VERSION", "v1alpha1"),
        help="The api version for the jupyterserver CRD.",
    )
    parser.add_argument(
        "-p",
        "--plural",
        type=str,
        required=False,
        default=os.environ.get("CRD_PLURAL", "jupyterservers"),
        help="The plural name for the jupyterserver CRD.",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        required=False,
        default="renku.io/",
        help="The renku k8s annotation prefix.",
    )
    args = parser.parse_args()
    return args


def run_all(args):
    # Run all migrations in order
    print("Starting k8s resource migrations.")
    migration_1.adjust_annotations(args)


if __name__ == "__main__":
    if config.POD_NAME is not None and re.match(r".*-0$", config.POD_NAME) is not None:
        # This is the first pod in the deployment - only that one will run the migrations
        args = parse_args()
        run_all(args)
