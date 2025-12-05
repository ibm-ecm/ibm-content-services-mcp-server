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
Utilities module for MCP servers.

This module provides common utility functions and models.
"""

from .common import (
    ToolError,
    SearchOperator,
    SearchProperty,
    SearchParameters,
    CachePropertyDescription,
    ClassDescriptionData,
    CacheClassDescriptionData,
    CachePropertyDescriptionBooleanData,
    CachePropertyDescriptionDateTimeData,
    CachePropertyDescriptionFloat64Data,
    CachePropertyDescriptionIdData,
    CachePropertyDescriptionInteger32Data,
    CachePropertyDescriptionStringData,
)
from .model.admin import HoldRelationship
from .model.propertyBase import TypeID, Cardinality
from .model.core import Document, Annotation
from .model.coreInput import (
    DocumentPropertiesInput,
    SubCheckinActionInput,
    SubCheckoutActionInput,
    ReservationType,
    ContentElementType,
    BaseContentElementInput,
    ContentElementListInput,
    InsertDependentActionInput,
    SubContentTransferInput,
)

# Import commonly used constants for convenience
from .constants import (
    DEFAULT_DOCUMENT_CLASS,
    DEFAULT_FOLDER_CLASS,
    VERSION_SERIES_CLASS,
    TEXT_EXTRACT_ANNOTATION_CLASS,
    CM_HOLD_CLASS,
    CM_HOLD_RELATIONSHIP_CLASS,
    EXACT_SYMBOLIC_NAME_MATCH_SCORE,
    EXACT_DISPLAY_NAME_MATCH_SCORE,
    HIGH_SIMILARITY_THRESHOLD,
    MEDIUM_SIMILARITY_THRESHOLD,
    MAX_SEARCH_RESULTS,
    TRACEBACK_LIMIT,
)

__all__ = [
    "ToolError",
    "SearchOperator",
    "SearchProperty",
    "SearchParameters",
    "TypeID",
    "Cardinality",
    "CachePropertyDescription",
    "ClassDescriptionData",
    "CacheClassDescriptionData",
    "CachePropertyDescriptionBooleanData",
    "CachePropertyDescriptionDateTimeData",
    "CachePropertyDescriptionFloat64Data",
    "CachePropertyDescriptionIdData",
    "CachePropertyDescriptionInteger32Data",
    "CachePropertyDescriptionStringData",
    "HoldRelationship",
    "Document",
    "Annotation",
    "DocumentPropertiesInput",
    "SubCheckinActionInput",
    "SubCheckoutActionInput",
    "ReservationType",
    "ContentElementType",
    "BaseContentElementInput",
    "ContentElementListInput",
    "InsertDependentActionInput",
    "SubContentTransferInput",
    # Constants
    "DEFAULT_DOCUMENT_CLASS",
    "DEFAULT_FOLDER_CLASS",
    "VERSION_SERIES_CLASS",
    "TEXT_EXTRACT_ANNOTATION_CLASS",
    "CM_HOLD_CLASS",
    "CM_HOLD_RELATIONSHIP_CLASS",
    "EXACT_SYMBOLIC_NAME_MATCH_SCORE",
    "EXACT_DISPLAY_NAME_MATCH_SCORE",
    "HIGH_SIMILARITY_THRESHOLD",
    "MEDIUM_SIMILARITY_THRESHOLD",
    "MAX_SEARCH_RESULTS",
    "TRACEBACK_LIMIT",
]
