from renku_notebooks.util.check_image import parse_image_name, public_image_exists


def test_public_image_name_parsing():
    assert parse_image_name("nginx") == {
        "hostname": "registry-1.docker.io",
        "username": "library",
        "project": "nginx",
        "image": "",
        "tag": "latest",
    }
    assert parse_image_name("nginx:1.28") == {
        "hostname": "registry-1.docker.io",
        "username": "library",
        "project": "nginx",
        "image": "",
        "tag": "1.28",
    }
    assert parse_image_name("nginx@sha256:24235rt2rewg345ferwf") == {
        "hostname": "registry-1.docker.io",
        "username": "library",
        "project": "nginx",
        "image": "",
        "tag": "sha256:24235rt2rewg345ferwf",
    }
    assert parse_image_name("username/image") == {
        "hostname": "registry-1.docker.io",
        "username": "username",
        "project": "image",
        "image": "",
        "tag": "latest",
    }
    assert parse_image_name("username/image:1.0.0") == {
        "hostname": "registry-1.docker.io",
        "username": "username",
        "project": "image",
        "image": "",
        "tag": "1.0.0",
    }
    assert parse_image_name("username/image@sha256:fdsaf345tre3412t1413r") == {
        "hostname": "registry-1.docker.io",
        "username": "username",
        "project": "image",
        "image": "",
        "tag": "sha256:fdsaf345tre3412t1413r",
    }
    assert parse_image_name("gitlab.smth.com/username/project") == {
        "hostname": "gitlab.smth.com",
        "username": "username",
        "project": "project",
        "image": "",
        "tag": "latest",
    }
    assert parse_image_name("gitlab.smth.com:443/username/project") == {
        "hostname": "gitlab.smth.com:443",
        "username": "username",
        "project": "project",
        "image": "",
        "tag": "latest",
    }
    assert parse_image_name("gitlab.smth.com/username/project/image/subimage") == {
        "hostname": "gitlab.smth.com",
        "username": "username",
        "project": "project",
        "image": "image/subimage",
        "tag": "latest",
    }
    assert parse_image_name("gitlab.smth.com:443/username/project/image/subimage") == {
        "hostname": "gitlab.smth.com:443",
        "username": "username",
        "project": "project",
        "image": "image/subimage",
        "tag": "latest",
    }
    assert parse_image_name("gitlab.smth.com/username/project:1.2.3") == {
        "hostname": "gitlab.smth.com",
        "username": "username",
        "project": "project",
        "image": "",
        "tag": "1.2.3",
    }
    assert parse_image_name("gitlab.smth.com:443/username/project:1.2.3") == {
        "hostname": "gitlab.smth.com:443",
        "username": "username",
        "project": "project",
        "image": "",
        "tag": "1.2.3",
    }
    assert parse_image_name(
        "gitlab.smth.com/username/project/image/subimage:1.2.3"
    ) == {
        "hostname": "gitlab.smth.com",
        "username": "username",
        "project": "project",
        "image": "image/subimage",
        "tag": "1.2.3",
    }
    assert parse_image_name(
        "gitlab.smth.com:443/username/project/image/subimage:1.2.3"
    ) == {
        "hostname": "gitlab.smth.com:443",
        "username": "username",
        "project": "project",
        "image": "image/subimage",
        "tag": "1.2.3",
    }
    assert parse_image_name("gitlab.smth.com/username/project@sha256:324fet13t4") == {
        "hostname": "gitlab.smth.com",
        "username": "username",
        "project": "project",
        "image": "",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name(
        "gitlab.smth.com:443/username/project@sha256:324fet13t4"
    ) == {
        "hostname": "gitlab.smth.com:443",
        "username": "username",
        "project": "project",
        "image": "",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name(
        "gitlab.smth.com/username/project/image/subimage@sha256:324fet13t4"
    ) == {
        "hostname": "gitlab.smth.com",
        "username": "username",
        "project": "project",
        "image": "image/subimage",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name(
        "gitlab.smth.com:443/username/project/image/subimage@sha256:324fet13t4"
    ) == {
        "hostname": "gitlab.smth.com:443",
        "username": "username",
        "project": "project",
        "image": "image/subimage",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name("us.gcr.io/image/subimage@sha256:324fet13t4") == {
        "hostname": "us.gcr.io",
        "username": "image",
        "project": "subimage",
        "image": "",
        "tag": "sha256:324fet13t4",
    }
    assert parse_image_name("us.gcr.io/proj/image") == {
        "hostname": "us.gcr.io",
        "username": "proj",
        "project": "image",
        "image": "",
        "tag": "latest",
    }
    assert parse_image_name("us.gcr.io/proj/image/subimage") == {
        "hostname": "us.gcr.io",
        "username": "proj",
        "project": "image",
        "image": "subimage",
        "tag": "latest",
    }


def test_public_image_check():
    assert public_image_exists(**parse_image_name("nginx:1.19.3"))
    assert public_image_exists(**parse_image_name("nginx"))
    assert public_image_exists(**parse_image_name("renku/singleuser:cb70d7e"))
    assert public_image_exists(**parse_image_name("renku/singleuser"))
    assert not public_image_exists(**parse_image_name("madeuprepo/madeupproject:tag"))
