import pytest

from renku_notebooks.util.check_image import (
    get_docker_token,
    get_image_workdir,
    image_exists,
    parse_image_name,
)


@pytest.mark.parametrize(
    "name,expected",
    [
        (
            "nginx",
            {
                "hostname": "registry-1.docker.io",
                "image": "library/nginx",
                "tag": "latest",
            },
        ),
        (
            "nginx:1.28",
            {
                "hostname": "registry-1.docker.io",
                "image": "library/nginx",
                "tag": "1.28",
            },
        ),
        (
            "nginx@sha256:24235rt2rewg345ferwf",
            {
                "hostname": "registry-1.docker.io",
                "image": "library/nginx",
                "tag": "sha256:24235rt2rewg345ferwf",
            },
        ),
        (
            "username/image",
            {
                "hostname": "registry-1.docker.io",
                "image": "username/image",
                "tag": "latest",
            },
        ),
        (
            "username/image:1.0.0",
            {
                "hostname": "registry-1.docker.io",
                "image": "username/image",
                "tag": "1.0.0",
            },
        ),
        (
            "username/image@sha256:fdsaf345tre3412t1413r",
            {
                "hostname": "registry-1.docker.io",
                "image": "username/image",
                "tag": "sha256:fdsaf345tre3412t1413r",
            },
        ),
        (
            "gitlab.smth.com/username/project",
            {
                "hostname": "gitlab.smth.com",
                "image": "username/project",
                "tag": "latest",
            },
        ),
        (
            "gitlab.smth.com:443/username/project",
            {
                "hostname": "gitlab.smth.com:443",
                "image": "username/project",
                "tag": "latest",
            },
        ),
        (
            "gitlab.smth.com/username/project/image/subimage",
            {
                "hostname": "gitlab.smth.com",
                "image": "username/project/image/subimage",
                "tag": "latest",
            },
        ),
        (
            "gitlab.smth.com:443/username/project/image/subimage",
            {
                "hostname": "gitlab.smth.com:443",
                "image": "username/project/image/subimage",
                "tag": "latest",
            },
        ),
        (
            "gitlab.smth.com/username/project:1.2.3",
            {
                "hostname": "gitlab.smth.com",
                "image": "username/project",
                "tag": "1.2.3",
            },
        ),
        (
            "gitlab.smth.com:443/username/project:1.2.3",
            {
                "hostname": "gitlab.smth.com:443",
                "image": "username/project",
                "tag": "1.2.3",
            },
        ),
        (
            "gitlab.smth.com/username/project/image/subimage:1.2.3",
            {
                "hostname": "gitlab.smth.com",
                "image": "username/project/image/subimage",
                "tag": "1.2.3",
            },
        ),
        (
            "gitlab.smth.com:443/username/project/image/subimage:1.2.3",
            {
                "hostname": "gitlab.smth.com:443",
                "image": "username/project/image/subimage",
                "tag": "1.2.3",
            },
        ),
        (
            "gitlab.smth.com/username/project@sha256:324fet13t4",
            {
                "hostname": "gitlab.smth.com",
                "image": "username/project",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "gitlab.smth.com:443/username/project@sha256:324fet13t4",
            {
                "hostname": "gitlab.smth.com:443",
                "image": "username/project",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "gitlab.smth.com/username/project/image/subimage@sha256:324fet13t4",
            {
                "hostname": "gitlab.smth.com",
                "image": "username/project/image/subimage",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "gitlab.smth.com:443/username/project/image/subimage@sha256:324fet13t4",
            {
                "hostname": "gitlab.smth.com:443",
                "image": "username/project/image/subimage",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "us.gcr.io/image/subimage@sha256:324fet13t4",
            {
                "hostname": "us.gcr.io",
                "image": "image/subimage",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "us.gcr.io/proj/image",
            {"hostname": "us.gcr.io", "image": "proj/image", "tag": "latest"},
        ),
        (
            "us.gcr.io/proj/image/subimage",
            {"hostname": "us.gcr.io", "image": "proj/image/subimage", "tag": "latest"},
        ),
    ],
)
def test_public_image_name_parsing(name, expected):
    assert parse_image_name(name) == expected


@pytest.mark.integration
def test_public_image_check():
    parsed_image = parse_image_name("nginx:1.19.3")
    token, _ = get_docker_token(**parsed_image, user={})
    assert image_exists(**parse_image_name("nginx:1.19.3"), token=token)
    parsed_image = parse_image_name("nginx")
    token, _ = get_docker_token(**parsed_image, user={})
    assert image_exists(**parse_image_name("nginx"), token=token)
    parsed_image = parse_image_name("renku/singleuser:cb70d7e")
    token, _ = get_docker_token(**parsed_image, user={})
    assert image_exists(**parsed_image, token=token)
    parsed_image = parse_image_name("renku/singleuser")
    token, _ = get_docker_token(**parsed_image, user={})
    assert image_exists(**parsed_image, token=token)
    parsed_image = parse_image_name("madeuprepo/madeupproject:tag")
    assert not image_exists(**parsed_image, token="madeuptoken")


@pytest.mark.integration
def test_image_workdir_check():
    image = "jupyter/minimal-notebook"
    parsed_image = parse_image_name(image)
    token, _ = get_docker_token(**parsed_image, user={})
    workdir = get_image_workdir(**parse_image_name(image), token=token)
    assert workdir == "/home/jovyan"
    assert get_image_workdir("invalid_host", "invalid_image", "invalid_tag") is None
