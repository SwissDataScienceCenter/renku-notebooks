import pytest
from marshmallow.exceptions import ValidationError

from renku_notebooks.api.schemas.custom_fields import CpuField, MemoryField, GpuField


@pytest.mark.parametrize(
    "test_input,expected_value",
    [("0.1", 0.1), ("1000m", 1), ("500", 500), (1000, 1000)],
)
def test_cpu_field_valid_deserialize(test_input, expected_value):
    assert CpuField().deserialize(test_input) == expected_value


@pytest.mark.parametrize("test_input", ["-1.0", -0.1, -1000, "500g", "0.5M", "wrong"])
def test_cpu_field_invalid_deserialize(test_input):
    with pytest.raises(ValidationError):
        CpuField().deserialize(test_input)


@pytest.mark.parametrize(
    "test_input,expected_value",
    [
        ({"cpu": 0.1}, "0.1"),
        ({"cpu": 1}, "1"),
        ({"cpu": 500}, "500"),
        ({"cpu": 1000}, "1000"),
    ],
)
def test_cpu_field_valid_serialize(test_input, expected_value):
    assert CpuField().serialize("cpu", test_input) == expected_value


@pytest.mark.parametrize(
    "test_input",
    [{"cpu": -1.0}, {"cpu": -0.1}, {"cpu": "500g"}, {"cpu": "0.5M"}, {"cpu": "wrong"}],
)
def test_cpu_field_invalid_serialize(test_input):
    with pytest.raises(ValidationError):
        CpuField().serialize("cpu", test_input)


@pytest.mark.parametrize(
    "test_input,expected_value",
    [
        ("0.1", 0.1),
        ("1000b", 1000),
        ("500G", 500 * (10**9)),
        ("1Gi", 1073741824),
        ("1kb", 1000),
    ],
)
def test_memory_field_valid_deserialize(test_input, expected_value):
    assert MemoryField().deserialize(test_input) == expected_value


@pytest.mark.parametrize("test_input", ["-1.0", -0.1, -1000, "wrong"])
def test_memory_field_invalid_deserialize(test_input):
    with pytest.raises(ValidationError):
        MemoryField().deserialize(test_input)


@pytest.mark.parametrize(
    "test_input,expected_value",
    [
        ({"memory": 0.1}, "0.00G"),
        ({"memory": 2**30}, "1.07G"),
        ({"memory": 10**9}, "1G"),
        ({"memory": 100.0 * 10**9}, "100G"),
    ],
)
def test_memory_field_valid_serialize(test_input, expected_value):
    assert MemoryField().serialize("memory", test_input) == expected_value


@pytest.mark.parametrize(
    "test_input",
    [
        {"memory": -1.0},
        {"memory": -0.1},
        {"memory": "500g"},
        {"memory": "0.5M"},
        {"memory": "wrong"},
    ],
)
def test_memory_field_invalid_serialize(test_input):
    # NOTE: serialization expects to receive a positive number indicating bytes
    with pytest.raises(ValidationError):
        MemoryField().serialize("memory", test_input)


@pytest.mark.parametrize(
    "test_input,expected_value",
    [
        ("1", 1),
        (1, 1),
        (2, 2),
        (2.0, 2),
        ("3.0", 3),
    ],
)
def test_gpu_field_valid_deserialize(test_input, expected_value):
    assert GpuField().deserialize(test_input) == expected_value


@pytest.mark.parametrize("test_input", ["-1.0", -0.1, 2.5, "3.5"])
def test_gpu_field_invalid_deserialize(test_input):
    with pytest.raises(ValidationError):
        GpuField().deserialize(test_input)


@pytest.mark.parametrize(
    "test_input,expected_value",
    [
        ({"gpu": 1}, "1"),
        ({"gpu": 2}, "2"),
    ],
)
def test_gpu_field_valid_serialize(test_input, expected_value):
    assert GpuField().serialize("gpu", test_input) == expected_value


@pytest.mark.parametrize(
    "test_input",
    [
        {"gpu": -1.0},
        {"gpu": -0.1},
        {"gpu": "500g"},
        {"gpu": "0.5M"},
        {"gpu": "wrong"},
        {"gpu": "1.5"},
    ],
)
def test_gpu_field_invalid_serialize(test_input):
    # NOTE: serialization expects to receive a positive number indicating bytes
    with pytest.raises(ValidationError):
        GpuField().serialize("gpu", test_input)
