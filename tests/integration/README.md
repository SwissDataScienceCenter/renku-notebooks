# Integration Tests

## Prerequisites 
The following is required in order to run the integrations tests:
- kind
- helm

## Instructions
```bash
# Start kind cluster
kind crate cluster --name test --config kind-config.yaml
# Install notebooks
helm dep update helm-chart/renku-notebooks --kubeconfig kind-config.yaml
helm install --upgrade renku-notebooks helm-chart/renku-notebooks -f values.yaml --kubeconfig kind-config.yaml
# Test notebooks
helm test renku-notebooks --kubeconfig kind-config.yaml
```