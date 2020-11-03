import logging
import requests
import re

from .gitlab_ import get_renku_project, get_public_project, get_notebook_image


def gcr_public_image_exists(host, image, tag="latest"):
    """Check if a public google container registry image exists, if so return True"""
    url = f"https://{host}/v2/{image}/manifests/{tag}"
    try:
        res = requests.get(url)
    except requests.exceptions.InvalidURL:
        return False
    else:
        return res.status_code == 200


def dockerhub_public_image_exists(image, tag="latest"):
    """Check if a public dockerhub image exists, if so return True"""
    auth_url = (
        f"https://auth.docker.io/token?scope=repository:"
        f"{image}:pull&service=registry.docker.io"
    )
    res = requests.get(auth_url)
    token = res.json().get("token")
    manifest_url = f"https://registry-1.docker.io/v2/{image}/manifests/{tag}"
    res = requests.get(
        manifest_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.docker.distribution.manifest.v2+json",
        },
    )
    return res.status_code == 200


def check_gitlab_image(image, tag, user):
    # See https://docs.gitlab.com/ee/user/packages/container_registry/#image-naming-convention
    # Images in gitlab can have quite different formats where the image name can have multiple
    # slashes or there could also be no image name at all (renku by default has no image names)
    host_project_re = '^registry.(?P<hostname>[a-zA-Z0-9-_.]{1,})'\
                      '/(?P<namespace>[a-zA-Z0-9-_.]{1,})'\
                      '/(?P<project>[a-zA-Z0-9-_.]{1,})'
    host_project_match = re.match(host_project_re, image)
    hostname, namespace, project = host_project_match.groups()
    url = 'https://' + hostname
    remaining = image[host_project_match.span()[1]:]
    if remaining == '':
        image = None
    else:
        image = remaining[1:]  # remove the starting / from image name
    # First check fi the image is public
    gl_project = get_public_project(url, namespace, project)
    if gl_project is not None:
        if get_notebook_image(gl_project, image, tag) is not None:
            return True, False
    # Check if image is on renkus gitlab
    gl_project = get_renku_project(user, namespace, project)
    if gl_project is not None:
        if get_notebook_image(gl_project, image, tag) is not None:
            return True, gl_project.attributes.get("visibility") in {"private", "internal"}
    return False, False


def image_exists(image, user):
    """Check if the provided image name is from a supported platform (public dockerhub,
    public gcr, public gitlab or renku gitlab). This is indicated by the first value that is
    returned. Also as the second returned value indicate whether the image is private
    (only applicable to renku gitlab images)."""
    image_split = image.split(":")
    if len(image_split) > 2:
        logging.info(
            f"Image names can only contain one or no ':' symbols, "
            f"image {image} contains {len(image_split)-1} ':' symbols."
        )
        return False, False
    tag = image_split[1] if len(image_split) == 2 else "latest"
    image_head = image_split[0]
    gcr_match = re.match("^eu.gcr.io|^us.gcr.io|^gcr.io|^asia.gcr.io", image_head)
    dockerhub_match = re.match("^(?P<image>[a-zA-Z0-9-_./]{1,})", image_head)
    gitlab_match = re.match("^registry.", image_head)
    if gcr_match is not None:
        # the image name matches gcr regex, check if it exists
        gcr_match_detail = re.match("^(?P<host>[a-zA-Z0-9-_.]{1,})/(?P<image>[a-zA-Z0-9-_./]{1,})$", image_head)
        return (
            gcr_public_image_exists(
                gcr_match_detail.group("host"), gcr_match_detail.group("image"), tag,
            ),
            False,
        )
    if dockerhub_match is not None and gitlab_match is None:
        # the image name matches dockerhub regex like username/project:tag, check if it exists
        docker_image_name = image_head if "/" in image_head else f"library/{image_head}"
        return (
            dockerhub_public_image_exists(docker_image_name, tag),
            False,
        )
    if gitlab_match is not None:
        # the image name matches gitlab regex, check if it exists
        return check_gitlab_image(image_head, tag, user)
    return False, False
