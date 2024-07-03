# SPDX-FileCopyrightText: 2024 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Salim Kayal <salim.kayal@idiap.ch>
#
# SPDX-License-Identifier: Apache-2.0


from pathlib import Path
from time import time

from asyncinotify import Inotify, Mask


class ActivityWatcher:
    """
    A class to monitor activity within a directory and surrounding pseudo-terminals.

    This class utilizes inotify to track file system events (create, delete, modify)
    within the workspace directory and additionally monitors access events on pseudo-terminals
    at `/dev/pts`. It maintains the last observed activity timestamp and provides methods
    to add or remove watch descriptors. The class also offers an asynchronous `run` method
    to continuously monitor activity and update the last activity timestamp.

    Attributes
    ----------
      last_activity (float): Timestamp of the last observed activity.
      workdir (str): The directory to monitor for file system events.
    """

    _DIRECTORY_CREATED = Mask.CREATE | Mask.ISDIR
    _DIRECTORY_DELETED = Mask.DELETE | Mask.ISDIR

    def __init__(self, workdir: Path):
        """
        Initialize the ActivityWatcher object.

        Args:
            workdir (str): The directory to monitor for file system events.
        """
        self._last_tty_activity = time()
        self._last_file_activity = time()
        self.workdir = workdir

    @property
    def last_file_activity(self) -> int:
        return int(self._last_file_activity)

    @property
    def last_tty_activity(self) -> int:
        return int(self._last_tty_activity)

    async def run_inotify(self) -> None:
        """
        Continuously monitors activity within the specified directory and pseudo-terminals.

        This asynchronous method utilizes inotify to monitor the configured directory and
        pseudo-terminals. It continuously reads events and updates the `_last_activity`
        timestamp. The method also handles directory creation and deletion events by
        adding or removing watch descriptors accordingly.

        This method should be called as an awaitable coroutine.
        """
        with Inotify() as inotify:
            workdir_mask = Mask.MODIFY | Mask.CREATE | Mask.DELETE

            inotify.add_watch(Path("/dev/pts"), Mask.ACCESS)
            inotify.add_watch(self.workdir, workdir_mask)
            for path_to_monitor, _, _ in self.workdir.walk():
                if path_to_monitor.is_dir():
                    inotify.add_watch(path_to_monitor, workdir_mask)

            async for event in inotify:
                if event.mask & Mask.ACCESS == Mask.ACCESS:
                    self._last_tty_activity = time()
                else:
                    self._last_file_activity = time()
                if event.mask & self._DIRECTORY_CREATED == self._DIRECTORY_CREATED:
                    inotify.add_watch(event.watch.path / event.name, workdir_mask)
                elif event.mask & self._DIRECTORY_DELETED == self._DIRECTORY_DELETED:
                    inotify.rm_watch(event.watch)
