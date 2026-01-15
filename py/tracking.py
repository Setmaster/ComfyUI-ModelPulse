"""
ModelPulse - Core Tracking Logic

Extracts models from prompts and records usage statistics.
"""

from datetime import datetime, timedelta
from typing import Any

from .model_types import MODEL_LOADERS, LOADER_PATTERNS
from .storage import load_data, save_data, cleanup_old_usage_logs


class ModelTracker:
    """Tracks model usage across ComfyUI workflow executions."""

    def __init__(self):
        self._data: dict[str, Any] | None = None

    @property
    def data(self) -> dict[str, Any]:
        """Lazy-load data from storage."""
        if self._data is None:
            self._data = load_data()
        return self._data

    def _save(self) -> None:
        """Save current data to storage."""
        if self._data is not None:
            save_data(self._data)

    def extract_models_from_prompt(self, prompt: dict[str, Any]) -> list[dict[str, str]]:
        """
        Extract all model references from a ComfyUI prompt.

        Args:
            prompt: The prompt dictionary from ComfyUI execution

        Returns:
            List of dicts with 'category', 'name', and 'model_id' keys
        """
        models = []
        seen = set()  # Avoid duplicates within same prompt

        for node_id, node_data in prompt.items():
            class_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {})

            # Check standard loaders first
            if class_type in MODEL_LOADERS:
                category, input_keys = MODEL_LOADERS[class_type]
                extracted = self._extract_from_inputs(category, input_keys, inputs)
                for model in extracted:
                    if model["model_id"] not in seen:
                        seen.add(model["model_id"])
                        models.append(model)

            # Check pattern-based loaders for custom nodes
            elif "Loader" in class_type:
                extracted = self._extract_from_patterns(class_type, inputs)
                for model in extracted:
                    if model["model_id"] not in seen:
                        seen.add(model["model_id"])
                        models.append(model)

        return models

    def _extract_from_inputs(
        self, category: str, input_keys: str | list[str], inputs: dict[str, Any]
    ) -> list[dict[str, str]]:
        """Extract model names from node inputs."""
        models = []

        if isinstance(input_keys, str):
            input_keys = [input_keys]

        for key in input_keys:
            value = inputs.get(key)
            if value and isinstance(value, str):
                model_id = f"{category}/{value}"
                models.append({
                    "category": category,
                    "name": value,
                    "model_id": model_id,
                })

        return models

    def _extract_from_patterns(
        self, class_type: str, inputs: dict[str, Any]
    ) -> list[dict[str, str]]:
        """Extract models using pattern matching for custom node loaders."""
        models = []

        for pattern, category, possible_keys in LOADER_PATTERNS:
            if pattern.lower() in class_type.lower():
                for key in possible_keys:
                    value = inputs.get(key)
                    if value and isinstance(value, str):
                        model_id = f"{category}/{value}"
                        models.append({
                            "category": category,
                            "name": value,
                            "model_id": model_id,
                        })
                        break  # Found a match for this pattern
                break  # Only match first pattern

        return models

    def record_usage(self, models: list[dict[str, str]]) -> None:
        """
        Record usage for a list of models.

        Args:
            models: List of model dicts from extract_models_from_prompt
        """
        if not models:
            return

        now = datetime.utcnow()
        now_iso = now.isoformat() + "Z"
        today = now.date().isoformat()

        for model in models:
            model_id = model["model_id"]

            if model_id not in self.data["models"]:
                # New model - create entry
                self.data["models"][model_id] = {
                    "category": model["category"],
                    "name": model["name"],
                    "path": model_id,  # We don't have full path, use model_id
                    "first_used": now_iso,
                    "last_used": now_iso,
                    "usage_count": 0,
                    "usage_log": [],
                }

            model_data = self.data["models"][model_id]

            # Update timestamps and count
            model_data["last_used"] = now_iso
            model_data["usage_count"] += 1

            # Update daily usage log
            usage_log = model_data["usage_log"]
            if usage_log and usage_log[-1]["date"] == today:
                usage_log[-1]["count"] += 1
            else:
                usage_log.append({"date": today, "count": 1})

        self._save()

    def extract_and_record_models(self, prompt: dict[str, Any]) -> None:
        """
        Extract models from prompt and record their usage.

        This is the main entry point called from the PromptExecutor hook.
        """
        models = self.extract_models_from_prompt(prompt)
        self.record_usage(models)

    def get_usage_data(
        self,
        timeframe: str = "all",
        sort_by: str = "last_used",
        category: str | None = None,
    ) -> dict[str, Any]:
        """
        Get filtered and sorted usage data.

        Args:
            timeframe: "all", "month", or "week"
            sort_by: "last_used", "usage_count", or "name"
            category: Optional category filter

        Returns:
            Dict with 'models' list and 'metadata'
        """
        models_list = []
        now = datetime.utcnow()

        # Calculate timeframe boundaries
        if timeframe == "week":
            cutoff = now - timedelta(days=7)
        elif timeframe == "month":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None

        cutoff_date = cutoff.date().isoformat() if cutoff else None

        for model_id, model_data in self.data["models"].items():
            # Filter by category if specified
            if category and model_data["category"] != category:
                continue

            # Calculate timeframe-specific usage count
            if cutoff_date:
                timeframe_count = sum(
                    entry["count"]
                    for entry in model_data.get("usage_log", [])
                    if entry["date"] >= cutoff_date
                )
            else:
                timeframe_count = model_data["usage_count"]

            models_list.append({
                "model_id": model_id,
                "category": model_data["category"],
                "name": model_data["name"],
                "first_used": model_data["first_used"],
                "last_used": model_data["last_used"],
                "usage_count": model_data["usage_count"],
                "timeframe_count": timeframe_count,
            })

        # Sort the results
        if sort_by == "usage_count":
            models_list.sort(key=lambda x: x["timeframe_count"], reverse=True)
        elif sort_by == "name":
            models_list.sort(key=lambda x: x["name"].lower())
        else:  # last_used (default)
            models_list.sort(key=lambda x: x["last_used"], reverse=True)

        return {
            "models": models_list,
            "metadata": self.data["metadata"],
            "timeframe": timeframe,
            "sort_by": sort_by,
        }

    def get_model_detail(self, model_id: str) -> dict[str, Any] | None:
        """
        Get detailed usage data for a specific model.

        Args:
            model_id: The model identifier (category/filename)

        Returns:
            Model data dict or None if not found
        """
        model_data = self.data["models"].get(model_id)
        if not model_data:
            return None

        return {
            "model_id": model_id,
            **model_data,
        }

    def reset(self) -> None:
        """Reset all tracking data."""
        from .storage import create_empty_data

        self._data = create_empty_data()
        self._save()

    def cleanup(self, max_days: int = 365) -> None:
        """Clean up old usage logs."""
        self._data = cleanup_old_usage_logs(self.data, max_days)
        self._save()
