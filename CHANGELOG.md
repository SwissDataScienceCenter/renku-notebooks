# Changelog for renku-notebooks

## [0.8.7](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.6...0.8.7) (2021-02-01)

### Bug Fixes

* **app:** checking secrets with no annotations and labels ([#509](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/509)) ([bfbb148](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/bfbb148f106b9eaf7aab570a7624c5f4a0827fa9))
* **app:** correct order of lfs pull and repo config for git proxy ([#486](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/486)) ([243af69](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/243af6912af438f186897a5dc684e647d26a91a4))
* **app:** duplicate https proxy containers ([#523](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/523)) ([21157dc](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/21157dc646dcef307100f3ddee33f1cc86696d0f))
* **app:** extraEnv requires only string values now ([#511](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/511)) ([2a1bb10](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/2a1bb10c155204e7bdffdc0671478c462ee27ccf))
* **app:** pod resources schema ([#513](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/513)) ([83c844a](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/83c844a1fa90f9f78ba49218b6a523a90bc0dfcc))
* **app:** properly recognize pod status when terminating ([#497](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/497)) ([f59c88f](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/f59c88f17733f572703734366541c744c57c4727))
* **app:** remove unneccessary log error calls ([#512](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/512)) ([d762870](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/d7628704f6bbe88cb97b79089895c587944ea10c))
* **app:** retry when creating notebook fails with 500 ([#518](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/518)) ([8d7799c](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/8d7799c0d373ff1ef40c8784dd7e9fe00d2e8e1f))
* **app:** fix bug in git-https-proxy ([3fc7e18](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/3fc7e184d8fdb032b316779959fc6e60c2c16187))

## [0.8.6](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.5...0.8.6) (2020-12-10)

### Features

* **app:** move gitlab oauth token to separate proxy container ([0488115](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/0488115650ad5d2cab0deaa602662a3d4a4ee0a1))
* **app:** specify image in server request ([95d4f92](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/95d4f922f69020c0d6371862eb5bc90664fb056f))

## [0.8.5](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.4...0.8.5) (2020-11-18)

### Bug Fixes

* fix cull secrets failures with pods forked repos ([559bb91](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/559bb91cf5461df9e0689146dc62811029ab5784))

## [0.8.4](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.3...0.8.4) (2020-10-29)


### Features

* automatically remove user registry secrets ([#435](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/435)) ([334f16b](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/334f16b))

## [0.8.3](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.2...0.8.3) (2020-10-15)

### Features

* **app:** restrict user pod egress ([#430](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/430)) ([f9a6c7a](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/f9a6c7af3a2dfa709fd7ba40e3daca2be4b469d3))

## [0.8.2](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.1...0.8.2)(2020-10-05)

### Bug Fixes

* **app:** escape username in registry secret name ([e960e36](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/e960e363a4c3ec6cee30cfeacde62f5662b64e89))
* **build:** remove build args from chartpress file ([d2feebe](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/d2feebed5f1bf4349e7783981288978e539479df))
* **charts:** correct proxy-public port in ingress ([18f98a2](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/18f98a292d27683ffa3d2197425f26ee7f0cd8fb))
* **charts:** enable storing gitlab auth state per default ([3caeb1e](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/3caeb1e5a12d34e8f76ad1c616f0db0845029e14))

### Features

* **charts:** enable pod autoscaling ([#417](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/417)) ([c9b919a](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/c9b919a55fe15661a07f52d7bfc926e46ea43410))

## [0.8.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.0...0.8.1) (2020-08-28)

### Bug Fixes

* update lfs version in git-clone to handle stored credentials ([c7f017d](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/c7f017d9b3d5012a8165721f30765e7e81bbef05))

## [0.8.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.7.4...0.8.0) (2020-08-11)

### Features

* use user credentials for pulling images for private projects, no more GitLab sudo token needed! ([a172b39](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/a172b39d5d674a9fc3caef3aa7d38a2900b9d2de)), closes [#105](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/105)

* remove user oauth token from repository URL ([5f2ba49](https://github.com/SwissDataScienceCenter/renku-notebooks/pull/346/commits/5f2ba490f3e6bb2e3a0d25f1ce34845685c8de0a)), closes [#313](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/313)

* add support for kubernetes versions > 1.15 ([a994845](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/a994845fbe4d642990ed24ec510794e1eb2a4767))

### Breaking changes

* kubernetes versions < 1.14 are not supported anymore


## [0.7.4](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.7.3...0.7.4) (2020-05-27)

This release contains only dependency updates.


## [0.7.3](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.7.2...0.7.3) (2020-04-29)

### Bug Fixes

* use lowercase image repository names ([3427698](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/3427698240fb657f552f407fdc9c9a5e88223d95)), closes [#287](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/287)


## [0.7.2](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.7.1...0.7.2) (2020-04-24)

### Features

* enable notebooks for logged-out and upriviledged users, closes [#171](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/171) and [#275](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/275).


## [0.7.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.7.0...0.7.1) (2020-03-26)

### Bug Fixes

* use registry API to find image ([7c4b396](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/7c4b39655c714a6facdfae3943152b0416d31b4e)), closes [#273](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/273)


### Features

* add repository url to annoations ([#266](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/266)) ([67b955b](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/67b955bde40b04b6c1e830f4415cf84a2dfc7ca8))
* add requested resources info to servers endpoint ([#261](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/261)) ([9e233cf](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/9e233cf4242c1f6dc537421d35a61d2e4fc025e7)), closes [#223](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/223)
* constrain the container gids ([84066c1](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/84066c17bc2349ea0ad31723bc173cae95b48272))


## [0.7.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.6.2...0.7.0) (2020-03-05)

### Bug Fixes

* Properly handle lfs fetching automation ([#243](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/243)) ([612543a](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/612543aa550d447be3f64f51e794320f5ee789bb)), closes [#227](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/227)


### Features

* **JupyterHub:** update to version 1.1.0 ([db5e876](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/db5e87632c054da2fa63a35572fe5cad516bfb47)), closes [#183](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/183) and [#257](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/257)
* update server logs API to return JSON data ([#225](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/225)) ([e34feaa](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/e34feaad47637e5e2bf62b114ec93c9b13d9c2c6)), closes [#224](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/224)


## [0.6.2](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.6.1...0.6.2) (2019-11-15)


### Bug Fixes

* reference environment starting commit on autosave branches ([#219](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/219)) ([eb79344](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/eb79344))


## [0.6.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.6.0...0.6.1) (2019-11-06)


### Bug Fixes

* Fix library dependency issues. See [#218](https://github.com/SwissDataScienceCenter/renku-notebooks/pull/218)


## [0.6.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.5.1...0.6.0) (2019-10-25)


### Bug Fixes

* check permissions before adding environment variables ([#212](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/212)) ([086a500](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/086a500)), closes [#210](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/210)


### Features

* can force delete pods ([#205](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/205)) ([4d7f2b5](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/4d7f2b5))
* handle k8s api errors when querying for logs ([#216](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/216)) ([397a54b](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/397a54b))
* use project name in the notebook URL ([#211](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/211)) ([e185002](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/e185002))

## [0.5.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.5.0...0.5.1) (2019-08-22)


### Bug Fixes

* do not shorten/modify annotation values ([6159fef](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/6159fef)), closes [#202](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/202)


## [0.5.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.4.0...0.5.0) (2019-08-15)


### Features

* implement new notebook API ([b50ca1c](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/b50ca1c))


## [0.4.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.3.3...0.4.0) (2019-07-09)


### Bug Fixes

* uncaught exception when creating notebooks ([7fdd566](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/7fdd566))
* update registry secret template ([320dcd7](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/320dcd7))
* use local and remote shortened commit-sha to recover from autosaves ([#190](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/190)) ([e1001b5](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/e1001b5))


### Features

* add JUPYTERHUB_USER as env var to git-clone image ([790f92c](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/790f92c))
* pre-stop script also autosaves unpushed commits ([1730d8a](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/1730d8a))
* recover autosave only when branch and commit-sha match ([3cbbcc9](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/3cbbcc9))
* spawn new server for different branch ([9d1a78b](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/9d1a78b)), closes [#90](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/90)



## v0.3.3

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

## v0.3.0

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

## v0.2.0

*(released 2018-09-25)*

Initial release as a part of the larger Renku release. Includes Helm
Chart for deployment and supports simple connection to JupyterHub for
launching notebook servers linked to GitLab repositories.
