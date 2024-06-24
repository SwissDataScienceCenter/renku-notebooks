<!--
 SPDX-FileCopyrightText: 2024 Idiap Research Institute <contact@idiap.ch>
 SPDX-FileContributor: Salim Kayal <salim.kayal@idiap.ch>

 SPDX-License-Identifier: Apache-2.0
 -->

# liveness-detector

This module provides an endpoint to check whether the user is actively using his pod or not

## Installation

In order to kickstart the project ensure [pixi is installed](https://pixi.sh/latest/#installation) as we will be using it for environment and packaging management. Then to install the base dependencies and jupyter kernel for this environment run

```bash
$ pixi install
```

## Testing

running the tests can be achieved by running the following command

```bash
$ pixi run test
```

## Running the server

### shell

Ensure the `PROJECT_SOURCE` environment variable is set then run

```bash
$ pixi run uvicorn liveness_detector:app --port 8888
```

### Docker

build the image with

```bash
$ docker build --target=production --tag=${YOUR_TAG}
```

run it with

```bash
$ docker run -it --rm -v ${YOUR_LOCAL_PROJECT_PATH}:/project:Z -e PROJECT_SOURCE=/project -p 8888:8888
${YOUR_TAG}
```
Connect to it with 

```bash
$ curl -sSL 127.0.0.1:8888/healthz
```

### As an init container

mount the `/renku-liveness` folder in the init container and the environment container and run the
`/entrypoint-init-container.sh` script

then from the environment container, run the `/renku-liveness/entrypoint-hook.sh` with the 8888
port forwarded.

