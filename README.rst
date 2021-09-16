Renku notebooks
===============

.. image:: https://github.com/SwissDataScienceCenter/renku-notebooks/workflows/CI/badge.svg
    :alt: CI
    :target: https://github.com/SwissDataScienceCenter/renku-notebooks/actions?query=branch%3Amaster+workflow%3ACI
    
.. image:: https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg?style=flat-square
    :alt: Conventional Commits
    :target: https://conventionalcommits.org


A simple service using the `Amalthea operator
<https://github.com/SwissDataScienceCenter/amalthea>`_, to provide interactive Jupyter
notebooks for the Renku platform.

The service relies on `renku-gateway <https://github.com/SwissDataScienceCenter/renku-gateway>`_
for authentication. However, anonymous users are supported as well in which case anyone can
start and use sessions for public renku projects. Therefore, the notebook service can run
even without having the renku-gateway installed or present. In this case only sessions 
for anonymous users can be launched.


Endpoints
---------

The service defines endpoints to list the active sessions for a user,
start or stop a session. It can also provide the logs of a running
user session or information about work that was saved automatically if a user
stops a session without committing and pushing all their work to their project 
repository.

The endpoints for the API will be defined in the swagger page of any Renku deployment.
The swagger page is usually available at ``https://<domain-name>/swagger/?urls.primaryName=notebooks%20service``.

`Here <https://renkulab.io/swagger/?urls.primaryName=notebooks%20service>`_ you can look 
at the swagger page for the ``renkulab.io`` deployment and explore the endpoints in more detail.

Usage
-----

The best way to use ``renku-notebooks`` is as a part of a ``renku`` platform deployment. 
As described above using ``renku-notebooks`` without the other components
in the ``renku`` platform will only allow the usage of anonymous sessions for public renku projects.
This is a drawback because anonymous sessions do not allow users to save their work but rather
to quickly test something out or explore what renku has to offer. 

If used as a part of ``renku`` the notebook service receives all required user credentials
from ``renku-gateway``, another service in the ``renku`` platform. 
These credentials include information about the user and their git credentials. 
The notebook service then uses the git credentials to clone the user's repository,
pull images from the registry if needed and sets up a proxy that handles and authenticates
all git commands issued by the user in the session without asking the user to log in 
GitLab every time they launch a session. 

Building images and charts
--------------------------

To build the images and render the chart locally, use `chartpress
<https://github.com/jupyterhub/chartpress>`_. Install it with ``pip`` or use
``pipenv install`` to install the dependency in the included ``Pipfile``.

.. code-block:: console

    $ pipenv install
    $ cd helm-chart
    $ pipenv run chartpress


Running in stand-alone mode with ``kind``
-----------------------------------------

The notebooks service can be run separate from a ``renku`` deployment. In this
case, it will function as a simple API that can launch anonymous user sessions.
Follow the steps below to do this.


1. Launch a ``kind`` cluster that maps port 80 and 443 from the host to the ``kind`` cluster.
This will allow you to access the notebooks api and sessions without having to setup 
port forwarding with the ``kubectl`` command.

.. code-block:: console

    cat <<EOF | kind create cluster --name kind --config=-
    kind: Cluster
    apiVersion: kind.x-k8s.io/v1alpha4
    nodes:
    - role: control-plane
      kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
      extraPortMappings:
      - containerPort: 80
        hostPort: 80
        protocol: TCP
      - containerPort: 443
        hostPort: 443
        protocol: TCP
    EOF

2. Install ``ingress-nginx`` and the notebook service helm chart in the kind cluster.

.. code-block:: console

    $ VERSION=$(curl https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/stable.txt)
    $ kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/$VERSION/deploy/static/provider/kind/deploy.yaml
    $ cd helm-chart
    $ helm dep update ./renku-notebooks
    $ helm upgrade --install renku-notebooks ./renku-notebooks \
      --set "global.anonymousSessions.enabled=true" \
      --set "gitlab.url=https://renkulab.io/gitlab" \
      --set "gitlab.registry.host=registry.renkulab.io" \
      --set "amalthea.scope.namespaces[0]=default" \
      --set "ingress.enabled=true" \
      --set "ingress.hosts[0]=localhost" \
      --set ingress.annotations."kubernetes\.io/ingress\.class"="nginx" \
      --set "sessionIngress.host=localhost"
      
