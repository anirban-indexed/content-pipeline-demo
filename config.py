"""
config.py — Loads environment variables and exposes them as constants.
Provides load_client_profile() to load per-client settings from clients/.
"""

from __future__ import annotations
import os
import json
from dotenv import load_dotenv

load_dotenv(override=True)

# Anthropic
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Ahrefs
AHREFS_API_KEY: str = os.getenv("AHREFS_API_KEY", "")

# Serper
SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")

# NeuronWriter — PENDING
NEURONWRITER_API_KEY: str = os.getenv("NEURONWRITER_API_KEY", "")
NEURONWRITER_ENABLED: bool = bool(NEURONWRITER_API_KEY)

# Root directory of the project
ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))

# Clients directory
CLIENTS_DIR: str = os.path.join(ROOT_DIR, "clients")


def load_client_profile(client_name: str) -> dict:
    """
    Load a client profile from clients/{client_name}/profile.json.
    Resolves all path values relative to ROOT_DIR and injects them
    as '_'-prefixed keys for use by pipeline modules.
    Raises FileNotFoundError if the profile does not exist.
    """
    profile_path = os.path.join(CLIENTS_DIR, client_name, "profile.json")
    if not os.path.exists(profile_path):
        available = [
            d for d in os.listdir(CLIENTS_DIR)
            if os.path.isdir(os.path.join(CLIENTS_DIR, d))
        ] if os.path.isdir(CLIENTS_DIR) else []
        raise FileNotFoundError(
            f"Client profile not found: {profile_path}\n"
            f"Available clients: {available}"
        )

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # Inject absolute paths
    profile["_client_dir"] = os.path.join(CLIENTS_DIR, client_name)
    profile["_system_prompt_path"] = os.path.join(CLIENTS_DIR, client_name, "system_prompt.md")
    profile["_brief_format_path"] = os.path.join(CLIENTS_DIR, client_name, "brief_format.md")
    profile["_outputs_dir"] = os.path.join(ROOT_DIR, profile.get("outputs_dir", f"outputs/{client_name}"))
    profile["_inputs_dir"] = os.path.join(ROOT_DIR, profile.get("inputs_dir", f"inputs/{client_name}"))

    # Resolve context file paths to absolute
    ctx = profile.get("context_files", {})
    resolved_ctx = {}
    for key, val in ctx.items():
        if isinstance(val, list):
            resolved_ctx[key] = [os.path.join(ROOT_DIR, p) for p in val]
        elif val and val != "TODO":
            resolved_ctx[key] = os.path.join(ROOT_DIR, val)
        else:
            resolved_ctx[key] = val
    profile["_context_files"] = resolved_ctx

    return profile


def validate(profile: dict | None = None) -> list[str]:
    errors = []
    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is missing from .env")
    if not NEURONWRITER_ENABLED:
        print("INFO: NeuronWriter API key not set. NeuronWriter integration is disabled.")

    if profile:
        ctx = profile.get("_context_files", {})
        handbook = ctx.get("editorial_handbook", "")
        if handbook and handbook != "TODO" and not os.path.exists(handbook):
            errors.append(f"Context file missing: {handbook}")
        for path in ctx.get("example_articles", []):
            if path and path != "TODO" and not os.path.exists(path):
                errors.append(f"Context file missing: {path}")

    return errors
