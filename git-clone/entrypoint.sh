#!/bin/bash -x
#

REMOTES_ORIGIN="remotes/origin/"
AUTOSAVE_BRANCH_PREFIX="renku/autosave/$JUPYTERHUB_USER"

# extract the GitLab host and path
pat='^(http[s]?:\/\/)([^\/]+)\/?([a-zA-Z0-9_\/\-]+?)$'
[[ $GITLAB_URL =~ $pat ]]
GITLAB_HOST="${BASH_REMATCH[2]}"
GITLAB_PATH="${BASH_REMATCH[3]}"

# if the PVC was already created before, do not touch it and exit!
if [ "$PVC_EXISTS" = "True" ]; then
  git config --unset http.proxy
  git config --unset http.sslVerify
  git config credential.helper "store --file=.git/credentials"
  echo "https://oauth2:${GITLAB_OAUTH_TOKEN}@${GITLAB_HOST}" > .git/credentials
  git fetch origin

  # Note that the () turn the output into an array.
  ALL_BRANCHES=(`git branch -a `)
  echo "PVC already exists, checking for matching autosave branches to delete..."

  for branch in "${ALL_BRANCHES[@]}"
  do
    # It's not scrictly impossible that we will have more than one branch matching
    # here, but RenkuLab should prevent users from creating more than one autsave
    # branch per user/branch/commmit tuple.
    if [[ $branch == *"${REMOTES_ORIGIN}${AUTOSAVE_BRANCH_PREFIX}/${BRANCH}/${COMMIT_SHA:0:7}"* ]] ; then
        AUTOSAVE_REMOTE_BRANCH=${branch// /}
        break
    fi
  done
  # If autosave branch is found delete it since pvc was used to recover
  if [ ! -z "$AUTOSAVE_REMOTE_BRANCH" ] ; then
  echo "PVC is used to recover work, deleteing autosave branch $AUTOSAVE_REMOTE_BRANCH"
    git push -d origin $(echo $AUTOSAVE_REMOTE_BRANCH | sed "s/^remotes\/origin\///")
  fi

  git config http.proxy http://localhost:8080
  git config http.sslVerify false
  git config --unset credential.helper
  rm .git/credentials
  git config --unset lfs.${REPOSITORY}/info/lfs.access || true
  exit 0
fi

# If we are setting up a new volume, remove the previous mount-path and
# do a fresh checkout of the repository. Also initialize git lfs and set
# the proper file permissions.

# clear path
rm -rf ${MOUNT_PATH}/*
(rm -rf ${MOUNT_PATH}/.* || true)

# set up git defaults
git config --system push.default simple

# set up the repo
mkdir -p $MOUNT_PATH
cd $MOUNT_PATH
git init
git lfs install --local --skip-smudge
git config credential.helper "store --file=.git/credentials"
echo "https://oauth2:${GITLAB_OAUTH_TOKEN}@${GITLAB_HOST}" > .git/credentials
git remote add origin $REPOSITORY
git fetch origin
git checkout ${BRANCH} || git checkout -b ${BRANCH}
git submodule init && git submodule update

# If this option is set, try to recover from a relevant autosave branch.
if [ "${GITLAB_AUTOSAVE}" == "1" ] ; then

  # Go through all available branches and find the appropriate autosave branch.
  # Note that the () turn the output into an array.
  ALL_BRANCHES=(`git branch -a `)
  for branch in "${ALL_BRANCHES[@]}"
  do
    # It's not scrictly impossible that we will have more than one branch matching
    # here, but RenkuLab should preven users from creating more than one autsave
    # branch per user/branch/commmit tuple.
    if [[ $branch == *"${REMOTES_ORIGIN}${AUTOSAVE_BRANCH_PREFIX}/${BRANCH}/${COMMIT_SHA:0:7}"* ]] ; then
        AUTOSAVE_REMOTE_BRANCH=${branch// /}
        break
    fi
  done

  # If no autosave branch was found, simply reset to the selected commit.
  if [ -z "$AUTOSAVE_REMOTE_BRANCH" ] ; then
    echo "No autosave branch was found"
    git reset --hard $COMMIT_SHA
  else
    echo "Restoring autosave branch $AUTOSAVE_REMOTE_BRANCH"
    IFS='/' read -r -a AUTOSAVE_REMOTE_BRANCH_ITEMS <<< "$AUTOSAVE_REMOTE_BRANCH"

    # Check if the found autosave branch has a valid format, fail otherwise
    if [ "${#AUTOSAVE_REMOTE_BRANCH_ITEMS[@]}" -lt 7 ] ; then
      echo "Auto-save branch is in the wrong format; cannot recover the state from that branch" >&2
      return 1
    fi

    # Reset the file tree to the auto-saved state.
    git reset --hard $AUTOSAVE_REMOTE_BRANCH

    # Reset HEAD to the last committed change prior to the autosave commit.
    PRE_SAVE_LOCAL_COMMIT_SHA=${AUTOSAVE_REMOTE_BRANCH_ITEMS[7]}
    git reset --soft $PRE_SAVE_LOCAL_COMMIT_SHA

    # Unstage all modified files.
    git reset HEAD .

    # Delete the autosave branch both remotely and locally.
    AUTOSAVE_LOCAL_BRANCH=${AUTOSAVE_REMOTE_BRANCH/$REMOTES_ORIGIN/''}
    git push origin :"$AUTOSAVE_LOCAL_BRANCH"
  fi
fi

# Configure the repo such that the git client will communicate with GitLab
# through the https proxy.
# Note: The proxy will still verify the certificates of the connection to the git server.
git config http.proxy http://localhost:8080
git config http.sslVerify false
git config --unset credential.helper
rm .git/credentials
git config --unset lfs.${REPOSITORY}/info/lfs.access || true

# Finally, set the correct permissions for the main container.
chown ${USER_ID}:${GROUP_ID} -Rc ${MOUNT_PATH}

# Setup git LFS to properly auto fetch if requested by the user.
# If autofetch is requested try to fetch here at the end of the script.
# Fetching LFS objects at the end will prevent the script crashing during the execution
# of other commands and resulting in an incomplete repository for the user
if [ "$LFS_AUTO_FETCH" = 1 ]; then
  git lfs install --local
  git lfs pull
fi

DISK_USAGE=$(df -h ./ | tail -1 | awk '{print $5}')
if [ "${DISK_USAGE}" == "100%" ]; then
  rm -rf ./*
  touch INSUFFICIENT_HARD_DRIVE_SPACE
fi
