# SPDX-FileCopyrightText: 2024 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Salim Kayal <salim.kayal@idiap.ch>
#
# SPDX-License-Identifier: Apache-2.0


import pytest

from fastapi.testclient import TestClient

from liveness_detector import HealthzResponse, app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_liveness(client) -> None:
    response = client.get(app.url_path_for("is_container_idle"))
    assert response.status_code == 200
    values = response.json()
    assert all(key in values for key in HealthzResponse.model_fields.keys())
