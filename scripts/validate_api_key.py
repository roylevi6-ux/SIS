"""Quick script to validate the Anthropic API key works.

Run: python scripts/validate_api_key.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MODEL_AGENTS_1_8

import anthropic


def main():
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    print(f"API Key: {ANTHROPIC_API_KEY[:8]}...{ANTHROPIC_API_KEY[-4:]}")
    print(f"Base URL: {ANTHROPIC_BASE_URL}")
    print(f"Model: {MODEL_AGENTS_1_8}")
    print("Testing API connection...")

    try:
        client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
            base_url=ANTHROPIC_BASE_URL,
        )
        response = client.messages.create(
            model=MODEL_AGENTS_1_8,
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: SIS API connection successful",
                }
            ],
        )
        print(f"Response: {response.content[0].text}")
        print(f"Input tokens: {response.usage.input_tokens}")
        print(f"Output tokens: {response.usage.output_tokens}")
        print("\nAPI key is valid via proxy. Ready to build.")
    except anthropic.AuthenticationError:
        print("ERROR: API key is invalid. Check your .env file.")
        print("For Riskified proxy: ensure you're on VPN and key is correct.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
