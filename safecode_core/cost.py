import os


def cost_kzt(tokens_in: int, tokens_out: int) -> float:
    """Prices come from env (default 0: set your own, see .env.example). Rule-based scans cost 0."""
    pin = float(os.environ.get("LLM_PRICE_INPUT_PER_1K_KZT", 0) or 0)
    pout = float(os.environ.get("LLM_PRICE_OUTPUT_PER_1K_KZT", 0) or 0)
    return round(tokens_in / 1000 * pin + tokens_out / 1000 * pout, 4)
