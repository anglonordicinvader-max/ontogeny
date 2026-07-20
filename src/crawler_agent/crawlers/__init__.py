"""Ontogeny Knowledge Acquisition System — modular acquisition engines for external evidence.

This package provides the acquisition engine layer for Ontogeny's cognitive architecture.
Each module implements an evidence acquisition adapter for a specific data source.
"""

# Acquisition system
# Academic
from .academic import ArxivCrawler, SemanticScholarCrawler
from .acquisition import (
    AcquisitionManager,
    ClaimValidator,
    CrawlObservability,
    DomainPolicies,
    DomainPolicy,
    EvidenceDocument,
    EvidenceStore,
    ProxyEndpoint,
    ProxyManager,
    RequestManager,
    ResearchObjective,
    ResearchPlan,
    ResearchPlanner,
    RevalidationScheduler,
    SourceCategory,
    SourceQualityScorer,
)

# Additional
from .additional import (
    GitHubCodeSearchCrawler,
    GitHubTrendingCrawler,
    HuggingFaceHubCrawler,
    PapersWithCodeCrawler,
)
from .apache import ApacheCrawler
from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult
from .bitbucket import BitbucketCrawler
from .codeberg import CodebergCrawler, GiteaCrawler, GiteaDotComCrawler
from .crates import CratesCrawler

# Messaging
from .discord import DiscordCrawler, SlackCrawler

# Code Hosting
from .github import GitHubCrawler
from .gitlab import GitLabCrawler
from .go_dev import GoDevCrawler
from .hackernews import HackerNewsCrawler

# AI/ML Platforms
from .huggingface import HuggingFaceCrawler

# Archives
from .internetarchive import InternetArchiveCrawler
from .jira import JiraCrawler
from .launchpad import LaunchpadCrawler
from .maven import MavenCrawler

# Productivity
from .notion import NotionCrawler
from .npm_registry import NpmCrawler
from .nuget import NugetCrawler
from .pagure import PagureCrawler
from .pastebin import PastebinCrawler

# Package Registries
from .pypi import PyPICrawler
from .reddit import RedditCrawler

# Documentation/Content
from .rss import RSSCrawler
from .rubygems import RubyGemsCrawler
from .savannah import SavannahCrawler
from .sourceforge import SourceForgeCrawler

# Q&A/Community
from .stackoverflow import StackOverflowCrawler

# Web
from .webscraper import WebScraperCrawler
from .wikipedia import WikipediaCrawler

__all__ = [
    # Base
    "BaseCrawler",
    "CrawlResult",
    "ContentType",
    "CrawlerConfig",
    # Code Hosting
    "GitHubCrawler",
    "GitLabCrawler",
    "BitbucketCrawler",
    "GiteaCrawler",
    "CodebergCrawler",
    "GiteaDotComCrawler",
    "SourceForgeCrawler",
    "LaunchpadCrawler",
    "SavannahCrawler",
    "ApacheCrawler",
    "PagureCrawler",
    # AI/ML
    "HuggingFaceCrawler",
    "PastebinCrawler",
    # Academic
    "ArxivCrawler",
    "SemanticScholarCrawler",
    # Q&A/Community
    "StackOverflowCrawler",
    "RedditCrawler",
    "HackerNewsCrawler",
    # Documentation
    "RSSCrawler",
    "WikipediaCrawler",
    # Messaging
    "DiscordCrawler",
    "SlackCrawler",
    # Productivity
    "NotionCrawler",
    "JiraCrawler",
    # Web
    "WebScraperCrawler",
    # Package Registries
    "PyPICrawler",
    "NpmCrawler",
    "CratesCrawler",
    "GoDevCrawler",
    "MavenCrawler",
    "NugetCrawler",
    "RubyGemsCrawler",
    # Archives
    "InternetArchiveCrawler",
    # Additional
    "GitHubCodeSearchCrawler",
    "PapersWithCodeCrawler",
    "HuggingFaceHubCrawler",
    "GitHubTrendingCrawler",
]
