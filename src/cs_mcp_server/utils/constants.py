# Copyright contributors to the IBM Core Content Services MCP Server project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Constants used across the MCP server tools.

This module centralizes magic numbers and string literals to improve
maintainability and reduce duplication across the codebase.

Constants are organized by category for easy navigation and maintenance.
"""

# ============================================================================
# DEFAULT CLASS IDENTIFIERS
# ============================================================================
# Used when no specific class is provided by the user

DEFAULT_DOCUMENT_CLASS = "Document"
"""Default class identifier for document operations."""

DEFAULT_FOLDER_CLASS = "Folder"
"""Default class identifier for folder operations."""

VERSION_SERIES_CLASS = "VersionSeries"
"""Class identifier for version series objects."""


# ============================================================================
# ANNOTATION CLASS NAMES
# ============================================================================

TEXT_EXTRACT_ANNOTATION_CLASS = "TxeTextExtractAnnotation"
"""Class name for text extract annotations."""


# ============================================================================
# LEGAL HOLD CLASS NAMES
# ============================================================================

CM_HOLD_CLASS = "CmHold"
"""Class name for legal hold objects."""

CM_HOLD_RELATIONSHIP_CLASS = "CmHoldRelationship"
"""Class name for hold relationship objects."""


# ============================================================================
# VECTOR SEARCH CLASS NAMES
# ============================================================================

GENAI_VECTOR_QUERY_CLASS = "GenaiVectorQuery"
"""Class name for GenAI vector query objects."""


# ============================================================================
# PROPERTY NAMES
# ============================================================================

ID_PROPERTY = "Id"
"""Standard ID property name."""

HELD_OBJECT_PROPERTY = "HeldObject"
"""Property name for held objects in legal hold relationships."""

EXCLUDED_PROPERTY_NAMES = ["GenaiDateIndexed", "GenaiWatsonxSummary"]
"""Property names to exclude from class-specific property lists."""


# ============================================================================
# SCORING THRESHOLDS AND MULTIPLIERS
# ============================================================================
# Used in fuzzy matching algorithms across classes.py and search.py

# Exact Match Scores
EXACT_SYMBOLIC_NAME_MATCH_SCORE = 20
"""Score awarded for exact symbolic name matches."""

EXACT_DISPLAY_NAME_MATCH_SCORE = 15
"""Score awarded for exact display name matches."""

# Substring Match Scores
SYMBOLIC_NAME_SUBSTRING_SCORE = 10
"""Score awarded for symbolic name substring matches."""

DISPLAY_NAME_SUBSTRING_SCORE = 8
"""Score awarded for display name substring matches."""

DESCRIPTIVE_TEXT_SUBSTRING_SCORE = 3
"""Score awarded for descriptive text substring matches."""

# Similarity Thresholds
HIGH_SIMILARITY_THRESHOLD = 0.7
"""Threshold for considering two words highly similar (70% match)."""

MEDIUM_SIMILARITY_THRESHOLD = 0.5
"""Threshold for considering two words moderately similar (50% match)."""

DESCRIPTION_HIGH_SIMILARITY_THRESHOLD = 0.8
"""Higher threshold for description text matching (80% match)."""

# Similarity Score Multipliers
HIGH_SIMILARITY_MULTIPLIER = 5
"""Multiplier for high similarity matches in symbolic names."""

MEDIUM_SIMILARITY_MULTIPLIER = 3
"""Multiplier for medium similarity matches in symbolic names."""

DISPLAY_HIGH_SIMILARITY_MULTIPLIER = 4
"""Multiplier for high similarity matches in display names."""

DISPLAY_MEDIUM_SIMILARITY_MULTIPLIER = 2
"""Multiplier for medium similarity matches in display names."""

DESCRIPTION_SIMILARITY_MULTIPLIER = 2
"""Multiplier for similarity matches in descriptive text."""

# Property Matching Scores
PROPERTY_SYMBOLIC_NAME_SCORE = 2
"""Score for matching property symbolic names."""

PROPERTY_DISPLAY_NAME_SCORE = 1.5
"""Score for matching property display names."""

# Keyword Coverage
KEYWORD_COVERAGE_BONUS = 5
"""Bonus score for matching multiple keywords."""

# Score Normalization
SCORE_NORMALIZATION_EXPONENT = 0.5
"""Exponent for normalizing scores (square root)."""

MAX_SCORE_CAP = 100.0
"""Maximum allowed score to prevent extreme values."""

# Word Similarity (used in scoring.py)
SUBSTRING_SIMILARITY_MULTIPLIER = 0.9
"""Multiplier for substring containment similarity."""

PREFIX_SIMILARITY_MULTIPLIER = 0.7
"""Multiplier for prefix matching similarity."""


# ============================================================================
# SEARCH AND RESULT LIMITS
# ============================================================================

MAX_SEARCH_RESULTS = 20
"""Maximum number of search results to return."""

MAX_CLASS_MATCHES = 3
"""Maximum number of class matches to return from determine_class."""

LRU_CACHE_SIZE = 1000
"""Maximum size for LRU cache in tokenization."""


# ============================================================================
# VERSION STATUS CODES
# ============================================================================
# FileNet version status values

VERSION_STATUS_RELEASED = 1
"""Version status code for released documents."""

VERSION_STATUS_IN_PROCESS = 2
"""Version status code for in-process documents (current version, not released)."""

VERSION_STATUS_RESERVATION = 3
"""Version status code for reservation (checked out)."""

VERSION_STATUS_SUPERSEDED = 4
"""Version status code for superseded documents."""


# ============================================================================
# DATA TYPES
# ============================================================================
# Property data type identifiers

DATA_TYPE_STRING = "STRING"
"""String data type identifier."""

DATA_TYPE_INTEGER = "INTEGER"
"""Integer data type identifier."""

DATA_TYPE_LONG = "LONG"
"""Long integer data type identifier."""

DATA_TYPE_FLOAT = "FLOAT"
"""Float data type identifier."""

DATA_TYPE_DOUBLE = "DOUBLE"
"""Double data type identifier."""

DATA_TYPE_BOOLEAN = "BOOLEAN"
"""Boolean data type identifier."""

DATA_TYPE_DATETIME = "DATETIME"
"""DateTime data type identifier."""

DATA_TYPE_DATE = "DATE"
"""Date data type identifier."""

DATA_TYPE_TIME = "TIME"
"""Time data type identifier."""

DATA_TYPE_OBJECT = "OBJECT"
"""Object data type identifier."""

CARDINALITY_LIST = "LIST"
"""List cardinality identifier."""


# ============================================================================
# SQL OPERATORS
# ============================================================================

SQL_LIKE_OPERATOR = "LIKE"
"""SQL LIKE operator for pattern matching."""

OPERATOR_CONTAINS = "CONTAINS"
"""Custom operator for substring matching."""

OPERATOR_STARTS = "STARTS"
"""Custom operator for prefix matching."""

OPERATOR_ENDS = "ENDS"
"""Custom operator for suffix matching."""


# ============================================================================
# TEXT FORMATTING
# ============================================================================

TEXT_EXTRACT_SEPARATOR = "\n\n"
"""Separator used between multiple text extracts."""


# ============================================================================
# VECTOR SEARCH PARAMETERS
# ============================================================================

DEFAULT_MAX_CHUNKS = 100
"""Default maximum number of chunks for vector search."""

DEFAULT_RELEVANCE_SCORE = 1.55
"""Default relevance score threshold for vector search results."""


# ============================================================================
# GUID FORMAT CONSTANTS
# ============================================================================

GUID_HEX_LENGTH = 32
"""Expected length of a GUID in hexadecimal format (without hyphens)."""

GUID_VALID_CHARS = "0123456789abcdefABCDEF"
"""Valid characters in a hexadecimal GUID string."""

# GUID slice indices for 8-4-4-4-12 format
GUID_PART1_START = 0
GUID_PART1_END = 8
GUID_PART2_START = 8
GUID_PART2_END = 12
GUID_PART3_START = 12
GUID_PART3_END = 16
GUID_PART4_START = 16
GUID_PART4_END = 20
GUID_PART5_START = 20
GUID_PART5_END = 32


# ============================================================================
# ERROR HANDLING
# ============================================================================

TRACEBACK_LIMIT = 15
"""Default limit for traceback depth in error logging."""

# ============================================================================
# VERSION NUMBER DEFAULTS
# ============================================================================

INITIAL_MAJOR_VERSION = 0
"""Initial major version number for new documents."""

INITIAL_MINOR_VERSION = 1
"""Initial minor version number for new documents."""
