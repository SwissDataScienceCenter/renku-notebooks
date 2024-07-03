#!/bin/bash
# SPDX-FileCopyrightText: 2024 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Salim Kayal <salim.kayal@idiap.ch>
#
# SPDX-License-Identifier: Apache-2.0

cp -r /app/liveness_detector /renku_liveness
cp -r /app/.pixi /renku_liveness
cp /entrypoint-hook.sh /renku_liveness

echo "listing all files copied"
ls -la /renku_liveness
