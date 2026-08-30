"""Vercel serverless entrypoint.

Vercel expects a Python file under api/ exporting a variable named `app`.
The real application lives in backend/app (a normal FastAPI project you can
also run locally with `uvicorn app.main:app`), so this just makes that
package importable and re-exports it — no logic lives here.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402
