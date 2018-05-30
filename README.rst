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

``<service-prefix>/<namespace>/<project>/<commit-sha>`` (GET): start a notebook
server for the user, at the ``<commit-sha>`` of the ``<project>`` from
``<namespace>``. Optionally, the endpoint may include ``/<path:notebook>``, a
path to the notebook within the cloned repository. Note that if multiple
users request the same ``<namespace>/<project>/<commit-sha>``, each user
receives their own notebook server.

``<service-prefix>/<namespace>/<project>/<commit-sha>`` (DELETE): stop the
notebook server.


Usage
-----

``renku-notebooks`` should be added as a dependency to a helm deployment which
includes JupyterHub. The following external service specification needs to be
added to the JupyterHub values:

.. code-block:: yaml

    hub:
      services:
        notebooks:
          url: http://renku-notebooks
          admin: true
          api_token: <notebooks-service-token>

Conversely, the deployment values should include:

.. code-block:: yaml

    notebooks:
      jupyterhub_base_url: /
      jupyterhub_api_token: <notebooks-service-token>


Building images and charts
--------------------------

To build the images and render the chart locally, use `chartpress <https://github.com/jupyterhub/chartpress>`_. Install it with ``pip`` or
use ``pipenv install`` to install the dependency in the included ``Pipfile``.
Then:

.. code-block:: console

    $ cd helm-chart
    $ chartpress
