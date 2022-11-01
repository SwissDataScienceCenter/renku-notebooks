# K8s-Watcher

K8s-Watcher is a small HTTP server which uses the k8s informer utility from the k8s go client
library. The informer subscribes to updates on the configured custom resource and makes basic listing
and retrieval of the custom resource available via a REST API. The informer utility subscribes to 
k8s events and keeps a cache of all custom resources in the namespaces that are provided in the configuration.


## To run

1. Change your current `kubecontext` to the desired cluster
2. Run the command below with `SERVER_CACHE_NAMESPACES` being a json string of a list of
k8s namespaces where the server resources should be cached.

```bash
SERVER_CACHE_NAMESPACES='["namespace1", "namespace2"]' SERVER_CACHE_CR_GROUP=amalthea.dev SERVER_CACHE_CR_VERSION=v1alpha1 SERVER_CACHE_CR_KIND=jupyterservers SERVER_CACHE_PORT=8000 SERVER_CACHE_USER_ID_LABEL=renku.io/safe-username go run *go
```

3. `curl localhost:8000/servers` should return a json list of all servers in all the namespaces
the cache is watching.

## Notes and limitations

- The server will first look for an in-cluster kubeconfig and will fall back to a
  user's kubeconfig located in their home directory if an in-cluster config cannot
  be found.
- It handles the case in which the connection to the k8s API connection may be
  lost only through the go client informer.
- It does not have proper Go definitions of the `JupyterServer` objects. It only
  knows about the metadata of a resource, everything else is left unmarshalled.
- It only handles a single label filter based on the user's id.
- It stores all resources it watches in memory. This means that at an average size of 30Kb for
  jupyter server it should fit roughly 30,000 jupyter server manifests for 1Gb of memory.
