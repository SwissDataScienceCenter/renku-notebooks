#!/bin/bash
# SPDX-FileCopyrightText: 2024 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Salim Kayal <salim.kayal@idiap.ch>
#
# SPDX-License-Identifier: Apache-2.0

cd -- "$(dirname "$0")"
.pixi/envs/default/bin/uvicorn liveness_detector:app --port 8888
