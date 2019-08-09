workflow "Run tests" {
  on = "push"
  resolves = ["cclauss/GitHub-Action-for-pytest"]
}

action "cclauss/GitHub-Action-for-pytest" {
  uses = "cclauss/GitHub-Action-for-pytest@ce387ba052749acd7a2c27bd01e0495fe0524645"
}
