from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Usage:

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_5m_tokens: int = 0
    cache_creation_1h_tokens: int = 0
    cache_read_tokens: int = 0
    tools: dict[str, "Usage.Tool"] = field(default_factory=dict)

    @property
    def cache_creation_tokens(self) -> int:
        return self.cache_creation_5m_tokens + self.cache_creation_1h_tokens

    @property
    def cache_tokens(self) -> int:
        return self.cache_creation_tokens + self.cache_read_tokens

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_tokens

    @property
    def tool_calls(self) -> int:
        return sum(t.calls for t in self.tools.values())

    @property
    def tool_errors(self) -> int:
        return sum(t.errors for t in self.tools.values())

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_5m_tokens=self.cache_creation_5m_tokens + other.cache_creation_5m_tokens,
            cache_creation_1h_tokens=self.cache_creation_1h_tokens + other.cache_creation_1h_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            tools={
                name: self.tools.get(name, Usage.Tool()) + other.tools.get(name, Usage.Tool())
                for name in {*self.tools, *other.tools}
            },
        )

    @dataclass(frozen=True, slots=True)
    class Tool:
        calls: int = 0
        errors: int = 0

        def __add__(self, other: "Usage.Tool") -> "Usage.Tool":
            return Usage.Tool(self.calls + other.calls, self.errors + other.errors)
