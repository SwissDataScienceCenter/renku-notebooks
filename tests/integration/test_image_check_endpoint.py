import pytest
import requests


@pytest.mark.parametrize(
    "image_url,expected_status_code",
    [
        ("nginx", 200),
        (":::?-+^", 422),
        ("image/does_not_exist:9999999999999.99999.9999", 404),
    ],
)
def test_image_check_endpoint(
    image_url,
    expected_status_code,
    headers,
    base_url,
):
    url = f"{base_url}/images"
    res = requests.get(url, headers=headers, params={"image_url": image_url})
    assert res.status_code == expected_status_code
