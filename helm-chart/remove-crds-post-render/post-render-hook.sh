#!/bin/sh

# A post-renderer can be any executable that accepts rendered Kubernetes manifests 
# on STDIN and returns valid Kubernetes manifests on STDOUT. It should return an 
# non-0 exit code in the event of a failure. This is the only "API" between the two 
# components. It allows for great flexibility in what you can do with your post-render process.

cat <&0 > all.yaml
kustomize build . && rm all.yaml
