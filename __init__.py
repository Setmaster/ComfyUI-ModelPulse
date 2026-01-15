"""
ModelPulse - ComfyUI Model Usage Tracker

Tracks model usage frequency to help identify abandoned or underutilized models.
"""

from .py.tracking import ModelTracker
from .py.routes import setup_routes

# Global tracker instance
tracker = ModelTracker()

# Store original execute for restoration if needed
_original_execute = None


def init_tracking():
    """Initialize the tracking hook on PromptExecutor."""
    global _original_execute

    try:
        from execution import PromptExecutor
    except ImportError:
        print("[ModelPulse] Warning: Could not import PromptExecutor. Tracking disabled.")
        return

    _original_execute = PromptExecutor.execute

    def tracked_execute(self, prompt, prompt_id, extra_data={}, execute_outputs=[]):
        """Wrapper that tracks model usage before execution."""
        try:
            # Extract and record models from the prompt
            tracker.extract_and_record_models(prompt)
        except Exception as e:
            # Don't let tracking errors break execution
            print(f"[ModelPulse] Error tracking models: {e}")

        # Call original execute (synchronous)
        return _original_execute(self, prompt, prompt_id, extra_data, execute_outputs)

    PromptExecutor.execute = tracked_execute
    print("[ModelPulse] Tracking initialized")


def init_routes():
    """Initialize API routes."""
    try:
        from server import PromptServer

        if PromptServer.instance is None:
            print("[ModelPulse] Warning: PromptServer not initialized. Routes disabled.")
            return

        setup_routes(PromptServer.instance.routes, tracker)
        print("[ModelPulse] API routes registered")

    except ImportError:
        print("[ModelPulse] Warning: Could not import PromptServer. Routes disabled.")
    except Exception as e:
        print(f"[ModelPulse] Error registering routes: {e}")


# Initialize on module load
init_tracking()
init_routes()


# ComfyUI node registration (empty - we don't add any nodes)
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Tell ComfyUI where to find our JavaScript files
WEB_DIRECTORY = "./js"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
    "tracker",
]
