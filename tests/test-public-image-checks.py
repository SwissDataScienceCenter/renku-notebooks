import pytest

from renku_notebooks.util.check_image import (
    parse_image_name,
    image_exists,
    get_docker_token,
)


def test_public_image_name_parsing():
    assert parse_image_name("nginx") == {
        "hostname": "registry-1.docker.io",
        "image": "library/nginx",
        "tag": "latest",
    }
    assert parse_image_name("nginx:1.28") == {
        "hostname": "registry-1.docker.io",
        "image": "library/nginx",
        "tag": "1.28",
    }
    assert parse_image_name("nginx@sha256:24235rt2rewg345ferwf") == {
        "hostname": "registry-1.docker.io",
        "image": "library/nginx",
        "tag": "sha256:24235rt2rewg345ferwf",
    }
    assert parse_image_name("username/image") == {
        "hostname": "registry-1.docker.io",
        "image": "username/image",
        "tag": "latest",
    }
    assert parse_image_name("username/image:1.0.0") == {
        "hostname": "registry-1.docker.io",
        "image": "username/image",
        "tag": "1.0.0",
    }
    assert parse_image_name("username/image@sha256:fdsaf345tre3412t1413r") == {
        "hostname": "registry-1.docker.io",
        "image": "username/image",
        "tag": "sha256:fdsaf345tre3412t1413r",
    }
    assert parse_image_name("gitlab.smth.com/username/project") == {
        "hostname": "gitlab.smth.com",
        "image": "username/project",
        "tag": "latest",
    }
    assert parse_image_name("gitlab.smth.com:443/username/project") == {
        "hostname": "gitlab.smth.com:443",
        "image": "username/project",
        "tag": "latest",
    }
    assert parse_image_name("gitlab.smth.com/username/project/image/subimage") == {
        "hostname": "gitlab.smth.com",
        "image": "username/project/image/subimage",
        "tag": "latest",
    }
    assert parse_image_name("gitlab.smth.com:443/username/project/image/subimage") == {
        "hostname": "gitlab.smth.com:443",
        "image": "username/project/image/subimage",
        "tag": "latest",
    }
    assert parse_image_name("gitlab.smth.com/username/project:1.2.3") == {
        "hostname": "gitlab.smth.com",
        "image": "username/project",
        "tag": "1.2.3",
    }
    assert parse_image_name("gitlab.smth.com:443/username/project:1.2.3") == {
        "hostname": "gitlab.smth.com:443",
        "image": "username/project",
        "tag": "1.2.3",
    }
    assert parse_image_name(
        "gitlab.smth.com/username/project/image/subimage:1.2.3"
    ) == {
        "hostname": "gitlab.smth.com",
        "image": "username/project/image/subimage",
        "tag": "1.2.3",
    }
    assert parse_image_name(
        "gitlab.smth.com:443/username/project/image/subimage:1.2.3"
    ) == {
        "hostname": "gitlab.smth.com:443",
        "image": "username/project/image/subimage",
        "tag": "1.2.3",
    }
    assert parse_image_name("gitlab.smth.com/username/project@sha256:324fet13t4") == {
        "hostname": "gitlab.smth.com",
        "image": "username/project",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name(
        "gitlab.smth.com:443/username/project@sha256:324fet13t4"
    ) == {
        "hostname": "gitlab.smth.com:443",
        "image": "username/project",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name(
        "gitlab.smth.com/username/project/image/subimage@sha256:324fet13t4"
    ) == {
        "hostname": "gitlab.smth.com",
        "image": "username/project/image/subimage",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name(
        "gitlab.smth.com:443/username/project/image/subimage@sha256:324fet13t4"
    ) == {
        "hostname": "gitlab.smth.com:443",
        "image": "username/project/image/subimage",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name("us.gcr.io/image/subimage@sha256:324fet13t4") == {
        "hostname": "us.gcr.io",
        "image": "image/subimage",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name("us.gcr.io/proj/image") == {
        "hostname": "us.gcr.io",
        "image": "proj/image",
        "tag": "latest",
    }
    assert parse_image_name("us.gcr.io/proj/image/subimage") == {
        "hostname": "us.gcr.io",
        "image": "proj/image/subimage",
        "tag": "latest",
    }


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
