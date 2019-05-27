Changes
=======

v0.3.3
------

*(released 2019-05-27)*

Bug Fixes
~~~~~~~~~

-  add project id to annotations bef303c, closes #129
-  correct indentation of periodSeconds 07be562, closes #157
-  do not create sentry configmap if no value 41e4993, closes #161
-  do not fail on empty annotations (#133) 373809b, closes #133 #132
-  enforce memory limits for user pods 91f503e, closes #147
-  fix syntax error 1f2088f
-  handle empty authorization token 1d725b7, closes #139
-  remove imageBuildTimeout f26ad81, closes #70
-  return 401 on unauthorized non-browser requests 453e955, closes #115

Features
~~~~~~~~

-  add ConfigMap for pre-stop autosave script (#156) cf6258a, closes
   #156 #137
-  add /servers for user server listing 8d7c177, closes #125
-  added pre-stop post-start hooks (#130) 8b6d7f4, closes #130
-  enable sentry e36ef73, closes #110
-  implement notebook server logs endpoint 66f5793, closes #124
-  include GitLab project variables 50bd6cd


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
