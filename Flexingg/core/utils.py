"""
REMOVED: This file was a compatibility shim re-exporting helpers from the refactored modules.
Helpers have been moved to focused modules under `core/`:
  - `core.liftosaur_client` (liftosaur_download)
  - `core.formatters` (convert_timestamp_to_datetime, format_exercise_name, parse_weight)
  - `core.aggregation_service` (aggregation and summary helpers)

Update imports accordingly. This file now raises on import to make any remaining references explicit during runtime.
"""

raise ImportError(
    "core/utils.py compatibility shim removed. "
    "Import helpers from their new locations, e.g.:\n\n"
    "  from core.liftosaur_client import liftosaur_download\n"
    "  from core.formatters import convert_timestamp_to_datetime, format_exercise_name, parse_weight\n"
    "  from core.aggregation_service import get_user_fitness_summary, get_aggregated_steps\n\n"
    "Replace imports and rerun tests."
)