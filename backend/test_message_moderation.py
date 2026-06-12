#!/usr/bin/env python3
"""Manual moderation check using Gemini."""

from controllers.message_controller.message_controller import _moderate_message
from config import get_settings


def run_case(label: str, text: str) -> None:
    result = _moderate_message(text)
    print(f"[{label}] allowed={result.get('allowed')} category={result.get('category')} severity={result.get('severity')}")
    print(f"Reason: {result.get('reason')}")
    print("-")


def main() -> None:
    settings = get_settings()
    if not settings.GEMINI_MODERATION_API_KEY:
        print("GEMINI_MODERATION_API_KEY is not set.")
        return

    run_case("safe", "Hello! Hope you are doing well today.")
    run_case("offensive", "You are a terrible person and I hate you.")


if __name__ == "__main__":
    main()
