import gitlab
import logging
import requests
import re

from .. import config
from .gitlab_ import _get_oauth_token


def gcr_public_image_exists(host, project, image, tag="latest"):
    """Check if a public google container registry image exists, if so return True"""
    url = f"https://{host}/v2/{project}/{image}/manifests/{tag}"
    try:
        res = requests.get(url)
    except requests.exceptions.InvalidURL:
        return False
    else:
        return res.status_code == 200


def dockerhub_public_image_exists(project, image, tag="latest"):
    """Check if a public dockerhub image exists, if so return True"""
    auth_url = (
        f"https://auth.docker.io/token?scope=repository:"
        f"{project}/{image}:pull&service=registry.docker.io"
    )
    res = requests.get(auth_url)
    token = res.json().get("token")
    manifest_url = f"https://registry-1.docker.io/v2/{project}/{image}/manifests/{tag}"
    res = requests.get(
        manifest_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.docker.distribution.manifest.v2+json",
        },
    )
    return res.status_code == 200


def gitlab_image_exists(gl, project, image, tag="latest"):
    """Check if a gitlab image exists and whether it is private, a value
    of True, False returned means that the image exists but it is not private."""
    try:
        projects = gl.projects.list(search=project)
    except gitlab.exceptions.GitlabListError:
        return False, False
    else:
        if len(projects) == 1:
            project = projects[0]
        else:
            return False, False
        repos = project.repositories.list(search=image)
        if len(repos) == 1:
            repo = repos[0]
        else:
            return False, False
        try:
            repo.tags.get(id=tag)
        except gitlab.exceptions.GitlabGetError:
            return False, False
        else:
            return True, project.visibility in {"private", "internal"}


def gitlab_public_image_exists(url, project, image, tag="latest"):
    """Check if a public image on a gitlab instance outside of renku exists.
    The first returned value indicates if the image exists, the second indicates
    whether the image is private."""
    try:
        gl = gitlab.Gitlab(url)
    except gitlab.exceptions.GitlabHttpError:
        logging.warning(f"Gitlab url {url} does not exist.")
        return False, False
    return gitlab_image_exists(gl, project, image, tag), False


def renku_gitlab_image_exists(user, project, image, tag="latest"):
    """Check if a specific image is present in the gitlab version tied to
    renku and whether the image is private (indicated in the second returned value)."""
    try:
        gl = gitlab.Gitlab(
            config.GITLAB_URL, api_version=4, oauth_token=_get_oauth_token(user)
        )
    except gitlab.exceptions.GitlabHttpError:
        logging.warning(f"Could not reach Gitlab.")
        return False, False
    return gitlab_image_exists(gl, project, image, tag)


def image_exists(image, user):
    """Check if the provided image name is from a supported platform (public dockerhub,
    public gcr, public gitlab or renku gitlab). This is indicated by the first value that is
    returned. Also as the second returned value indicate whether the image is private
    (only applicable to renku gitlab images)."""
    project_re = "(?P<project>[a-zA-Z0-9-_.]{1,})"
    host_re = "(?P<host>[a-zA-Z0-9-_.]{1,})"
    image_re = "(?P<image>[a-zA-Z0-9-_.]{1,})"
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
    dockerhub_match_w_project = re.match(f"^{project_re}/{image_re}$", image_head)
    dockerhub_match_wo_project = re.match(f"^{image_re}$", image_head)
    gitlab_match = re.match(f"^registry.{host_re}/{project_re}/{image_re}$", image_head)
    if gcr_match is not None:
        # the image name matches gcr regex, check if it exists
        gcr_match_detail = re.match(f"^{host_re}/{project_re}/{image_re}$", image_head)
        return (
            gcr_public_image_exists(
                gcr_match_detail.group("host"),
                gcr_match_detail.group("project"),
                gcr_match_detail.group("image"),
                tag,
            ),
            False,
        )
    elif dockerhub_match_w_project is not None:
        # the image name matches dockerhub regex like username/project:tag, check if it exists
        return (
            dockerhub_public_image_exists(
                dockerhub_match_w_project.group("project"),
                dockerhub_match_w_project.group("image"),
                tag,
            ),
            False,
        )
    elif dockerhub_match_wo_project is not None:
        # the image name matches dockerhub regex like python:3.8, check if it exists
        return (
            dockerhub_public_image_exists(
                "library", dockerhub_match_wo_project.group("image"), tag
            ),
            False,
        )
    elif gitlab_match is not None:
        # the image matches gitlab regex
        public_image_check = gitlab_public_image_exists(
            "https://" + gitlab_match.group("host"),
            gitlab_match.group("project"),
            gitlab_match.group("image"),
            tag,
        )
        if public_image_check[0]:
            # The image is from gitlab and available publicly
            return True, False
        renku_gitlab_check = renku_gitlab_image_exists(
            user, gitlab_match.group("project"), gitlab_match.group("image"), tag
        )
        if renku_gitlab_check[0]:
            # The image is from the renku gitlab repository
            return renku_gitlab_check
    else:
        return False, False
