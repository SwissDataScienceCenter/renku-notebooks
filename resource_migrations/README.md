# Resource Migrations

In most cases the notebooks code is compatible with old versions of the JuyterServer CRD and the values of existing
JupyterServer resources. However sometimes changes are made that require all existing JupyterServer resources
to be adjusted and migrated to avoid interruption of users' work.

The migrations here are python scripts that utilize the python k8s SDK and modify
existing resources in the cluster so that they properly function after a new version of the notebook
service has been released.

The migration scripts are named after the version of the release that requires them to run. 
The migrations should be applied after the specific notebooks release is deployed.

Refer to the changelog for specific information about each migration.

The migrations are expected to be run from the terminal. They use the currently active k8s context
and a specific namespace where they will operate. Running the migrations should be done through the terminal
with the python environment specified in the repo's Pipenv file.

The migrations are made to be idempotent - which means that running a single migration more than once 
will not provide different results. I.e. if you run the same migration twice the second time
around the same changes will be applied which means that ultimately the second time the resources in
question did not actually change.
