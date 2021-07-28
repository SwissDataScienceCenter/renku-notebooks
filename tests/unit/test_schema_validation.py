from marshmallow import ValidationError
import pytest

from renku_notebooks.api.schemas import UserPodAnnotations

RENKU_ANNOTATION_PREFIX = "renku.io/"
JUPYTER_ANNOTATION_PREFIX = "jupyter.org/"

passing_annotation_response = {
    f"{RENKU_ANNOTATION_PREFIX}namespace": "smth",
    f"{RENKU_ANNOTATION_PREFIX}gitlabProjectId": "smth",
    f"{RENKU_ANNOTATION_PREFIX}projectName": "smth",
    f"{RENKU_ANNOTATION_PREFIX}branch": "smth",
    f"{RENKU_ANNOTATION_PREFIX}commit-sha": "smth",
    f"{RENKU_ANNOTATION_PREFIX}username": "smth",
    f"{RENKU_ANNOTATION_PREFIX}default_image_used": "smth",
    f"{RENKU_ANNOTATION_PREFIX}repository": "smth",
    f"{RENKU_ANNOTATION_PREFIX}git-host": "smth",
    f"{JUPYTER_ANNOTATION_PREFIX}servername": "smth",
    f"{JUPYTER_ANNOTATION_PREFIX}username": "smth",
}


def test_unknown_annotations_allowed():
    schema = UserPodAnnotations()
    response = {**passing_annotation_response, "extra_annotation": "smth"}
    assert schema.load(response) == response


def test_missing_required_annotation_fails():
    schema = UserPodAnnotations()
    response = passing_annotation_response.copy()
    response.pop(f"{RENKU_ANNOTATION_PREFIX}projectName")
    with pytest.raises(ValidationError):
        schema.load(response)


def test_value_range_check():
    from renku_notebooks.api.schemas import _in_range

    # test byte size comparison
    value_range = {"type": "bytes", "min": "1G", "max": "10G"}
    # too small
    assert not _in_range("0.5M", value_range)
    # too big
    assert not _in_range("200G", value_range)
    # just right
    assert _in_range("5G", value_range)

    # test int comparison
    value_range = {"type": "int", "min": 1, "max": 10}
    # too small
    assert not _in_range(0, value_range)
    # too big
    assert not _in_range(100, value_range)
    # just right
    assert _in_range(5, value_range)
