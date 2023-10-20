import pytest

from renku_notebooks.api.schemas.utils import flatten_dict


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            {
                "cloudstorage": {
                    0: {
                        "bucket": ["Missing data for required field."],
                        "endpoint": ["Not a valid URL."],
                    }
                }
            },
            [
                ("cloudstorage.0.bucket", ["Missing data for required field."]),
                ("cloudstorage.0.endpoint", ["Not a valid URL."]),
            ],
        ),
    ],
)
def test_flatten_dict(test_input, expected):
    assert list(flatten_dict(test_input.items(), skip_key_concat=["_schema"])) == expected
