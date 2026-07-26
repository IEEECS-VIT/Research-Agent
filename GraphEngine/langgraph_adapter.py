"""
Lightweight adapter for LangGraph SDK with a safe fallback.

This module intentionally keeps the dependency optional: if the
`langgraph` Python package is not installed or not configured, the
adapter exposes `available = False` and callers should fall back to
local orchestration.

It reads `LANGGRAPH_API_KEY` from the environment when present.
"""
import os
from typing import Any


class LangGraphAdapter:
    def __init__(self):
        self.api_key = os.getenv("LANGGRAPH_API_KEY")
        self.available = False
        self.client = None

        try:
            import langgraph

            # If import succeeds, try to initialize the client.
            # This is intentionally minimal — we only use LangGraph for
            # orchestration in future. If the user provides an API key,
            # the client will be configured accordingly.
            self.client = getattr(langgraph, "Client", None)
            if callable(self.client):
                try:
                    self.client = self.client(api_key=self.api_key) if self.api_key else self.client()
                except Exception:
                    # If client init fails, mark as unavailable
                    self.client = None

            self.available = self.client is not None
        except Exception:
            # LangGraph SDK not installed — adapter remains unavailable
            self.available = False

    def run_workflow(self, workflow_name: str, state: dict) -> Any:
        """
        Submit a workflow to LangGraph and block until it completes.

        If the SDK is unavailable this raises RuntimeError so callers can
        fallback to local orchestration.
        """
        if not self.available or not self.client:
            raise RuntimeError("LangGraph SDK not available")

        # Placeholder: the exact client API depends on LangGraph SDK.
        # We assume a simple `run_workflow(name, state)` synchronous API.
        runner = getattr(self.client, "run_workflow", None)
        if not callable(runner):
            raise RuntimeError("LangGraph client does not expose run_workflow")

        return runner(workflow_name, state)


adapter = LangGraphAdapter()
