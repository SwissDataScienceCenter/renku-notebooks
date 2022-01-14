from time import sleep

from kubernetes import client
from kubernetes import config as k8s_config

from run_all import parse_args


def adjust_annotations(args):
    k8s_config.load_config()
    k8s_api = client.CustomObjectsApi(client.ApiClient())

    jss = k8s_api.list_namespaced_custom_object(
        group=args.group,
        version=args.api_version,
        namespace=args.namespace,
        plural=args.plural,
    )

    print(
        "Running migration 1: Patching projecName and namespace "
        "in annotations to be lowercarse."
    )
    print(f"Total number of sessions: {len(jss['items'])}")

    annotation_keys = [
        f"{args.prefix}projectName",
        f"{args.prefix}namespace",
    ]
    dry_run_prefix = "DRY RUN: " if args.dry_run else ""

    for js in jss["items"]:
        js_name = js["metadata"]["name"]
        print(f"Checking session {js_name}")
        for annotation_key in annotation_keys:
            annotations = js["metadata"]["annotations"]
            try:
                annotation_val = annotations[annotation_key]
            except KeyError:
                print(f"Annotation {annotation_key} not found in {js_name}.")
                continue
            if annotation_val != annotation_val.lower():
                print(
                    f"{dry_run_prefix}Patching {js_name} for annotation {annotation_key}: "
                    f"{annotation_val} --> {annotation_val.lower()}"
                )
                if not args.dry_run:
                    k8s_api.patch_namespaced_custom_object(
                        group=args.group,
                        version=args.api_version,
                        namespace=args.namespace,
                        plural=args.plural,
                        name=js_name,
                        body={
                            "metadata": {
                                "annotations": {annotation_key: annotation_val.lower()}
                            }
                        },
                    )
            else:
                print(f"No need to patch {js_name} for annotation {annotation_key}")
            sleep(2)


if __name__ == "__main__":
    args = parse_args()
    adjust_annotations(args)
