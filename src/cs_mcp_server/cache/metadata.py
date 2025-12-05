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

from typing import Dict, List, Optional
import json

# Use absolute imports instead of relative imports
from cs_mcp_server.utils import CacheClassDescriptionData

# Define common class names as constants for convenience
DOCUMENT = "Document"
FOLDER = "Folder"
ANNOTATION = "Annotation"
CUSTOM_OBJECT = "CustomObject"

# These are the system root classes. That we support.
# These are also the root classes that have a table
# associated with them in the database. If we support any Abstract classes, such as
# CmAbstractPersistable, this will change and we will have to dynamically generate
# part of the list of root classes to include the immediate subclasses of a given Abstract
# system root class.
SYSTEM_ROOT_CLASS_TYPES = [DOCUMENT, FOLDER, ANNOTATION, CUSTOM_OBJECT]
# Root class types that we want to include statically. For now these are the same
# as the system root classes.
ROOT_CLASS_TYPES = SYSTEM_ROOT_CLASS_TYPES


class MetadataCache:
    """
    Class to manage the metadata cache for repository classes and their properties.
    Provides methods to access and manipulate the cache.
    """

    def __init__(self):
        """Initialize the metadata cache with known root classes."""
        self._cache = {}

        # Initialize root classes
        for root_class in ROOT_CLASS_TYPES:
            if root_class not in self._cache:
                self._cache[root_class] = {}

    def reset(self):
        """Reset the cache to its initial state."""
        self.__init__()

    def ensure_root_class_exists(self, class_name: str) -> None:
        """
        Ensures that a root class exists in the cache.

        Args:
            class_name: The name of the root class to ensure exists
        """
        if class_name not in self._cache:
            self._cache[class_name] = {}

    def get_class_cache(self, root_class: str) -> Dict:
        """
        Get the cache for a specific root class.

        Args:
            root_class: The root class name

        Returns:
            The cache dictionary for the specified root class
        """
        self.ensure_root_class_exists(root_class)
        return self._cache[root_class]

    def get_class_data(
        self, root_class: str, class_name: str
    ) -> Optional[CacheClassDescriptionData]:
        """
        Get class data from the cache.

        Args:
            root_class: The root class name
            class_name: The class name to retrieve

        Returns:
            ContentClassData if found, None otherwise
        """
        if root_class in self._cache and class_name in self._cache[root_class]:
            return self._cache[root_class][class_name]
        return None

    def set_class_data(
        self, root_class: str, class_name: str, class_data: CacheClassDescriptionData
    ) -> None:
        """
        Store class data in the cache.

        Args:
            root_class: The root class name
            class_name: The class name to store
            class_data: The class data to store
        """
        self.ensure_root_class_exists(root_class)
        self._cache[root_class][class_name] = class_data

    def find_root_class_for_class(self, class_name: str) -> Optional[str]:
        """
        Find which root class a class belongs to.

        Args:
            class_name: The class name to find

        Returns:
            The root class name if found, None otherwise
        """
        for root_class, classes in self._cache.items():
            if class_name in classes:
                return root_class
        return None

    def get_all_keys_for_root(self, root_class: str) -> List[str]:
        """
        Get all symbolic name of classes for a root class.

        Args:
            root_class: The root class name

        Returns:
            List of symbolic names of classes
        """
        self.ensure_root_class_exists(root_class)
        return list(self._cache[root_class].keys())

    def get_root_class_keys(self) -> List[str]:
        """
        Get all root class keys from the cache.

        Returns:
            List of root class names (keys of the cache)
        """
        return list(self._cache.keys())

    def print_structure(self):
        """Print the structure of the cache for debugging purposes."""
        print("\n=== CACHE STRUCTURE (JSON) ===")

        # Create a serializable representation of the cache
        cache_json = {}
        for root_class, classes in self._cache.items():
            cache_json[root_class] = {}
            for class_name, class_data in classes.items():
                cache_json[root_class][class_name] = {
                    "display_name": class_data.display_name,
                    "descriptive_text": class_data.descriptive_text,
                    "properties_count": len(class_data.properties),
                }

        # Print as formatted JSON
        print(json.dumps(cache_json, indent=2))
        print("============================\n")
