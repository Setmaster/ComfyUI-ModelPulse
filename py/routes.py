"""
ModelPulse - API Routes

Custom HTTP routes for the ModelPulse extension.
"""

from aiohttp import web
from urllib.parse import unquote

from .tracking import ModelTracker


def setup_routes(routes, tracker: ModelTracker) -> None:
    """
    Register ModelPulse API routes.

    Args:
        routes: PromptServer.instance.routes
        tracker: The ModelTracker instance
    """

    @routes.get("/modelpulse/usage")
    async def get_usage_data(request: web.Request) -> web.Response:
        """
        Get all model usage data.

        Query parameters:
            timeframe: "all" (default), "month", or "week"
            sort: "last_used" (default), "usage_count", or "name"
            category: Optional category filter
        """
        timeframe = request.query.get("timeframe", "all")
        sort_by = request.query.get("sort", "last_used")
        category = request.query.get("category")

        # Validate parameters
        if timeframe not in ("all", "month", "week"):
            timeframe = "all"
        if sort_by not in ("last_used", "usage_count", "name"):
            sort_by = "last_used"

        data = tracker.get_usage_data(
            timeframe=timeframe,
            sort_by=sort_by,
            category=category,
        )
        return web.json_response(data)

    @routes.get("/modelpulse/model/{model_id:.*}")
    async def get_model_detail(request: web.Request) -> web.Response:
        """
        Get detailed usage data for a specific model.

        Path parameters:
            model_id: The model identifier (category/filename)
        """
        model_id = unquote(request.match_info["model_id"])
        data = tracker.get_model_detail(model_id)

        if data is None:
            return web.json_response(
                {"error": "Model not found"},
                status=404,
            )

        return web.json_response(data)

    @routes.get("/modelpulse/categories")
    async def get_categories(request: web.Request) -> web.Response:
        """Get list of model categories with counts."""
        from .model_types import MODEL_CATEGORIES

        usage_data = tracker.get_usage_data()
        category_counts: dict[str, int] = {}

        for model in usage_data["models"]:
            cat = model["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        categories = []
        for cat_id, cat_info in MODEL_CATEGORIES.items():
            categories.append({
                "id": cat_id,
                "name": cat_info["name"],
                "icon": cat_info["icon"],
                "count": category_counts.get(cat_id, 0),
            })

        # Sort by count descending
        categories.sort(key=lambda x: x["count"], reverse=True)

        return web.json_response({"categories": categories})

    @routes.post("/modelpulse/reset")
    async def reset_tracking(request: web.Request) -> web.Response:
        """
        Reset all tracking data.

        Requires confirmation in request body: {"confirm": true}
        """
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"error": "Invalid JSON body"},
                status=400,
            )

        if body.get("confirm") is not True:
            return web.json_response(
                {"error": "Confirmation required. Send {\"confirm\": true}"},
                status=400,
            )

        tracker.reset()
        return web.json_response({"status": "ok", "message": "Tracking data reset"})

    @routes.post("/modelpulse/cleanup")
    async def cleanup_old_data(request: web.Request) -> web.Response:
        """
        Clean up old usage log entries.

        Optional body parameter: {"max_days": 365}
        """
        try:
            body = await request.json()
            max_days = body.get("max_days", 365)
        except Exception:
            max_days = 365

        if not isinstance(max_days, int) or max_days < 1:
            max_days = 365

        tracker.cleanup(max_days=max_days)
        return web.json_response({
            "status": "ok",
            "message": f"Cleaned up entries older than {max_days} days",
        })
