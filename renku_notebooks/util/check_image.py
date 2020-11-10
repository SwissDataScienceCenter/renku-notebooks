import re
import requests

from werkzeug.http import parse_www_authenticate_header


def public_image_exists(hostname, username, project, image, tag):
    """Check the docker repo API if the image exists"""
    url = f"https://{hostname}"
    image = "/".join([username, project, image]).rstrip("/")
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


def build_re(*parts):
    """Assemble the regex."""
    return re.compile(r"^" + r"".join(parts) + r"$")


def parse_image_name(image):
    """
    Extract the hostname, username, project, image and tag name from the provided
    string. If the image cannot be validated return None. Otherwise return
    a dictionary with the keys ['hostname', 'username', 'project', 'image', 'tag'].
    """
    # docker username occurs only at the beginning of the image and is followed by /
    docker_username = r"(?P<username>(?<=^)[a-zA-Z0-9]{1,}(?=\/))"
    # the hostname occurs at the beginning, has at least one part followed by .
    # and it ends with a /
    hostname = r"(?P<hostname>(?<=^)[a-zA-Z0-9_\-]{1,}\.[a-zA-Z0-9\._\-:]{1,}(?=\/))"
    # gitlab namespace/project/subproject combination is preceeded by /
    # and ends with @ or : or the end of the image name
    gl_namespace = r"(?P<username>(?<=\/)[a-zA-Z0-9\._\-]{1,}(?:(?=\/)))"
    gl_project = r"(?P<project>(?<=\/)[a-zA-Z0-9\._\-]{1,}(?:(?=:)|(?=@)|(?=$)|(?=\/)))"
    gl_image = r"(?P<image>(?<=\/)[a-zA-Z0-9\._\-\/]{1,}(?:(?=:)|(?=@)|(?=$)))"
    # docker project is similar to gitlab project but it cannot contain /
    docker_project = (
        r"(?P<project>(?:(?<=^)|(?<=\/))[a-zA-Z0-9\._\-]{1,}(?:(?=:)|(?=@)|(?=$)))"
    )
    # sha code is preceeded by @ and ends with the end of the image name
    sha = r"(?P<tag>(?<=@)[a-zA-Z0-9\._\-:]{1,}(?=$))"
    # tag is preceeded by : and ends with the end of the image name
    tag = r"(?P<tag>(?<=:)[a-zA-Z0-9\._\-]{1,}(?=$))"

    # a list of tuples with (regex, stuff to fill in case of match)
    regexes = [
        # nginx
        (
            build_re(docker_project),
            {
                "hostname": "registry-1.docker.io",
                "username": "library",
                "tag": "latest",
                "image": "",
            },
        ),
        # nginx:1.28
        (
            build_re(docker_project, r":", tag),
            {"hostname": "registry-1.docker.io", "username": "library", "image": ""},
        ),
        # nginx@sha256:24235rt2rewg345ferwf
        (
            build_re(docker_project, r"@", sha),
            {"hostname": "registry-1.docker.io", "username": "library", "image": ""},
        ),
        # username/image
        (
            build_re(docker_username, r"\/", docker_project),
            {"hostname": "registry-1.docker.io", "tag": "latest", "image": ""},
        ),
        # username/image:1.0.0
        (
            build_re(docker_username, r"\/", docker_project, r":", tag),
            {"hostname": "registry-1.docker.io", "image": ""},
        ),
        # username/image@sha256:fdsaf345tre3412t1413r
        (
            build_re(docker_username, r"\/", docker_project, r"@", sha),
            {"hostname": "registry-1.docker.io", "image": ""},
        ),
        # gitlab.com/username/project
        (
            build_re(hostname, r"\/", gl_namespace, r"\/", gl_project),
            {"tag": "latest", "image": ""},
        ),
        # gitlab.com/username/project:1.2.3
        (
            build_re(hostname, r"\/", gl_namespace, r"\/", gl_project, r":", tag),
            {"image": ""},
        ),
        # gitlab.com/username/project@sha256:324fet13t4
        (
            build_re(hostname, r"\/", gl_namespace, r"\/", gl_project, r"@", sha),
            {"image": ""},
        ),
        # gitlab.com/username/project/image/subimage
        (
            build_re(hostname, r"\/", gl_namespace, r"\/", gl_project, r"\/", gl_image),
            {"tag": "latest"},
        ),
        # gitlab.com/username/project/image/subimage:1.2.3
        (
            build_re(
                hostname,
                r"\/",
                gl_namespace,
                r"\/",
                gl_project,
                r"\/",
                gl_image,
                r":",
                tag,
            ),
            {},
        ),
        # gitlab.com/username/project/image/subimage@sha256:324fet13t4
        (
            build_re(
                hostname,
                r"\/",
                gl_namespace,
                r"\/",
                gl_project,
                r"\/",
                gl_image,
                r"@",
                sha,
            ),
            {},
        ),
    ]

    matches = []
    for regex, fill in regexes:
        match = re.match(regex, image)
        if match is not None:
            match_dict = match.groupdict()
            match_dict.update(fill)
            matches.append(match_dict)
    if len(matches) == 1:
        return matches[0]
