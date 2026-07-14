"""Crawler modules."""

from .base import BaseCrawler, CrawlResult, ContentType, CrawlerConfig

# Code Hosting
from .github import GitHubCrawler
from .gitlab import GitLabCrawler
from .bitbucket import BitbucketCrawler
from .codeberg import GiteaCrawler, CodebergCrawler, GiteaDotComCrawler
from .sourceforge import SourceForgeCrawler
from .launchpad import LaunchpadCrawler
from .savannah import SavannahCrawler
from .apache import ApacheCrawler
from .pagure import PagureCrawler

# AI/ML Platforms
from .huggingface import HuggingFaceCrawler
from .pastebin import PastebinCrawler

# Academic
from .academic import ArxivCrawler, SemanticScholarCrawler

# Q&A/Community
from .stackoverflow import StackOverflowCrawler
from .reddit import RedditCrawler
from .hackernews import HackerNewsCrawler

# Documentation/Content
from .rss import RSSCrawler
from .wikipedia import WikipediaCrawler

# Messaging
from .discord import DiscordCrawler, SlackCrawler

# Productivity
from .notion import NotionCrawler
from .jira import JiraCrawler

# Web
from .webscraper import WebScraperCrawler

# Package Registries
from .pypi import PyPICrawler
from .npm_registry import NpmCrawler
from .crates import CratesCrawler
from .go_dev import GoDevCrawler
from .maven import MavenCrawler
from .nuget import NugetCrawler
from .rubygems import RubyGemsCrawler

# Archives
from .internetarchive import InternetArchiveCrawler

__all__ = [
    # Base
    "BaseCrawler", "CrawlResult", "ContentType", "CrawlerConfig",
    
    # Code Hosting
    "GitHubCrawler", "GitLabCrawler", "BitbucketCrawler",
    "GiteaCrawler", "CodebergCrawler", "GiteaDotComCrawler",
    "SourceForgeCrawler", "LaunchpadCrawler", "SavannahCrawler",
    "ApacheCrawler", "PagureCrawler",
    
    # AI/ML
    "HuggingFaceCrawler", "PastebinCrawler",
    
    # Academic
    "ArxivCrawler", "SemanticScholarCrawler",
    
    # Q&A/Community
    "StackOverflowCrawler", "RedditCrawler", "HackerNewsCrawler",
    
    # Documentation
    "RSSCrawler", "WikipediaCrawler",
    
    # Messaging
    "DiscordCrawler", "SlackCrawler",
    
    # Productivity
    "NotionCrawler", "JiraCrawler",
    
    # Web
    "WebScraperCrawler",
    
    # Package Registries
    "PyPICrawler", "NpmCrawler", "CratesCrawler",
    "GoDevCrawler", "MavenCrawler", "NugetCrawler", "RubyGemsCrawler",
    
    # Archives
    "InternetArchiveCrawler",
]
