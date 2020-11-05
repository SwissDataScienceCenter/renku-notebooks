from renku_notebooks.util.check_image import parse_image_name, public_image_exists


def test_public_image_name_parsing():
    assert parse_image_name(
        "registry.dev.renku.ch:443/tasko.olevski/testpublic:9966d3e"
    ) == ("https://registry.dev.renku.ch:443", "tasko.olevski/testpublic", "9966d3e")
    assert parse_image_name(
        "registry.dev.renku.ch/tasko.olevski/testpublic:9966d3e"
    ) == ("https://registry.dev.renku.ch", "tasko.olevski/testpublic", "9966d3e")
    assert parse_image_name("nginx") == (
        "https://registry-1.docker.io",
        "library/nginx",
        "latest",
    )
    assert parse_image_name("nginx:1.19.3") == (
        "https://registry-1.docker.io",
        "library/nginx",
        "1.19.3",
    )
    assert parse_image_name("renku/singleuser:cb70d7e") == (
        "https://registry-1.docker.io",
        "renku/singleuser",
        "cb70d7e",
    )
    assert parse_image_name(
        "gcr.io/google-containers/busybox"
        "@sha256:545e6a6310a27636260920bc07b994a299b6708a1b26910cfefd335fdfb60d2b"
    ) == (
        "https://gcr.io",
        "google-containers/busybox",
        "sha256:545e6a6310a27636260920bc07b994a299b6708a1b26910cfefd335fdfb60d2b",
    )


def test_public_image_check():
    assert public_image_exists(*parse_image_name("nginx:1.19.3"))
    assert public_image_exists(*parse_image_name("nginx"))
    assert public_image_exists(*parse_image_name("renku/singleuser:cb70d7e"))
    assert public_image_exists(*parse_image_name("renku/singleuser"))
    assert not public_image_exists(*parse_image_name("madeuprepo/madeupproject:tag"))
