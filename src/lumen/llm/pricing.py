# Pricing: Claude Sonnet 4.5 per https://www.anthropic.com/pricing (verified May 2026).
# TODO: revisit when Anthropic updates published rates.
_SONNET_45_INPUT_PER_MTOK_USD = 3.0
_SONNET_45_OUTPUT_PER_MTOK_USD = 15.0


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    m = model.casefold()
    if "claude" in m and "sonnet" in m:
        inp = input_tokens * _SONNET_45_INPUT_PER_MTOK_USD / 1_000_000
        out = output_tokens * _SONNET_45_OUTPUT_PER_MTOK_USD / 1_000_000
        return round(inp + out, 6)
    inp = input_tokens * _SONNET_45_INPUT_PER_MTOK_USD / 1_000_000
    out = output_tokens * _SONNET_45_OUTPUT_PER_MTOK_USD / 1_000_000
    return round(inp + out, 6)
