from dataclasses import dataclass

from cctop.core.usage import Usage


@dataclass(frozen=True, slots=True)
class Model:
    slug: str
    input_rate: float
    output_rate: float
    cache_write_5m_rate: float
    cache_write_1h_rate: float
    cache_read_rate: float

    def cost(self, usage: Usage) -> float:
        return (
            usage.input_tokens * self.input_rate
            + usage.output_tokens * self.output_rate
            + usage.cache_creation_5m_tokens * self.cache_write_5m_rate
            + usage.cache_creation_1h_tokens * self.cache_write_1h_rate
            + usage.cache_read_tokens * self.cache_read_rate
        ) / 1_000_000


OPUS_4_7 = Model("claude-opus-4-7", 5.0, 25.0, 6.25, 10.0, 0.50)
OPUS_4_6 = Model("claude-opus-4-6", 5.0, 25.0, 6.25, 10.0, 0.50)
OPUS_4_5 = Model("claude-opus-4-5", 5.0, 25.0, 6.25, 10.0, 0.50)
OPUS_4_1 = Model("claude-opus-4-1", 15.0, 75.0, 18.75, 30.0, 1.50)
OPUS_4 = Model("claude-opus-4", 15.0, 75.0, 18.75, 30.0, 1.50)
SONNET_4_6 = Model("claude-sonnet-4-6", 3.0, 15.0, 3.75, 6.0, 0.30)
SONNET_4_5 = Model("claude-sonnet-4-5", 3.0, 15.0, 3.75, 6.0, 0.30)
SONNET_4 = Model("claude-sonnet-4", 3.0, 15.0, 3.75, 6.0, 0.30)
SONNET_3_7 = Model("claude-sonnet-3-7", 3.0, 15.0, 3.75, 6.0, 0.30)
HAIKU_4_5 = Model("claude-haiku-4-5", 1.0, 5.0, 1.25, 2.0, 0.10)
HAIKU_3_5 = Model("claude-haiku-3-5", 0.80, 4.0, 1.0, 1.6, 0.08)
OPUS_3 = Model("claude-opus-3", 15.0, 75.0, 18.75, 30.0, 1.50)
HAIKU_3 = Model("claude-haiku-3", 0.25, 1.25, 0.30, 0.50, 0.03)

type ModelUsage = dict[Model, Usage]

_MODELS_BY_SPECIFICITY = sorted(
    [OPUS_4_7, OPUS_4_6, OPUS_4_5, OPUS_4_1, OPUS_4, SONNET_4_6, SONNET_4_5,
     SONNET_4, SONNET_3_7, HAIKU_4_5, HAIKU_3_5, OPUS_3, HAIKU_3],
    key=lambda m: len(m.slug),
    reverse=True,
)


def model(name: str) -> Model | None:
    lower = name.lower()
    return next((m for m in _MODELS_BY_SPECIFICITY if m.slug in lower), None)
