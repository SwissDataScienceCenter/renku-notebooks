#!/bin/bash

mkdir -p $MOUNT_PATH
cd $MOUNT_PATH

# If there's already a git repo, we don't have to do anything
git rev-parse --is-inside-work-tree 2> /dev/null
if [ $? == 0 ]
then
  echo "Found git repo, returning"
  exit 0
fi

echo "No git repo found, setting up repo and cloning into $GIT_URL"


# Extract the Git host, path and repo name given the full URL.
pat='^(http[s]?:\/\/)([^\/]+)\/?([a-zA-Z0-9_\/\-]+?)$'
[[ $GIT_URL =~ $pat ]]
GIT_HOST="${BASH_REMATCH[2]}"
GIT_PATH="${BASH_REMATCH[3]}"
pat='p\/([^\/]*?)\.git'
[[ $REPOSITORY_URL =~ $pat ]]
REPOSITORY_NAME="${BASH_REMATCH[1]}"

# Wait in case gitlab is temporarily unavailable
curl $GIT_URL
while [ $? != 0 ]
do
  echo "Waiting for git server to become visible at $GIT_URL"
  sleep 5
  curl $GIT_URL
done

echo "Git server found"

# Set up some useful git config, parts of which are omitted
# for anonymous sessions.
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

# It is on purpose that the git credentials are stored OUTSIDE of the volume
# which will be mounted into the user session.
git config credential.helper "store --file=/tmp/git-credentials"
echo "https://oauth2:${GITLAB_OAUTH_TOKEN}@${GIT_HOST}" > /tmp/git-credentials
echo "Git credentials set up"

if [ "$LFS_AUTO_FETCH" = 1 ]; then
  LFS_SKIP_SMUDGE="";
else
  LFS_SKIP_SMUDGE="--skip-smudge";
fi
git lfs install $LFS_SKIP_SMUDGE --local
git remote add origin $REPOSITORY_URL
git fetch origin
git checkout ${BRANCH} || git checkout -b ${BRANCH}
git submodule init && git submodule update
echo "Branch $BRANCH checked out"

# If this option is set, try to recover from a relevant autosave branch.
if [ "${GIT_AUTOSAVE}" == "1" ] ; then
  echo "Trying to recover  from autosave branch"

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
    echo "No auto-save branch found"
  else

    IFS='/' read -r -a AUTOSAVE_REMOTE_BRANCH_ITEMS <<< "$AUTOSAVE_REMOTE_BRANCH"

    # Check if the found autosave branch has a valid format, fail otherwise
    if [ "${#AUTOSAVE_REMOTE_BRANCH_ITEMS[@]}" -lt 7 ] ; then
      echo "Auto-save branch is in the wrong format; cannot recover the state from that branch" >&2
    else
      echo "Resetting to remote branch $AUTOSAVE_REMOTE_BRANCH"
      # Reset the file tree to the auto-saved state.
      git reset --hard $AUTOSAVE_REMOTE_BRANCH

      # Reset HEAD to the last committed change prior to the autosave commit.
      echo "Resetting to commit $PRE_SAVE_LOCAL_COMMIT_SHA"
      PRE_SAVE_LOCAL_COMMIT_SHA=${AUTOSAVE_REMOTE_BRANCH_ITEMS[7]}
      git reset --soft $PRE_SAVE_LOCAL_COMMIT_SHA

      # Unstage all modified files.
      git reset HEAD .

      # Delete the autosave branch both remotely and locally.
      echo "Remove branch $AUTOSAVE_REMOTE_BRANCH locally and remotely"
      AUTOSAVE_LOCAL_BRANCH=${AUTOSAVE_REMOTE_BRANCH/$REMOTES_ORIGIN/''}
      git push origin :"$AUTOSAVE_LOCAL_BRANCH"
    fi
  fi
fi

# Finally: configure the repo such that the git client will communicate with the
# git server through the https proxy and remove all references to credentials store
# on disk. DO NOT ADD ANYTHING AFTER THIS BLOCK!

# Note: The proxy will still verify the certificates of the connection to the git server.
echo "Configure repo for usage with git http proxy"
git config http.proxy http://localhost:8080
git config http.sslVerify false
git config --unset credential.helper
rm /tmp/git-credentials

