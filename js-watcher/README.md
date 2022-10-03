# JS-Watcher

JS-Watcher is a small service which subscribes to updates on Renku
`JupyterServer` custom resources and makes them available via a HTTP API. It
uses the watch mechanism (described
[here](https://kubernetes.io/docs/reference/using-api/api-concepts/#efficient-detection-of-changes))
provided by the Kubernetes API.

The service operates as follows:
- it obtains a list of `JupyterServer` objects from the Kubernetes API
- it stores them in memory in a mutex protected data store
- it creates a http server which serves the list of servers in the data store
- it subscribes to updates on `JupyterServer` objects via the `Watch` mechanism
  - whenever such an update is received, it updates the local data store accordingly 
 
Notes:
- this is not production ready
- it assumes existence of a kubeconfig and will connect to the current context
  defined therein
- it does not have proper Go definitions of the `JupyterServer` objects
  (although this might not in fact be necessary)
- it does not adequately handle the case in which the server connection may be
  lost
- it does not handle any label or annotation filters, but the basic plumbing is
  there which makes this v straightforward to do

