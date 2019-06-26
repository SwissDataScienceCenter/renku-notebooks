Renku notebooks
===============

.. image:: https://travis-ci.org/SwissDataScienceCenter/renku-notebooks.svg?branch=master
    :target: https://travis-ci.org/SwissDataScienceCenter/renku-notebooks

.. image:: https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg?style=flat-square
    :alt: Conventional Commits
    :target: https://conventionalcommits.org


A simple external JupyterHub service, which provides interactive notebooks for
the Renku platform.

The service authenticates the user against JupyterHub and provides additional
endpoints for launching notebooks for GitLab repository projects. An
authenticated user may launch a notebook for any commit-sha in any project
where they have developer access rights.


Endpoints
---------

The service defines these endpoints:

``<service-prefix>/<namespace>/<project>/<commit-sha>`` (GET): an html request
returns a page with the server status. If the server is running, it redirects to
it. A request for ``application/json`` returns the server JSON.

``<service-prefix>/<namespace>/<project>/<commit-sha>`` (POST): start a notebook
server for the user, at the ``<commit-sha>`` of the ``<project>`` from
``<namespace>``. Optionally, the endpoint may include ``/<path:notebook>``, a
path to the notebook within the cloned repository. Note that if multiple users
request the same ``<namespace>/<project>/<commit-sha>``, each user receives
their own notebook server.

``<service-prefix>/<namespace>/<project>/<commit-sha>`` (DELETE): stop the
notebook server.

``<service-prefix>/servers`` (GET): retrieve the servers running for the
logged-in user.


Usage
-----

``renku-notebooks`` can be used as part of a ``renku`` platform deployment as a
helm dependency, or as a standalone service. If used as a part of ``renku`` with
a managed GitLab deployment, the client registration is done automatically.  If
used as a standalone service or with a non-managed GitLab, JupyterHub needs to
first be added as an OAuth application in GitLab.

The following external service specification is added to the JupyterHub values:

.. code-block:: yaml

    hub:
      services:
        notebooks:
          url: http://renku-notebooks
          admin: true
          api_token: <notebooks-service-token>
          oauth_client_id: service-notebooks

Conversely, the deployment values should include:

.. code-block:: yaml

    notebooks:
      jupyterhub_base_url: /
      jupyterhub_api_token: <notebooks-service-token>


Building images and charts
--------------------------

To build the images and render the chart locally, use `chartpress
<https://github.com/jupyterhub/chartpress>`_. Install it with ``pip`` or use
``pipenv install`` to install the dependency in the included ``Pipfile``.

.. code-block:: console

    $ pipenv install
    $ cd helm-chart
    $ pipenv run chartpress


Running in stand-alone mode with minikube
-----------------------------------------

The notebooks service can be run separate from a ``renku`` deployment. In this
case, it will function simply as an extension of a JupyterHub deployment.
Since the functionality is contingent on accessing GitLab, JupyterHub must
first be added as a GitLab OAuth application. The configuration of the
callbacks should follow:

.. code-block::

    <hub-url>/hub/oauth_callback
    <hub-url>/hub/api/oauth2/authorize

where ``<hub-url>`` should be the full public address of the hub, including the
``base_url``, if any. Using the provided `minikube-values.yaml` you can use

.. code-block::

    http://localhost:31212/hub/oauth_callback
    http://localhost:31212/hub/api/oauth2/authorize

You can then deploy JupyterHub and the notebooks service with helm:

.. code-block:: console

    helm upgrade --install renku-notebooks \
      -f minikube-values.yaml \
      --set global.renku.domain$(minikube ip):31212 \
      renku-notebooks

Look up the name of the proxy pod and set up a port-forward, e.g.

.. code-block:: console

    kubectl get pods
    NAME                               READY   STATUS    RESTARTS   AGE
    hub-8d6cc8f8c-ss52t                1/1     Running   0          22m
    proxy-747596c4f4-wdmfs             1/1     Running   0          22m
    renku-notebooks-678b8fdd99-x6sbn   1/1     Running   0          22m

    kubectl port-forward proxy-747596c4f4-wdmfs 31212:8000

You can now visit http://localhost:31212/jupyterhub/services/notebooks/user
which should log you in to gitlab.com and show your user information. To
launch a notebook server, you need to obtain a token from
http://localhost:31212/hub/token and use it in the ``POST`` request:

.. code-block:: console

    curl -X POST \
    http://localhost:31212/services/notebooks/<namespace>/<project>/<commit-sha> \
    -H "Authorization: token <token>"


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

To run tests:

.. code-block:: console

    pipenv run pytest

To generate HTML coverage report:

.. code-block:: console

    pipenv run pytest --cov=renku_notebooks --cov-report html

Test coverage report will be generated in a ``htmlcov`` directory in the project's
root directory.
