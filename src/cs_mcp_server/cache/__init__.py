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
Cache module for MCP servers.

This module provides caching mechanisms for metadata and other repository objects.
"""

# Use relative imports for direct script execution
from .metadata import (
    MetadataCache,
    ROOT_CLASS_TYPES,
    DOCUMENT,
    FOLDER,
    ANNOTATION,
    CUSTOM_OBJECT,
)
from .metadata_loader import (
    get_class_metadata_tool,
    get_root_class_description_tool,
)

__all__ = [
    "MetadataCache",
    "ROOT_CLASS_TYPES",
    "DOCUMENT",
    "FOLDER",
    "ANNOTATION",
    "CUSTOM_OBJECT",
    "get_class_metadata_tool",
    "get_root_class_description_tool",
]
