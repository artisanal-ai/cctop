import pytest

from cctop.core.models import (
    HAIKU_3,
    HAIKU_3_5,
    HAIKU_4_5,
    OPUS_3,
    OPUS_4,
    OPUS_4_5,
    OPUS_4_6,
    OPUS_4_7,
    SONNET_3_7,
    SONNET_4,
    SONNET_4_5,
    SONNET_4_6,
    Model,
    model,
)
from cctop.core.usage import Usage


@pytest.mark.parametrize(
    ("m", "usage", "expected"),
    [
        (OPUS_4_6, Usage(input_tokens=1_000_000, output_tokens=1_000_000), 30.0),
        (SONNET_4_5, Usage(
            cache_creation_5m_tokens=500_000, cache_creation_1h_tokens=500_000, cache_read_tokens=1_000_000,
        ), 5.175),
        (HAIKU_4_5, Usage(input_tokens=1_000_000), 1.0),
        (OPUS_4, Usage(input_tokens=1_000_000), 15.0),
        (HAIKU_3_5, Usage(input_tokens=1_000_000, output_tokens=1_000_000), 4.8),
        (HAIKU_3, Usage(input_tokens=1_000_000), 0.25),
    ],
)
def test_model_cost_calculation(m: Model, usage: Usage, expected: float) -> None:
    assert m.cost(usage) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("claude-opus-4-20250514", OPUS_4),
        ("claude-opus-4-6-20260401", OPUS_4_6),
        ("claude-opus-4-5-20250514", OPUS_4_5),
        ("claude-opus-4-7-20260601", OPUS_4_7),
        ("claude-sonnet-4-20250514", SONNET_4),
        ("claude-sonnet-4-5-20250514", SONNET_4_5),
        ("claude-sonnet-4-6-20260401", SONNET_4_6),
        ("claude-sonnet-3-7-20250219", SONNET_3_7),
        ("claude-haiku-4-5-20251001", HAIKU_4_5),
        ("claude-haiku-3-5-20241022", HAIKU_3_5),
        ("claude-opus-3-20240229", OPUS_3),
        ("claude-haiku-3-20240307", HAIKU_3),
    ],
)
def test_model_lookup(name: str, expected: Model) -> None:
    assert model(name) is expected


def test_model_lookup_case_insensitive() -> None:
    assert model("CLAUDE-OPUS-4-6") is OPUS_4_6


@pytest.mark.parametrize("name", ["gpt-4", "", "unknown-model"])
def test_model_lookup_unknown(name: str) -> None:
    assert model(name) is None


def test_cache_write_rates_differ() -> None:
    assert OPUS_4_6.cache_write_5m_rate == pytest.approx(6.25)
    assert OPUS_4_6.cache_write_1h_rate == pytest.approx(10.0)
