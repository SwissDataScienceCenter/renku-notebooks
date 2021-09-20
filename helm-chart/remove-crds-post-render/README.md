# Remove Datashim CRDs

This sets up a simple Helm post-renderer to remove the CRDs from the
Datashim helm chart. There is no option in the helm chart to not include these
in the installation.

To use this post-renderer:
```
cd helm-chart/remove-crds-post-render
helm upgrade --install renku-notebooks ../renku-notebooks --post-renderer post-renderer-hook.sh -f <values.yaml>
```
