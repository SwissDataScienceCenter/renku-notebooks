import pytest
from dataclasses import asdict

from renku_notebooks.api.classes.image import Image


@pytest.mark.parametrize(
    "name,expected",
    [
        (
            "nginx",
            {
                "hostname": "registry-1.docker.io",
                "name": "library/nginx",
                "tag": "latest",
            },
        ),
        (
            "nginx:1.28",
            {
                "hostname": "registry-1.docker.io",
                "name": "library/nginx",
                "tag": "1.28",
            },
        ),
        (
            "nginx@sha256:24235rt2rewg345ferwf",
            {
                "hostname": "registry-1.docker.io",
                "name": "library/nginx",
                "tag": "sha256:24235rt2rewg345ferwf",
            },
        ),
        (
            "username/image",
            {
                "hostname": "registry-1.docker.io",
                "name": "username/image",
                "tag": "latest",
            },
        ),
        (
            "username/image:1.0.0",
            {
                "hostname": "registry-1.docker.io",
                "name": "username/image",
                "tag": "1.0.0",
            },
        ),
        (
            "username/image@sha256:fdsaf345tre3412t1413r",
            {
                "hostname": "registry-1.docker.io",
                "name": "username/image",
                "tag": "sha256:fdsaf345tre3412t1413r",
            },
        ),
        (
            "gitlab.smth.com/username/project",
            {
                "hostname": "gitlab.smth.com",
                "name": "username/project",
                "tag": "latest",
            },
        ),
        (
            "gitlab.smth.com:443/username/project",
            {
                "hostname": "gitlab.smth.com:443",
                "name": "username/project",
                "tag": "latest",
            },
        ),
        (
            "gitlab.smth.com/username/project/image/subimage",
            {
                "hostname": "gitlab.smth.com",
                "name": "username/project/image/subimage",
                "tag": "latest",
            },
        ),
        (
            "gitlab.smth.com:443/username/project/image/subimage",
            {
                "hostname": "gitlab.smth.com:443",
                "name": "username/project/image/subimage",
                "tag": "latest",
            },
        ),
        (
            "gitlab.smth.com/username/project:1.2.3",
            {
                "hostname": "gitlab.smth.com",
                "name": "username/project",
                "tag": "1.2.3",
            },
        ),
        (
            "gitlab.smth.com:443/username/project:1.2.3",
            {
                "hostname": "gitlab.smth.com:443",
                "name": "username/project",
                "tag": "1.2.3",
            },
        ),
        (
            "gitlab.smth.com/username/project/image/subimage:1.2.3",
            {
                "hostname": "gitlab.smth.com",
                "name": "username/project/image/subimage",
                "tag": "1.2.3",
            },
        ),
        (
            "gitlab.smth.com:443/username/project/image/subimage:1.2.3",
            {
                "hostname": "gitlab.smth.com:443",
                "name": "username/project/image/subimage",
                "tag": "1.2.3",
            },
        ),
        (
            "gitlab.smth.com/username/project@sha256:324fet13t4",
            {
                "hostname": "gitlab.smth.com",
                "name": "username/project",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "gitlab.smth.com:443/username/project@sha256:324fet13t4",
            {
                "hostname": "gitlab.smth.com:443",
                "name": "username/project",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "gitlab.smth.com/username/project/image/subimage@sha256:324fet13t4",
            {
                "hostname": "gitlab.smth.com",
                "name": "username/project/image/subimage",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "gitlab.smth.com:443/username/project/image/subimage@sha256:324fet13t4",
            {
                "hostname": "gitlab.smth.com:443",
                "name": "username/project/image/subimage",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "us.gcr.io/image/subimage@sha256:324fet13t4",
            {
                "hostname": "us.gcr.io",
                "name": "image/subimage",
                "tag": "sha256:324fet13t4",
            },
        ),
        (
            "us.gcr.io/proj/image",
            {"hostname": "us.gcr.io", "name": "proj/image", "tag": "latest"},
        ),
        (
            "us.gcr.io/proj/image/subimage",
            {"hostname": "us.gcr.io", "name": "proj/image/subimage", "tag": "latest"},
        ),
    ],
)
def test_public_image_name_parsing(name, expected):
    assert asdict(Image.from_path(name)) == expected


@pytest.mark.parametrize(
    "image,exists",
    [
        ("nginx:1.19.3", True),
        ("nginx", True),
        ("renku/singleuser:cb70d7e", True),
        ("renku/singleuser", True),
        ("madeuprepo/madeupproject:tag", False),
        ("olevski90/oci-image:0.0.1", True),
    ],
)
@pytest.mark.integration
def test_public_image_check(image, exists):
    parsed_image = Image.from_path(image)
    assert parsed_image.repo_api().image_exists(parsed_image) == exists


@pytest.mark.integration
def test_image_workdir_check():
    image = "jupyter/minimal-notebook"
    parsed_image = Image.from_path(image)
    workdir = parsed_image.repo_api().image_workdir(parsed_image)
    assert workdir.absolute().as_posix() == "/home/jovyan"
    parsed_image = Image.from_path("invalid_image:invalid_tag")
    workdir = parsed_image.repo_api().image_workdir(parsed_image)
    assert workdir is None
