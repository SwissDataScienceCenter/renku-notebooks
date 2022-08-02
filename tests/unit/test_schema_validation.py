import pytest
from marshmallow import ValidationError

from renku_notebooks.config import config

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
    schema = config.session_get_endpoint_annotations.schema()
    response = {**passing_annotation_response, "extra_annotation": "smth"}
    assert schema.load(
        response
    ) == config.session_get_endpoint_annotations.sanitize_dict(response)


def test_missing_required_annotation_fails():
    schema = config.session_get_endpoint_annotations.schema()
    response = passing_annotation_response.copy()
    response.pop(f"{RENKU_ANNOTATION_PREFIX}projectName")
    with pytest.raises(ValidationError):
        schema.load(response)
