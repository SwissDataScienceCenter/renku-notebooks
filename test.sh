ALL_BRANCHES=(`git branch -a `)
for branch in "${ALL_BRANCHES[@]}"
do
# It's not scrictly impossible that we will have more than one branch matching
# here, but RenkuLab should preven users from creating more than one autsave
# branch per user/branch/commmit tuple.
    AUTOSAVE_REMOTE_BRANCH=${branch// /}
    echo $branch $AUTOSAVE_REMOTE_BRANCH
done

branch="some/test///branch///"
AUTOSAVE_REMOTE_BRANCH=${branch// /}
echo $branch $AUTOSAVE_REMOTE_BRANCH