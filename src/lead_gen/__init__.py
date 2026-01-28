"""
Lead-Gen: Enterprise-grade lead generation platform with AI-powered outreach.

This package provides a complete solution for:
- Scraping business leads from Google Places API
- Generating personalized AI outreach messages
- Enriching leads with email addresses via Hunter.io
- Exporting results to Google Sheets

Example:
    >>> from lead_gen import LeadGenWorkflow
    >>> workflow = LeadGenWorkflow.from_yaml("workflows/slovakia_dentists.yaml")
    >>> await workflow.run()
"""

from importlib.metadata import version

__version__ = version("lead-gen")
__all__ = ["__version__"]
