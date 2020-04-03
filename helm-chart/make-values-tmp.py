#!/usr/bin/env python3

import argparse
import secrets
import sys

import ruamel.yaml

yaml = ruamel.yaml.YAML()
yaml.preserve_quotes = True

# Note: We hardcode "notebooks.fullname" / the service
# name here. These secondary deployments MUST run in their
# own dedicated namespace anyway.
TEMPORARY_NOTEBOOKS_SERVICE_NAME = "notebooks-tmp"


def main():
    """Create a values file for a secondary notebooks service helm deployment
    (inluding a secondary Jupyterhub) which handles temporary sessions for
    logged-out users."""

    argparser = argparse.ArgumentParser(description=main.__doc__)

    argparser.add_argument("--values-file", help="Input values file", required=True)
    argparser.add_argument(
        "--renku-namespace", help="Namespace for the Renku deployment", required=True
    )
    argparser.add_argument(
        "--output", "-o", help="Output file", default="notebooks-tmp-values.yaml"
    )
    args = argparser.parse_args()

    with open(args.values_file) as f:
        values = yaml.load(f.read())

    # Copy over all the necessary stuff from the original values file
    new_values = values["notebooks"]

    # We don't know the release name here, so we override the name of the service

    new_values["fullnameOverride"] = TEMPORARY_NOTEBOOKS_SERVICE_NAME

    new_values["global"] = {
        "renku": {"domain": values["global"]["renku"]["domain"]},
        "useHTTPS": values["global"]["useHTTPS"],
    }

    hub_section = new_values["jupyterhub"]["hub"]
    hub_section["cookie_secret"] = secrets.token_hex(32)
    hub_section["baseUrl"] = "{}-tmp/".format(hub_section["baseUrl"].rstrip("/"))
    hub_section["db"]["url"] = (
        hub_section["db"]["url"]
        .replace("jupyterhub", "jupyterhub-tmp")
        .replace("postgresql:", "postgresql.{}.svc:".format(args.renku_namespace))
    )
    hub_section["extraEnv"] = [
        env
        for env in hub_section["extraEnv"]
        if env["name"] not in ["PGPASSWORD", "JUPYTERHUB_AUTHENTICATOR"]
    ]
    hub_section["extraEnv"].append(
        {
            "name": "PGPASSWORD",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "renku-jupyterhub-tmp-postgres",
                    "key": "jupyterhub-tmp-postgres-password",
                }
            },
        }
    )
    hub_section["extraEnv"].append({"name": "JUPYTERHUB_AUTHENTICATOR", "value": "tmp"})
    hub_section["services"]["notebooks"]["url"] = "http://{}".format(
        TEMPORARY_NOTEBOOKS_SERVICE_NAME
    )
    hub_section["services"]["notebooks"]["apiToken"] = secrets.token_hex(32)
    del hub_section["services"]["gateway"]

    auth_section = new_values["jupyterhub"]["auth"]
    auth_section["state"]["cryptoKey"] = secrets.token_hex(32)
    auth_section["type"] = "tmp"
    del auth_section["gitlab"]

    new_values["jupyterhub"]["proxy"]["secretToken"] = secrets.token_hex(32)

    # Add some reasonably short defaults for server culling
    new_values["jupyterhub"]["cull"] = {
        "enabled": True,
        "timeout": 3600,
        "every": 60,
    }

    # Configure ingress rule for /jupyterhub-tmp/
    new_values["ingress"] = values["ingress"]
    new_values["ingress"]["jupyterhubPath"] = new_values["jupyterhub"]["hub"]["baseUrl"]

    with open(args.output, "w") as f:
        yaml.dump(new_values, f)
    sys.stdout.write("Successfully created {}".format(args.output))


if __name__ == "__main__":
    main()
