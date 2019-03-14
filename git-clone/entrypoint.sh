#!/bin/sh
#
# The entrypoint removes the previous mount-path and does a fresh
# checkout of the repository. It also initializes git lfs and sets
# the proper file permissions.
set -x

if [ "$LFS_AUTO_FETCH" = 1 ]; then LFS_SKIP_SMUDGE="";
else LFS_SKIP_SMUDGE="--skip-smudge";
fi

rm -rf ${MOUNT_PATH}/*
(rm -rf ${MOUNT_PATH}/.* || true)
git lfs install $LFS_SKIP_SMUDGE --system
git clone $REPOSITORY ${MOUNT_PATH}
git lfs install $LFS_SKIP_SMUDGE --local
(git checkout ${BRANCH} || git checkout -b ${BRANCH})
git submodule init && git submodule update
git reset --hard $COMMIT_SHA
git config push.default simple
chown ${USER_ID}:${GROUP_ID} -Rc ${MOUNT_PATH}
