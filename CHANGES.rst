Changes
=======

v0.3.0
------

*(released 2018-11-26)*

Chart values need to be migrated from `v0.2.0` -- this essentially amounts to
copying the `jupyterhub` section from renku to the `notebooks` section.

In addition:

* It is no longer needed to specify `jupyterhub_api_token`,
  `jupyterhub_base_url` or `jupyterhub_api_url` as they are derived from the
  corresponding jupyterhub values.
* `gitlab.url`, `gitlab.registry.host` and `gitlab.registry.secret` must be
  specified (the `secret` is needed only for pulling private images).
* A new values section for `server_options` can be configured -- see the
  example in `minikube-values.yaml`.

Server options
^^^^^^^^^^^^^^

This is a configuration that is read by the UI client, rendered as a form for
the user and sent back to the notebooks service as request data. The example
in `values.yaml` or `minikube-values.yaml` sets some reasonable defaults for
`cpu_request`, `mem_request`, `gpu_request`, the `defaultUrl` and
`lfs_auto_fetch`.

If R or other specialized notebooks are used, `defaultUrl` allows the user to
select the default landing path, e.g. `/rstudio`. `lfs_auto_fetch` is *off* by
default, meaning that LFS data is not automatically retrieved.

v0.2.0
------

*(released 2018-09-25)*

Initial release as a part of the larger Renku release. Includes Helm Chart
for deployment and supports simple connection to JupyterHub for launching
notebook servers linked to GitLab repositories.
