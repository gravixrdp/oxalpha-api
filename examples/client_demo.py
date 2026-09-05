"""Example script demonstrating how to interact with the LLM API proxy using the OpenAI Python SDK."""

import os
from openai import OpenAI

# 1. Configure the OpenAI client to point to the local proxy or Railway deployment
API_KEY = os.getenv("API_KEY", "your-secret-api-key")
BASE_URL = os.getenv("PROXY_URL", "http://127.0.0.1:8000/v1")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)


def demo_list_models():
    """List available models."""
    print("--- Listing Available Models ---")
    models = client.models.list()
    for model in models.data:
        print(f"Model ID: {model.id}, Owned By: {model.owned_by}")
    print()


def demo_non_streaming():
    """Perform a standard non-streaming chat completion."""
    print("--- Non-Streaming Completion ---")
    response = client.chat.completions.create(
        model="glm-5.3-flash",
        messages=[
            {"role": "user", "content": "Hello! Write a 1-sentence haiku about coding."}
        ],
        stream=False,
    )
    print("Response ID:", response.id)
    print("Model:", response.model)
    print("Content:\n", response.choices[0].message.content)
    print()


def demo_streaming():
    """Perform a streaming chat completion using SSE."""
    print("--- Streaming Completion ---")
    stream = client.chat.completions.create(
        model="glm-5.3-flash",
        messages=[
            {"role": "user", "content": "Count from 1 to 5 slowly."}
        ],
        stream=True,
    )

    print("Streamed output: ", end="", flush=True)
    for chunk in stream:
        delta_content = chunk.choices[0].delta.content if chunk.choices else None
        if delta_content:
            print(delta_content, end="", flush=True)
    print("\n--- End of Stream ---\n")


if __name__ == "__main__":
    print(f"Connecting to LLM Proxy at: {BASE_URL}\n")
    try:
        demo_list_models()
        # Note: Chat completions require the proxy to be connected to Ox Alpha or running a mock upstream
        demo_non_streaming()
        demo_streaming()
    except Exception as exc:
        print(f"Error executing request: {exc}")
