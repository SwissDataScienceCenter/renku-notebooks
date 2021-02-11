from marshmallow import ValidationError
import pytest

from renku_notebooks.api.schemas import UserPodAnnotations


RENKU_ANNOTATION_PREFIX = "renku.io/"
JUPYTERHUB_ANNOTATION_PREFIX = "hub.jupyter.org/"

passing_annotation_response = {
    f"{RENKU_ANNOTATION_PREFIX}namespace": "smth",
    f"{RENKU_ANNOTATION_PREFIX}projectId": "smth",
    f"{RENKU_ANNOTATION_PREFIX}projectName": "smth",
    f"{RENKU_ANNOTATION_PREFIX}branch": "smth",
    f"{RENKU_ANNOTATION_PREFIX}commit-sha": "smth",
    f"{RENKU_ANNOTATION_PREFIX}username": "smth",
    f"{RENKU_ANNOTATION_PREFIX}default_image_used": "smth",
    f"{RENKU_ANNOTATION_PREFIX}repository": "smth",
    f"{RENKU_ANNOTATION_PREFIX}git-host": "smth",
    f"{JUPYTERHUB_ANNOTATION_PREFIX}servername": "smth",
    f"{JUPYTERHUB_ANNOTATION_PREFIX}username": "smth",
}


def test_unknown_annotations_allowed():
    schema = UserPodAnnotations()
    response = {
        **passing_annotation_response,
        "extra_annotation": "smth",
    }
    assert schema.load(response) == response


def test_missing_required_annotation_fails():
    schema = UserPodAnnotations()
    response = passing_annotation_response.copy()
    response.pop(f"{RENKU_ANNOTATION_PREFIX}projectName")
    with pytest.raises(ValidationError):
        schema.load(response)