3. You can then start a new session with the request:

.. code-block:: console

    curl -kL http://localhost/notebooks/servers -X POST \
      -H "Renku-Auth-Anon-Id: secret1234567" -H "Content-Type: application/json" \
      -d '{"namespace":"andi", "project":"public-test-project", "commit_sha":"8368d4455d760b68f7547c31f5918b0178d6190f"}'

4. See the list of running sessions by listing all JupyterServer resources in k8s. 
You can also use the output to get the URL to visit the session as well as 
see if the session is fully running or pending.

.. code-block:: console

    $ kubectl get jupyterservers
    NAME                                          IMAGE                                                   URL                                                                      POD STATUS
    secret1234-public-2dtest-2dproject-faadeed2   registry.renkulab.io/andi/public-test-project:8368d44   https://localhost/sessions/secret1234-public-2dtest-2dproject-faadeed2   Running

5. When the session is fully running you can visit it at the URL indicated
in the output of the command from the previous step. When you are prompted to enter a 
token then use the value from the ``Renku-Auth-Anon-Id`` header in the request to 
start the notebook - ``secret1234567``. Alternatively to bypass the token prompt you can
append ``?token=secret1234567`` at the end of the url.

6. If you send a ``GET`` request the same endpoint you used to launch the session
then you will get a list of all running sessions. This list will also include information
on the session status, URL to access the session and other useful information.

.. code-block:: console

    $ curl -kL http://localhost/notebooks/servers -X GET -H "Renku-Auth-Anon-Id: secret1234567"
    {
      "servers": {
        "secret1234-public-2dtest-2dproject-faadeed2": {
          "annotations": {
            "renku.io/branch": "master",
            "renku.io/commit-sha": "8368d4455d760b68f7547c31f5918b0178d6190f",
            "renku.io/default_image_used": "False",
            "renku.io/git-host": "renkulab.io",
            "renku.io/gitlabProjectId": "10856",
            "renku.io/namespace": "andi",
            "renku.io/projectName": "public-test-project",
            "renku.io/username": "secret1234567"
          },
          "image": "",
          "name": "secret1234-public-2dtest-2dproject-faadeed2",
          "resources": {
            "cpu": "0.5",
            "memory": "1G",
            "storage": "1G"
          },
          "started": "2021-09-16T12:23:35+00:00",
          "state": {
            "pod_name": "secret1234-public-2dtest-2dproject-faadeed2-0"
          },
          "status": {
            "message": null,
            "phase": "Running",
            "ready": true,
            "reason": null,
            "step": "Ready"
          },
          "url": "https://localhost/sessions/secret1234-public-2dtest-2dproject-faadeed2?token=secret1234567"
        }
      }
    }

Please note that the example here does not use ``https`` because it is for illustration
purposes only. For a production deployment ``https`` should be used.

Contributing
------------

Please see the general `contributing guidelines for
Renku <https://github.com/SwissDataScienceCenter/renku/blob/master/CONTRIBUTING.rst>`_.


To ensure a consistent code style, this project uses
`black <https://github.com/python/black>`_ and
`flake8 <http://flake8.pycqa.org/en/latest/>`_. The easiest way to minimize
conflicts is to use the `pre-commit
package <https://github.com/pre-commit/pre-commit>`_ - simple run:

.. code-block:: console

    pipenv run pre-commit install

and the relevant pre-commit hooks will be placed in your ``.git`` folder.

To run unit tests:

.. code-block:: console

    pipenv run pytest tests/unit

To run the integration tests, see `here <https://github.com/SwissDataScienceCenter/renku-notebooks/blob/master/tests/integration/README.md>`_.

To generate HTML coverage report:

.. code-block:: console

    pipenv run pytest --cov=renku_notebooks --cov-report html

Test coverage report will be generated in a ``htmlcov`` directory in the project's
root directory.
