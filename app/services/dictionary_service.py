"""Build dictionary context for stages."""

from app.core.logging import get_logger
from app.models.analysis import Analysis
from app.models.enums import AnalysisType
from app.repositories.dictionary_repo import (
    CuratedDictionaryRepo,
    VendorDictionaryRepo,
)

log = get_logger(__name__)


async def build_context_text(analysis: Analysis) -> str:
    """Build formatted dictionary context for an analysis.

    Returns a block of text describing available tables/fields based on the
    analysis type (curated or vendor).
    """
    if not analysis.curated_tables and not analysis.vendor_details:
        return ""

    text_parts = []

    if analysis.analysis_type == AnalysisType.CURATED:
        if analysis.curated_tables:
            repo = CuratedDictionaryRepo()
            entries = await repo.list_by_tables(analysis.curated_tables)
            if entries:
                text_parts.append("## Curated Business Dictionary\n")
                for entry in entries:
                    text_parts.append(
                        f"**{entry.table_name}.{entry.field_name}**\n"
                        f"  Type: {entry.data_type}\n"
                        f"  Description: {entry.business_description}\n"
                        f"  Sample: {entry.sample_values}\n"
                    )

    elif analysis.analysis_type == AnalysisType.VENDOR:
        if analysis.vendor_details:
            repo = VendorDictionaryRepo()
            for vendor_detail in analysis.vendor_details:
                entries = await repo.list_by_vendor_and_layouts(
                    vendor_detail.vendor_name, vendor_detail.layout
                )
                if entries:
                    text_parts.append(f"## {vendor_detail.vendor_name} Data Dictionary\n")
                    for entry in entries:
                        text_parts.append(
                            f"**{entry.field_name}** ({entry.file_category})\n"
                            f"  Type: {entry.data_type}\n"
                            f"  Description: {entry.business_description}\n"
                            f"  Protected: {entry.protected_data_flag}\n"
                            f"  Sample: {entry.sample_values}\n"
                        )

    return "\n".join(text_parts)
