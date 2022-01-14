# Resource Migrations

In most cases the notebooks code is compatible with old versions of the JuyterServer CRD and the values of existing
JupyterServer resources. However sometimes changes are made that require all existing JupyterServer resources
to be adjusted and migrated to avoid interruption of users' work.

The migrations here are python scripts that utilize the python k8s SDK and modify
existing resources in the cluster so that they properly function after a new version of the notebook
service has been released.

The migrations run in an `init` container before the notebook service starts.

The migrations are made to be idempotent - which means that running a single migration more than once 
will not provide different results. I.e. if you run the same migration twice, the second time
around the same changes will be applied which means that ultimately the second time the resources in
question did not actually change.

**WARNING**: The migrations do not support downgrading the notebook service. In the case 
where it is required to downgrade the notebook service and migrations were applied by
the upgrades that will be rolled back, then all active sessions should be deleted prior to
the downgrade to avoid problems.