Renku notebooks
===============

A simple external JupyterHub service, which provides interactive notebooks for
the Renku platform.

The service authenticates the user against JupyterHub and provides additional
endpoints for launching notebooks for GitLab repository projects. An
authenticated user may launch a notebook for any commit-sha in any project
where they have developer access rights.


Endpoints
---------

The service defines these endpoints:

``<service-prefix>`` (GET): Show the currently running notebook servers.

``<service-prefix>/<namespace>/<project>/<commit-sha>`` (GET): an html request
returns a page with the server status. If the server is running, it redirects
to it. A request for ``application/json`` returns the server JSON.

``<service-prefix>/<namespace>/<project>/<commit-sha>`` (POST): start a notebook
server for the user, at the ``<commit-sha>`` of the ``<project>`` from
``<namespace>``. Optionally, the endpoint may include ``/<path:notebook>``, a
path to the notebook within the cloned repository. Note that if multiple
users request the same ``<namespace>/<project>/<commit-sha>``, each user
receives their own notebook server.

``<service-prefix>/<namespace>/<project>/<commit-sha>`` (DELETE): stop the
notebook server.

``<service-prefix>/user`` (GET): retrieve the JupyterHub user model


Usage
-----

``renku-notebooks`` can be used as part of a ``renku`` platform deployment as
a helm dependency, or as a standalone service. If used as a part of ``renku``
with a managed GitLab deployment, the client registration is done
automatically.  If used as a standalone service or with a non-managed GitLab,
JupyterHub needs to first be added as an OAuth application in GitLab.

The following external service specification is added to the JupyterHub
values:

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
Then:

.. code-block:: console

    $ cd helm-chart
    $ chartpress


Running in stand-alone mode
---------------------------

The notebooks service can be run separate from a ``renku`` deployment. In this
case, it will function simply as an extension of a JupyterHub deployment.
Since the functionality is contingent on accessing GitLab, JupyterHub must
first be added as a GitLab OAuth application. The configuration of the
callbacks should follow:

.. code-block::

    <hub-url>/hub/oauth_callback
    <hub-url>/hub/api/oauth2/authorize

where ``<hub-url>`` should be the full public address of the hub, including the
``base_url``, if any.

If you are using minikube, you can then deploy JupyterHub and the notebooks
service with helm:

.. code-block:: console

    helm upgrade --install renku-notebooks \
      -f minikube_values.yaml \
      --set jupyterhub.hub.extraEnv.GITLAB_URL=https://gitlab.com \
      --set jupyterhub.hub.extraEnv.IMAGE_REGISTRY=registry.gitlab.com \
      --set jupyterhub_api_url=http://$(minikube ip):31212/hub/api \
      renku-notebooks

  To launch a server, you can now use the ``POST`` endpoint described above.
