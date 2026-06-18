"""Tools available to agents in the LangGraph.

Agents can call `lookup_dictionary` to retrieve business-dictionary context entries
for a given table/field. The tool initially returns empty (stub); Phase 5 wires it to
the repository layer.
"""

from langchain_core.tools import tool

from app.core.logging import get_logger

log = get_logger(__name__)


@tool
def lookup_dictionary(table_name: str) -> str:
    """Look up a table in the business dictionary.

    Args:
        table_name: Name of the table (e.g., "customers", "transactions").

    Returns:
        Formatted text describing the table's fields and business context.
        Returns empty string if the table is not found.
    """
    return ""
