#!/bin/bash

# extract the Git host and path
pat='^(http[s]?:\/\/)([^\/]+)\/?([a-zA-Z0-9_\/\-]+?)$'
[[ $GIT_URL =~ $pat ]]
GIT_HOST="${BASH_REMATCH[2]}"
GIT_PATH="${BASH_REMATCH[3]}"

# If we are setting up a new volume, remove the previous mount-path and
# do a fresh checkout of the repository. Also initialize git lfs and set
# the proper file permissions.
if [ "$LFS_AUTO_FETCH" = 1 ]; then
  LFS_SKIP_SMUDGE="";
else
  LFS_SKIP_SMUDGE="--skip-smudge";
fi

nc -z localhost 8080
while [ $? == 1 ]
do
  echo "Waiting for git proxy to start..."
  sleep 1
  nc -z localhost 8080
done

curl $GIT_HOST
while [ $? != 0 ]
do
  echo "Waiting for git server to become visible at $GIT_HOST"
  sleep 1
  curl $GIT_HOST
done


pat='p\/([^\/]*?)\.git'
[[ $REPOSITORY =~ $pat ]]
REPOSITORY_NAME="${BASH_REMATCH[1]}"

#clear path
rm -rf ${MOUNT_PATH}/*
(rm -rf ${MOUNT_PATH}/.* || true)


# set up the repo
mkdir -p $MOUNT_PATH
cd $MOUNT_PATH
git init
if [[ -v GIT_EMAIL ]]
then
  git config user.email "$GIT_EMAIL"
fi
if [[ -v GIT_FULL_NAME ]]
then
  git config user.name "$GIT_FULL_NAME"
fi
git config push.default simple

# Configure the repo such that the git client will communicate with Git Server
# through the https proxy.
# Note: The proxy will still verify the certificates of the connection to the git server.
git config http.proxy http://localhost:8080
git config http.sslVerify false

git lfs install $LFS_SKIP_SMUDGE --local
git remote add origin $REPOSITORY
git fetch origin
git checkout ${BRANCH} || git checkout -b ${BRANCH}
git submodule init && git submodule update

# If this option is set, try to recover from a relevant autosave branch.
if [ "${GIT_AUTOSAVE}" == "1" ] ; then

  # Go through all available branches and find the appropriate autosave branch.
  REMOTES_ORIGIN="remotes/origin/"
  AUTOSAVE_BRANCH_PREFIX="renku/autosave/$RENKU_USERNAME"

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
    git reset --hard $COMMIT_SHA
  else

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


python /app/rpc-server.py


# run the command
$@
