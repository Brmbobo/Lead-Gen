"""
Tools layer for Lead-Gen.

Provides modular, composable tools for:
- Scraping leads from Google Places
- Generating AI outreach messages
- Exporting data to Google Sheets
- Enriching leads with email data
"""

from lead_gen.tools.base import BaseTool, ToolResult, ToolContext
from lead_gen.tools.scrape_leads import ScrapeLeadsTool
from lead_gen.tools.generate_outreach import GenerateOutreachTool
from lead_gen.tools.export_to_sheets import ExportToSheetsTool
from lead_gen.tools.enrich_email import EnrichEmailTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolContext",
    "ScrapeLeadsTool",
    "GenerateOutreachTool",
    "ExportToSheetsTool",
    "EnrichEmailTool",
]
