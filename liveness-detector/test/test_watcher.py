# SPDX-FileCopyrightText: 2024 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Salim Kayal <salim.kayal@idiap.ch>
#
# SPDX-License-Identifier: Apache-2.0
import asyncio
import subprocess
import threading

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from liveness_detector.activity_watcher import ActivityWatcher


@pytest.fixture(scope="session")
def watcher():
    with TemporaryDirectory() as tmp:
        yield ActivityWatcher(Path(tmp))


async def tty_activity(sleep_time=2):
    await asyncio.sleep(2)
    subprocess.run(["touch", "-a", "/dev/pts/0"])  # noqa s603, s607


async def file_activity(path, sleep_time=2):
    await asyncio.sleep(sleep_time)
    dirpath = path / "mydir"
    dirpath.mkdir()
    filepath = dirpath / "this"
    with filepath.open("w") as file:
        file.write("that")
    filepath.unlink()
    dirpath.rmdir()


async def create_events(path, sleep_time=2):
    await tty_activity(sleep_time)
    await file_activity(path, sleep_time)


@pytest.fixture(scope="session")
def thread(watcher):
    thread = threading.Thread(
        target=asyncio.run, args=(create_events(watcher.workdir),)
    )
    thread.start()
    yield thread
    thread.join()


@pytest.mark.asyncio
async def test_watcher(watcher, thread):
    liveness_file = watcher.last_file_activity
    liveness_pty = watcher.last_tty_activity
    try:
        async with asyncio.timeout(5):
            await watcher.run_inotify()
    except TimeoutError:
        pass
    new_liveness_pty = watcher.last_tty_activity
    new_liveness_file = watcher.last_file_activity
    assert new_liveness_pty - liveness_pty >= 2
    assert new_liveness_file - liveness_file >= 4
