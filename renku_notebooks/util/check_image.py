import requests

from werkzeug.http import parse_www_authenticate_header


def public_image_exists(url, image, tag="latest", token=None):
    """Check the docker repo API if the image exists"""
    image_digest_url = f"{url}/v2/{image}/manifests/{tag}"
    req1 = requests.get(image_digest_url)
    if req1.status_code == 200:
        # the repo did not require authentication
        return True
    if req1.status_code == 401 and "Www-Authenticate" in req1.headers.keys():
        # the repo requires a token, get token then get manifest
        www_auth = parse_www_authenticate_header(req1.headers["Www-Authenticate"])
        params = dict(www_auth.items())
        realm = params.pop("realm")
        req2 = requests.get(realm, params=params)
        public_token = req2.json().get("token")
        if req2.status_code == 200 and public_token is not None:
            req3 = requests.get(
                image_digest_url,
                headers={
                    "Authorization": f"Bearer {public_token}",
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json",
                },
            )
            return req3.status_code == 200
    return False


def extract_tag(text, sep=":"):
    """Extract a tag from the text and return the tag as well as any text that remains."""
    split_text = text.split(sep)
    if len(split_text) == 1:
        # no tag was present in the text
        return "latest", text
    elif len(split_text) == 2:
        # a tag was present but there is a another sep symbol
        # this is useful when a port is specified in the docker image host
        # it avoids grabbing everything past the port which occurs early in the string
        return split_text[-1], split_text[0]
    else:
        # same as above but there are even more separator symbols, assume last is tag
        return split_text[-1], sep.join(split_text[:-1])


def parse_image_name(image):
    """Parse a full image name into repo url, image and tag.
    If the tag is not give this will return latest. If the
    repository is not mentioned this will default to dockerhub."""
    docker_url = "https://registry-1.docker.io"
    parts = image.split("/")
    # extract url of the container repo host
    try:
        requests.get("https://" + parts[0])
    except requests.exceptions.ConnectionError:
        url = docker_url
    else:
        url = "https://" + parts[0]
        parts.pop(0)
    # extract tag or sha
    if "@" in parts[-1]:
        tag, remainder = extract_tag(parts[-1], "@")
        parts[-1] = remainder
    elif ":" in parts[-1]:
        tag, remainder = extract_tag(parts[-1], ":")
        parts[-1] = remainder
    else:
        tag = "latest"
    # extract image name
    if len(parts) == 1 and url == docker_url:
        image_name = "library/" + parts[0]
    else:
        image_name = "/".join(parts)
    return url, image_name, tag
