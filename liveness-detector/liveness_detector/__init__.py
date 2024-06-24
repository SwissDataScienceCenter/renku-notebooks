# SPDX-FileCopyrightText: 2024 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Salim Kayal <salim.kayal@idiap.ch>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from os import environ, getloadavg
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from liveness_detector.activity_watcher import ActivityWatcher


class HealthzResponse(BaseModel):
    """
    Represent a health check response containing system and activity information.

    This model is used to structure the response for health check endpoints. It
    provides details about the current system load average (`load_average`), timestamp
    of the last file system activity within a monitored directory (`last_file_activity`),
    and timestamp of the last pseudo-terminal activity (`last_tty_activity`).
    """

    load_average: float
    last_file_activity: int
    last_tty_activity: int


watcher = ActivityWatcher(Path(environ["PROJECT_SOURCE"]))


@asynccontextmanager
async def manage_monitoring(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage the monitoring of the last user activity."""
    task = asyncio.create_task(watcher.run_inotify())
    yield
    task.cancel()


app = FastAPI(lifespan=manage_monitoring)


@app.get("/healthz", response_model=HealthzResponse)
async def is_container_idle() -> HealthzResponse:
    """
    Check container idleness in the background and returns the status.

    Returns
    -------
        JSON response with last activity timestamp.
    """

    return HealthzResponse(
        load_average=getloadavg()[0],
        last_tty_activity=watcher.last_tty_activity,
        last_file_activity=watcher.last_file_activity,
    )
