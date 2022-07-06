# Changelog for renku-notebooks

## [1.9.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.8.3...1.9.0) (2022-07-05)


### Features

* add support for passing env variables to notebooks ([#1131](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1131)) ([9a37728](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/9a377281fa5c500780db2ec6a6e8b6b715d1da17))
* update Amalthea to [0.5.0](https://github.com/SwissDataScienceCenter/amalthea/releases/tag/0.5.0)



## [1.8.3](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.8.2...1.8.3) (2022-06-24)


### Bug Fixes

* **app:** handle endpoints for s3 not on AWS ([#1124](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1124)) ([4922458](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/49224585bc0f910367ed53e3cb141c5bd3505fa5))
* **app:** list autosaves only for the current user ([#1118](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1118)) ([d67d8ad](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/d67d8addcee839dd09c6ea04aa1c1a4d90be0567))



## [1.8.2](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.8.1...1.8.2) (2022-06-21)


### Bug Fixes

* **app:** cloudstorage in server_options schema ([#1113](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1113)) ([38904f9](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/38904f9dfb2cf191a99a6e1e3dde79d652dae8bd))
* **app:** parse unschedulable resources message ([#1114](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1114)) ([7457538](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/7457538edcd264cb5f16459f71ae8dc93b16efe2))



## [1.8.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.8.0...1.8.1) (2022-06-15)


### Bug Fixes

* **app:** no main pod in status when getting logs ([#1104](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1104)) ([561d447](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/561d447dd24b3cead524ed20c1ae9e61dba8b057))
* **app:** properly deserialize server options ([#1108](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1108)) ([1b7ae18](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/1b7ae185bebf5dbafe9927a26cf4022a2466a726))



## [1.8.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.7.0...1.8.0) (2022-06-13)


### Bug Fixes

* **app:** handle missing project in autosave list ([#1090](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1090)) ([ea7667f](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/ea7667fa7e35f3a17308c0b03b30f2965def9a19))
* **app:** s3 bucket location ([#1083](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1083)) ([a23e53f](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/a23e53f24674b802372b97d7e44722b676dd1cce))
* **app:** show starting message ([#1099](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1099)) ([2c56b17](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/2c56b17adc8f878254a92a9247386d0e73cd6e34))
* **app:** custom certs env variables in git clone ([#1101](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1101)) ([ad10f71](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/ad10f71ee4a1ed33a02dbdbfb38aad8868a5b9ea))
* **app:** serialize cpu and gpu request to number ([#1103](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1103)) ([77aadd5](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/77aadd53e0537fcea7702b7223b661058d6041fe))


### Features

* add git error codes to notebooks response ([#1055](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1055)) ([dd59afe](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/dd59afe59d32fed8c95be80676cfb2562f7a78e9)), closes [#1064](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1064)
* **app:** show session resource usage ([#968](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/968)) ([84e8035](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/84e8035d206143e5d8cbcaf1e6d6f38ccd3e7fd7))
* **app:** surface message and status when pod is unschedulable ([#1088](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1088)) ([a6cf716](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/a6cf716f2b91b59624c58528c8221d285a1a282b))
* **app:** update Amalthea to version 0.4.0



## [1.7.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.6.2...1.7.0) (2022-05-16)


### Bug Fixes

* **app:** eliminate unnecessary gitlab calls ([#1035](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1035)) ([3ff58d5](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/3ff58d52e1ed0e09a07a74c0adde74408c5e04ae))
* **app:** keep git-proxy alive on session shutdown ([#951](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/951)) ([7589230](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/758923031465ff0e492bcd401fdbb33b0cbedb0e))


### Features

* **app:** switch git proxy to golang ([#993](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/993)) ([3f0f965](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/3f0f96514c71eff4f0a9d5f16263a29ae3e4ce87))
* **app:** update Amalthea to version 0.3.0

### Breaking changes

The value `securityContext.enabled` in the notebook service `values.yaml` used to be used in 
much older versions and has since been deprecated. However, it may still be present in your `values.yaml` file. 
If this is the case it will cause problems when deploying because with this release the 
`securityContext` field is directly added as the security context for every container in the notebook 
service. You can correct this by simply removing this field from your values file along with its parent 
`securityContext` field, this will make the notebook service use the default security context which functions properly.

## [1.6.2](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.6.1...1.6.2) (2022-04-08)

### Bug Fixes

* **chart:** revert the removal of bash autosave script ([#1011](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1011)) ([2f6f353](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/2f6f35354ca6d3f26f8d2f15b0b6816f22c19a2b))

## [1.6.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.6.0...1.6.1) (2022-04-06)

### Bug Fixes

* **app:** handle user names in git clone ([#1006](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1006)) ([e5c5874](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/e5c58743b4d022ff139cae423994ad951d05d819))

## [1.6.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.5.1...1.6.0) (2022-04-05)

### Features

* **app:** add endpoint to verify docker image availability ([#990](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/990)) ([e1a9f73](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/e1a9f7347524dc9ca45949743ec60ad14f332127))
* **app:** add sentry to git clone and autosaves ([#963](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/963)) ([7d73cad](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/7d73cadcdbf09b0564b0430277694afd6a59a1f7))
* **app:** use python for git clone and autosaves ([#956](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/956)) ([e5a86eb](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/e5a86eb5a2b4a05c5167556e029a3d98ec84423f))

## [1.5.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.5.0...1.5.1) (2022-03-18)

### Bug Fixes

* **app:** enable s3 flag in server options ([#969](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/969)) ([18787aa](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/18787aa69975d0867f84cff2fcaca330340fefa9))

## [1.5.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.4.1...1.5.0) (2022-03-15)

### Features

* **app:** better messages on session launch fail (#923) ([a8636e3](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/a8636e35210e4b7499ec8ba9bf847d0b63887481)), closes [#923](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/923)
* **app:** return logs from all containers ([#887](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/887)) ([3defae5](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/3defae5ca4a441f85d16b16a10106bbfc261c23d))
* **app:** version endpoint ([#938](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/938)) ([4c2b26d](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/4c2b26dd6086a466cffa245a56f9fab6fb7ea4a2))

### BREAKING CHANGES

* The status of the session is reported in a different more compact form in the API. This affects the `/servers` or `/servers/<server_name>` endpoints.
* The logs from all containers in the session (including init containers) are returned, not just the logs from the `jupyter-server` container. This affects the `/notebooks/logs/<server_name>` endpoint.
* The logs from `/notebooks/logs/<server_name>` are returned as a dictionary of strings where the key is the container name and the string is the log.

## [1.4.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.4.0...1.4.1) (2022-02-18)

### Bug Fixes

* **app:** remove S3 flag from server options ([#940](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/940)) ([a2768d6](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/a2768d6e240c0f8e64841821f7caf4cda09f3750))

## [1.4.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.3.0...1.4.0) (2022-02-15)

### Features

* **chart:** add anti-affinity to stateful set ([#915](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/915)) ([67b3b80](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/67b3b807f7ccaaf47141c92eed047f37d6a387c0))

### Bug Fixes

* **app:** modify terminology for mounting S3 buckets ([#922](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/922)) ([9f93dcf](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/9f93dcff42015dbde398e16f61bfae7d9dcdbbf6))
* **chart:** allow mounting of S3 buckets to be enabled without installing Datashim ([#922](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/922)) ([9f93dcf](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/9f93dcff42015dbde398e16f61bfae7d9dcdbbf6))

### Breaking changes

The impact of the following breaking changes is minor because they only affect deployments that mount S3 buckets in user sessions. However as this is an experimental feature that was released very recently (and is turned off by default) it is very unlikely that any users are affected by this. Only users who have enabled S3 bucket mounting in sessions in `1.3.0` and are using this will be affected by this change.

* the API endpoints that start user sessions or list them use `cloudstorage` in their request/response schemas rather than `s3mounts`
* the values for the Helm chart related to mounting S3 buckets have also changed to use `cloudstorage` instead of `s3mounts`, and the setupt for mounting S3 buckets can be found under `cloudstorage.s3`

## [1.3.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.2.1...1.3.0) (2022-02-08)

### Bug Fixes

* **app:** case insensitive project and namespace ([#858](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/858)) ([56c2db4](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/56c2db49b42b6713ce83a29d65cc0410acbea87d))
* **app:** do not accept an empty anonymous user id ([#845](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/845)) ([0fa71df](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/0fa71df327467c0b5da35d8d14190f42efd14280))
* **app:** return proper values for image and repository ([#834](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/834)) ([39a6d96](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/39a6d960edeca152dd0cbe0c7b92c4eebda4c31b))

### Features

* **app:** enable age-based session culling ([#848](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/848)) ([b92722d](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/b92722d0c7485460b7eb842c3bf09ff483e8b303))
* **chart:** modify for custom CA certificates ([#788](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/788)) ([1a7f15c](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/1a7f15c676abb1c3e42e346ab84c8f10a8b98242))
* **app:** mount s3 buckets in sessions ([#729](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/729)) ([808e767](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/808e7675dd6d3b4f23ea503be0251bba1150bbac))
* Upgrade Amalthea to 0.2.3

## [1.2.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.2.0...1.2.1) (2021-12-01)

### Bug Fixes

* **app:** apply CPU limits to user sessions ([#826](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/826)) ([29d44a2](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/29d44a28b850bbbd8155e02eae0dbdc7bed642b2))
* **app:** do not delete autosaves before restoring ([#814](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/814)) ([32f6c5e](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/32f6c5e6aba26881a85d5a8d8c1971becec17827))
* **app:** use 3 scenarios for session cpu limits ([#828](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/828)) ([ff7899d](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/ff7899d04d028f75734c1af5df7390289e6f3745))
* **app:** use pyjwt to decode token ([#818](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/818)) ([4987db1](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/4987db191c5faf2f2f5a44600f6cf4e1b15fea1c))
* **app:** user not authenticated and anonymous sessions not allowed ([#829](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/829)) ([edb9c03](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/edb9c03dc38e67a2d8c9a8b593e72c02f18d7d53))

## [1.2.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.1.1...1.2.0) (2021-11-15)

### Bug Fixes

* **app:** check out the correct branch instead of always master([#802](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/802)) ([5a9ffbe](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/5a9ffbeed0ae299e10f35b35d9ada34069d00e97))
* **chart:** use current fallback renku image ([#803](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/803)) ([30df71b](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/30df71bf98f6635bb90552a5944148fb245a2f51))

### Features

* **chart:** add session tolerations, affinity, nodeSelector ([#806](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/806)) ([49a2d54](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/49a2d545bd041b2e4342093bb578ad8305b66a5e))
* **app:** new Amalthea version - 0.2.1

## [1.1.1](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.1.0...1.1.1) (2021-11-08)

### Bug Fixes

* add ingress annotation to each session so iframes work ([#794](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/794)) ([f854d34](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/f854d3491de8bead044ae61e9c0d53c74e19927b))

## [1.1.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/1.0.0...1.1.0) (2021-11-02)

### Bug Fixes

* **app:** displaying gpu resources in API responses ([#786](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/786)) ([6784504](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/6784504a92b290e5b7c4d0a1441200f765c3f542))
* **app:** use the right storage class name parameter in Jupyter server manifest ([#769](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/769)) ([0481561](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/0481561255856fd33cb37860d3e3a9d157ea372f))
* **app:** when a gitlab project does not exist log a warning instead of error ([#763](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/763)) ([ce7af2a](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/ce7af2a7a558f2886432acdf86c5f389bcd97bfc))

### Features

* **app:** option to not limit size of user session emptyDir ([#785](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/785)) ([3a0eae8](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/3a0eae88ec0e737b71baee10ddce8801592d78e8))

## [1.0.0](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.18...1.0.0)  (2021-09-16)

### Features

* **app** use Amalthea to run sessions through a K8s operator ([#668](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/668)) ([f808ac0](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/f808ac03f4431bda1817096862431de1c3648786))

### Breaking changes

* The use of Amalthea and removal of Jupyterhub will require some changes. Namely:
  - All references to Jupyterhub in the `values.yaml` have been removed and are not required anymore.
  - Amalthea is installed from a separate helm chart which is now a dependency of the `renku-notebooks` helm chart.
  - Several new sections have been added to the `values.yaml` file which are required by Amalthea. These include `amalthea`, `oidc`, `sessionIngress`, `culling` and `tests`.
* Some older images with Rstudio will open Rstudio in a directory one level above the repository. This can be fixed by upgrading to a newer version of the base image in the Dockerfile in the relevant renku project.
* This version is not backward compatible with the user sessions from older versions. Therefore before deploying the admin should notify users to save their work and shut down all active sessions. During the deployment the admin should clean up all remaining user sessions and then deploy this version. 

## [0.8.18](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.17...0.8.18) (2021-08-11)

### Bug Fixes

* **app:** bugs with mistyped variable and missing branches in autosaves ([#723](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/723)) ([cebb39d](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/cebb39dafb0c95a77d28a4def83791ab4b4f0478))
* **app:** listing sessions when a project has been deleted ([#718](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/718)) ([2c65ede](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/2c65ede8216aee1614eb86629eb4373a8df1e55d))

## [0.8.17](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.16...0.8.17) (2021-07-29)

### Bug Fixes

* **app:** fix failing on pvcs created with old 0.8.4 renku verison pvc naming ([fb7e318](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/fb7e318dbcd7c11f1a0e723a5c1784e0a441f8d1))

## [0.8.16](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.15...0.8.16) (2021-07-28)

### Bug Fixes

* **app:** upper case letters in pvc name ([f6cfb8b](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/f6cfb8b4716e75ddb6261918dc917e5f57a6cc65))

## [0.8.15](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.14...0.8.15) (2021-07-23)

### Bug Fixes

* **app:** properly display storage ([#708](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/708)) ([9aa1df6](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/9aa1df6225cc41b7056fc7cb4230e15f46fb83db))

## [0.8.14](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.13...0.8.14) (2021-07-09)

### Features
* **app:** add autosave delete endpoint ([e2f1538](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/e2f1538c323639b5dd544cd4b01966af35ecd0bf))

### Bug Fixes

* **app:** git-https-proxy/Dockerfile to reduce vulnerabilities ([#664](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/664)) ([092703d](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/092703d749e97c8c26de2b45d819a7300f45191d))
* **app:** properly assign default server option values ([#649](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/649)) ([eda1685](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/eda1685a85f45807da0e6918e8fb7b77876aabce))

## [0.8.13](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.12...0.8.13)  (2021-05-14)

### Bug Fixes

* clusterrole is not required for user session PVCs ([#641](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/641)) ([752ca3f](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/752ca3fa84c3b7fb88a9e483bf6cbda55c952bb7))
* remove disk request values ([#657](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/657)) ([33d6251](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/33d6251f9505435db8b04ef3ae26aaf815427821))

### Features

* cleanup PVS and autosave branches ([#611](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/611)) ([f1510fd](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/f1510fd883422782da91ee32afdcc52245d80028))

## [0.8.12](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.11...0.8.12) (2021-04-16)

### Bug Fixes

* **app:** missing annotations handling in marshmallow ([23e54b0](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/23e54b06620b341000fde4b7f5917284e8a17bf0))

### Features

* endpoint for autosave information ([#607](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/607)) ([5370a13](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/5370a13))

## [0.8.11](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.10...0.8.11) (2021-04-15)

### Bug Fixes

* **app:** increase huboauth caching from 1min to 5min ([#603](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/603)) ([1e459cc](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/1e459cc6afbabba0ee62a6731c8bc6ecff7b3ab0))
* **app:** unset lfs auth mode in init container ([c2017ca](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/c2017ca0d220ef52479df39595fca8049bb59870))

### Features

* **app:** use pvs for user sessions ([#573](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/573)) ([9842fc9](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/9842fc9b3e4642365447e8cc335f918835fad125))

# [0.8.10](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.9...0.8.10) (2021-03-08)


### Bug Fixes

* **app:** image pull secret for pod restart ([#556](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/556)) ([afe92f9](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/afe92f993caf10e534c5c6f715b9998f3348b7fc))
* **app:** support for long project title ([#553](https://github.com/SwissDataScienceCenter/renku-notebooks/pull/553)) ([44d9578](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/44d957896d4623e2c362751e1f6cee08029992a4))

### Improvements

* **build:** switch to debian-based image ([ad5adff](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/ad5adffa0f4119225c08d11d942b13f5b2f01ed1))
* **build:** update dependencies, including a vulnerability patch ([#547](https://github.com/SwissDataScienceCenter/renku-notebooks/pull/544)) ([a5becee](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/a5beceeb2df3c9681b6bdb6870c44d345c41ce7f))

# [0.8.9](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.8...0.8.9) (2021-02-11)


### Bug Fixes

* **app:** add label for hub network policy selector ([#547](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/547)) ([a90ff26](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/a90ff267d24dfd02619dfa284c7e97c13b924723))
* **app:** allow unknown annotations in schema ([#546](https://github.com/SwissDataScienceCenter/renku-notebooks/pull/546)) ([5d3bcb9](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/5d3bcb9a09934f95f76f0f568798db9e4be8757f))
* **app:** allow to launch notebooks using defaultUrl ([#542](https://github.com/SwissDataScienceCenter/renku-notebooks/pull/542)) ([534b04c](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/534b04c46087914b14195f537019a00489bcf32b))



# [0.8.8](https://github.com/SwissDataScienceCenter/renku-notebooks/compare/0.8.7...0.8.8) (2021-02-05)


### Bug Fixes

* **app:** unknown gpu field in resources request ([#538](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/538)) ([4fc9215](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/4fc9215ffe49a40e6e9edbc1fd81618aef53e48e))
* **app:** validate server options ([#529](https://github.com/SwissDataScienceCenter/renku-notebooks/issues/529)) ([03d20e2](https://github.com/SwissDataScienceCenter/renku-notebooks/commit/03d20e2206122820146feee2ee61d625c6689fe6))


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
