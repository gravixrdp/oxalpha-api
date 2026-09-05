"""Live local verification script."""

import os
import sys
import time
import httpx
import uvicorn
import threading

from app.main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8899, log_level="warning")

if __name__ == "__main__":
    # Start uvicorn in a daemon thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    # Wait for server to bind
    time.sleep(1.5)

    base_url = "http://127.0.0.1:8899"
    api_key = "test-api-key-12345"

    with httpx.Client(base_url=base_url, timeout=5.0) as client:
        # 1. Test /health
        r_health = client.get("/health")
        print("1. /health ->", r_health.status_code, r_health.json(), "X-Request-ID:", r_health.headers.get("X-Request-ID"))
        assert r_health.status_code == 200
        assert r_health.json() == {"status": "ok"}

        # 2. Test unauthenticated /v1/models
        r_unauth = client.get("/v1/models")
        print("2. /v1/models (unauth) ->", r_unauth.status_code, r_unauth.json())
        assert r_unauth.status_code == 401

        # 3. Test authenticated /v1/models
        r_models = client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
        print("3. /v1/models (auth) ->", r_models.status_code, r_models.json())
        assert r_models.status_code == 200
        assert r_models.json()["object"] == "list"

        # 4. Test validation error format on completions
        r_bad_chat = client.post("/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json={})
        print("4. /v1/chat/completions (invalid) ->", r_bad_chat.status_code, r_bad_chat.json())
        assert r_bad_chat.status_code == 400
        assert "error" in r_bad_chat.json()

    print("\nALL LIVE VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    sys.exit(0)
