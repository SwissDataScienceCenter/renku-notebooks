# [0.5.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.4.0...0.5.0) (2019-08-15)


### Features

* implement new notebook API ([b50ca1c](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/b50ca1c))


# [0.4.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.3.3...0.4.0) (2019-07-09)


### Bug Fixes

* uncaught exception when creating notebooks ([7fdd566](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/7fdd566))
* update registry secret template ([320dcd7](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/320dcd7))
* use local and remote shortened commit-sha to recover from autosaves ([#190](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/190)) ([e1001b5](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/e1001b5))


### Features

* add JUPYTERHUB_USER as env var to git-clone image ([790f92c](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/790f92c))
* pre-stop script also autosaves unpushed commits ([1730d8a](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/1730d8a))
* recover autosave only when branch and commit-sha match ([3cbbcc9](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/3cbbcc9))
* spawn new server for different branch ([9d1a78b](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/9d1a78b)), closes [#90](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/90)



v0.3.3
------

*(released 2019-05-27)*

### Bug Fixes

-   add project id to annotations bef303c, closes \#129
-   correct indentation of periodSeconds 07be562, closes \#157
-   do not create sentry configmap if no value 41e4993, closes \#161
-   do not fail on empty annotations (\#133) 373809b, closes \#133 \#132
-   enforce memory limits for user pods 91f503e, closes \#147
-   fix syntax error 1f2088f
-   handle empty authorization token 1d725b7, closes \#139
-   remove imageBuildTimeout f26ad81, closes \#70
-   return 401 on unauthorized non-browser requests 453e955, closes
    \#115

### Features

-   add ConfigMap for pre-stop autosave script (\#156) cf6258a, closes
    \#156 \#137
-   add /servers for user server listing 8d7c177, closes \#125
-   added pre-stop post-start hooks (\#130) 8b6d7f4, closes \#130
-   enable sentry e36ef73, closes \#110
-   implement notebook server logs endpoint 66f5793, closes \#124
-   include GitLab project variables 50bd6cd

v0.3.0
------

*(released 2018-11-26)*

Chart values need to be migrated from [v0.2.0]{.title-ref} \-- this
essentially amounts to copying the [jupyterhub]{.title-ref} section from
renku to the [notebooks]{.title-ref} section.

In addition:

-   It is no longer needed to specify
    [jupyterhub\_api\_token]{.title-ref},
    [jupyterhub\_base\_url]{.title-ref} or
    [jupyterhub\_api\_url]{.title-ref} as they are derived from the
    corresponding jupyterhub values.
-   [gitlab.url]{.title-ref}, [gitlab.registry.host]{.title-ref} and
    [gitlab.registry.secret]{.title-ref} must be specified (the
    [secret]{.title-ref} is needed only for pulling private images).
-   A new values section for [server\_options]{.title-ref} can be
    configured \-- see the example in
    [minikube-values.yaml]{.title-ref}.

#### Server options

This is a configuration that is read by the UI client, rendered as a
form for the user and sent back to the notebooks service as request
data. The example in [values.yaml]{.title-ref} or
[minikube-values.yaml]{.title-ref} sets some reasonable defaults for
[cpu\_request]{.title-ref}, [mem\_request]{.title-ref},
[gpu\_request]{.title-ref}, the [defaultUrl]{.title-ref} and
[lfs\_auto\_fetch]{.title-ref}.

If R or other specialized notebooks are used, [defaultUrl]{.title-ref}
allows the user to select the default landing path, e.g.
[/rstudio]{.title-ref}. [lfs\_auto\_fetch]{.title-ref} is *off* by
default, meaning that LFS data is not automatically retrieved.

v0.2.0
------

*(released 2018-09-25)*

Initial release as a part of the larger Renku release. Includes Helm
Chart for deployment and supports simple connection to JupyterHub for
launching notebook servers linked to GitLab repositories.
