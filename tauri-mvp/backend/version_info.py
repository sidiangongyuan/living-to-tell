"""Shared version metadata for the Tauri backend surface."""
from __future__ import annotations

import os

APP_DISPLAY_NAME = "Living to Tell"
APP_VERSION = os.environ.get("LIVING_TO_TELL_APP_VERSION", "0.1.36")
API_VERSION = "2.0.0"
API_CAPABILITIES = [
    "data_location",
    "ai_chat_settings",
    "ai_task_presets",
    "ai_profiles",
    "ai_jobs",
    "ai_task_compare",
    "ai_task_compare_stream",
    "motif_star_map",
    "motif_ai_enrichment",
    "motif_ai_enrichment_jobs",
    "update_check",
    "article_versions",
    "collection_outline",
    "sample_project",
]
