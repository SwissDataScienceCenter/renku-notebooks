import gitlab
import logging
import requests
import re

from .. import config
from .gitlab_ import _get_oauth_token


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


def gitlab_image_exists(gl, namespace, image, tag="latest"):
    """Check if a gitlab image exists and whether it is private, a value
    of True, False returned means that the image exists but it is not private."""
    try:
        gl_project = gl.projects.get(f"{namespace}")
    except gitlab.exceptions.GitlabGetError:
        return False, False
    else:
        is_private = hasattr(gl_project, "visibility") and gl_project.visibility in {
            "private",
            "internal",
        }
        repos = gl_project.repositories.list()
        for repo in repos:
            path = namespace if image == "" else f"{namespace}/{image}"
            if repo.path == path:
                try:
                    repo.tags.get(id=tag)
                except gitlab.exceptions.GitlabGetError:
                    return False, False
                else:
                    return True, is_private


def gitlab_public_image_exists(url, namespace, image, tag="latest"):
    """Check if a public image on a gitlab instance outside of renku exists.
    The first returned value indicates if the image exists, the second indicates
    whether the image is private."""
    try:
        gl = gitlab.Gitlab(url, api_version=4)
    except gitlab.exceptions.GitlabHttpError:
        logging.warning(f"Gitlab url {url} does not exist.")
        return False, False
    return gitlab_image_exists(gl, namespace, image, tag)


def renku_gitlab_image_exists(user, namespace, image, tag="latest"):
    """Check if a specific image is present in the gitlab version tied to
    renku and whether the image is private (indicated in the second returned value)."""
    try:
        gl = gitlab.Gitlab(
            config.GITLAB_URL, api_version=4, oauth_token=_get_oauth_token(user)
        )
    except gitlab.exceptions.GitlabHttpError:
        logging.warning(f"Could not reach Gitlab.")
        return False, False
    output = gitlab_image_exists(gl, namespace, image, tag)
    return output


def image_exists(image, user):
    """Check if the provided image name is from a supported platform (public dockerhub,
    public gcr, public gitlab or renku gitlab). This is indicated by the first value that is
    returned. Also as the second returned value indicate whether the image is private
    (only applicable to renku gitlab images)."""
    host_re = "(?P<host>[a-zA-Z0-9-_.]{1,})"
    image_re = "(?P<image>[a-zA-Z0-9-_./]{1,})"
    gcr_match = re.match("^eu.gcr.io|^us.gcr.io|^gcr.io|^asia.gcr.io", image)
    image_split = image.split(":")
    if len(image_split) > 2:
        logging.info(
            f"Image names can only contain one or no ':' symbols, "
            f"image {image} contains {len(image_split)-1} ':' symbols."
        )
        return False, False
    tag = image_split[1] if len(image_split) == 2 else "latest"
    image_head = image_split[0]
    dockerhub_match = re.match(f"^{image_re}$", image_head)
    gitlab_match = re.match(f"^registry.{host_re}/(?P<rest>.+)", image_head)
    if gcr_match is not None:
        # the image name matches gcr regex, check if it exists
        gcr_match_detail = re.match(f"^{host_re}/{image_re}$", image_head)
        return (
            gcr_public_image_exists(
                gcr_match_detail.group("host"), gcr_match_detail.group("image"), tag,
            ),
            False,
        )
    elif gitlab_match is None and dockerhub_match is not None:
        # the image name matches dockerhub regex like username/project:tag, check if it exists
        docker_image_name = image_head if "/" in image_head else f"library/{image_head}"
        return (
            dockerhub_public_image_exists(docker_image_name, tag),
            False,
        )
    elif gitlab_match is not None:
        # the image matches gitlab regex
        rest = gitlab_match.group("rest").split("/")
        if len(rest) == 2:
            gl_namespace = "/".join(rest[0:2])
            gl_image = ""
        elif len(rest) > 2:
            gl_namespace = "/".join(rest[0:2])
            gl_image = rest[2] if len(rest) == 3 else "/".join(rest[2:])
        else:
            return False, False
        public_image_check = gitlab_public_image_exists(
            "https://" + gitlab_match.group("host"), gl_namespace, gl_image, tag,
        )
        if public_image_check[0]:
            # The image is from gitlab and available publicly
            return True, False
        else:
            renku_gitlab_check = renku_gitlab_image_exists(
                user, gl_namespace, gl_image, tag
            )
            return renku_gitlab_check
    else:
        return False, False
