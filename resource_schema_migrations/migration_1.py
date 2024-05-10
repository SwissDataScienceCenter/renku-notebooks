"""Migration for projectName and namespace annotations."""

import config
from kubernetes import client
from kubernetes import config as k8s_config
from run_all import parse_args


def adjust_annotations(args):
    """Fix projectName and namespace annotations."""
    k8s_config.load_config()
    k8s_api = client.CustomObjectsApi(client.ApiClient())

    print("Running migration 1: Patching projectName and namespace in annotations to be lowercase.")

    annotation_keys = [
        f"{args.prefix}projectName",
        f"{args.prefix}namespace",
    ]
    next_page = ""
    dry_run_prefix = "DRY RUN: " if args.dry_run else ""

    while True:
        jss = k8s_api.list_namespaced_custom_object(
            version=args.api_version,
            namespace=args.namespace,
            plural=args.plural,
            limit=config.PAGINATION_LIMIT,
            group=args.group,
            _continue=next_page,
            # select only servers that do not have a schema version label
            label_selector=f"!{args.prefix}{config.SCHEMA_VERSION_LABEL_NAME}",
        )

        for js in jss["items"]:
            annotation_patches = {}
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
                    annotation_patches[annotation_key] = annotation_val.lower()
                else:
                    print(f"No need to patch {js_name} for annotation {annotation_key}")

                patch = {
                    "metadata": {
                        "labels": {f"{args.prefix}{config.SCHEMA_VERSION_LABEL_NAME}": "1"},
                    }
                }
                if len(annotation_patches.keys()) > 0:
                    patch["metadata"]["annotations"] = annotation_patches
                if not args.dry_run:
                    k8s_api.patch_namespaced_custom_object(
                        group=args.group,
                        version=args.api_version,
                        namespace=args.namespace,
                        plural=args.plural,
                        name=js_name,
                        body=patch,
                    )

        next_page = jss["metadata"].get("continue")
        if next_page is None or next_page == "":
            break


if __name__ == "__main__":
    args = parse_args()
    adjust_annotations(args)
