# SPDX-FileCopyrightText: 2024 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Salim Kayal <salim.kayal@idiap.ch>
#
# SPDX-License-Identifier: Apache-2.0

FROM ghcr.io/prefix-dev/pixi:0.24.2-bullseye-slim AS build

COPY pixi.lock /app/pixi.lock
COPY pyproject.toml /app/pyproject.toml
COPY liveness_detector /app/liveness_detector
WORKDIR /app

RUN pixi install -e default

RUN <<EOF
echo '#!/bin/bash' > /shell-hook.sh
echo 'export PATH=/app/.pixi/envs/default/bin:${PATH}' >> /shell-hook.sh
echo 'exec "$@"' >> /shell-hook.sh
EOF

FROM docker.io/debian:bullseye-slim AS production

COPY --from=build /app/.pixi/envs/default /app/.pixi/envs/default
COPY --from=build /app/liveness_detector /app/liveness_detector
COPY --chmod=755 --from=build /shell-hook.sh /shell-hook.sh
COPY --chmod=755 scripts/ /
WORKDIR /app
EXPOSE 8888

ENTRYPOINT ["/shell-hook.sh"]

CMD ["uvicorn", "liveness_detector:app", "--port", 8888]
