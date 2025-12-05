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

from logging import Logger


import logging
from typing import Union

# Use absolute imports instead of relative imports
from cs_mcp_server.cache import metadata
from cs_mcp_server.cache.metadata import SYSTEM_ROOT_CLASS_TYPES
from cs_mcp_server.utils.common import (
    CacheClassDescriptionData,
    CachePropertyDescription,
    ToolError,
)

# Logger for this module
logger: Logger = logging.getLogger(__name__)


def get_root_class_description_tool(
    graphql_client,
    root_class_type: str,
    metadata_cache,
) -> Union[bool, ToolError]:
    """
    Retrieves all classes of a specific root class type (e.g., "Document", "Folder", "Annotation", "CustomObject).

    Args:
        graphql_client: The GraphQL client to use for queries
        root_class_type: The type of root class to retrieve (e.g., "Document", "Folder", "Annotation", "CustomObject")
        metadata_cache: The metadata cache instance to use

    Returns:
        True if the cache exists or was successfully filled, False otherwise, or a ToolError if an error occurs
    """
    # Ensure the root class exists in the cache
    metadata_cache.ensure_root_class_exists(root_class_type)

    # Check if we have any cached classes for this root class type
    class_cache = metadata_cache.get_class_cache(root_class_type)
    if class_cache:
        # Cache exists, return True
        return True

    # If no cached classes, fetch all classes of this type
    query = """
    query getClassAndSubclasses($object_store_name: String!, $root_class_name: String!, $page_size: Int!) {
        classDescription(
            repositoryIdentifier: $object_store_name
            identifier: $root_class_name
        ) {
            symbolicName
            displayName
            descriptiveText
        }
        subClassDescriptions(
            repositoryIdentifier: $object_store_name
            identifier: $root_class_name
            pageSize: $page_size
        ) {
            classDescriptions {
                symbolicName
                displayName
                descriptiveText
            }
        }
    }
    """

    variables = {
        "object_store_name": graphql_client.object_store,
        "root_class_name": root_class_type,
        "page_size": 500,
    }

    try:
        response = graphql_client.execute(query=query, variables=variables)

        # Check for errors in the response
        if "error" in response and response["error"]:
            return ToolError(
                message=f"Failed to retrieve classes for {root_class_type}: {response.get('message', 'Unknown error')}",
                suggestions=[
                    "Verify the root class type is correct",
                    "Check your connection to the repository",
                ],
            )

        # Process the response
        data = response.get("data", {})
        root_class_info = data.get("classDescription", {})
        subclasses = data.get("subClassDescriptions", {}).get("classDescriptions", [])

        if not root_class_info and not subclasses:
            return ToolError(
                message=f"No classes found for root class type '{root_class_type}'",
                suggestions=[
                    "Check if the root class type is correct",
                    "Verify that classes of this type exist in the repository",
                ],
            )

        # Cache the root class with basic information
        if root_class_info:
            root_class_data = CacheClassDescriptionData(
                display_name=root_class_info.get("displayName", ""),
                symbolic_name=root_class_info.get("symbolicName", ""),
                descriptive_text=root_class_info.get("descriptiveText", ""),
                property_descriptions=[],  # Empty list for now
                name_property_symbolic_name=None,  # To be filled in when property descriptions loaded
            )

            # Cache the root class under its own key (e.g., "Document" -> "Document")
            # This ensures the root class itself is included in the cache
            metadata_cache.set_class_data(
                root_class_type, root_class_type, root_class_data
            )

        # Cache the subclasses with basic information
        for subclass in subclasses:
            symbolic_name = subclass.get("symbolicName", "")

            # Create a ContentClassData object with empty properties list
            class_data = CacheClassDescriptionData(
                display_name=subclass.get("displayName", ""),
                symbolic_name=symbolic_name,
                descriptive_text=subclass.get("descriptiveText", ""),
                property_descriptions=[],  # Empty list for now
                name_property_symbolic_name=None,  # To be filled in when property descriptions loaded
            )

            metadata_cache.set_class_data(root_class_type, symbolic_name, class_data)

        # Successfully filled the cache
        return True

    except Exception as e:
        return ToolError(
            message=f"Failed to retrieve classes for {root_class_type}: {str(e)}",
            suggestions=[
                "Verify the root class type is correct",
                "Check your connection to the repository",
            ],
        )


def discover_and_load_root_class(
    graphql_client, metadata_cache, class_symbolic_name: str, class_gql_data: dict
) -> Union[bool, ToolError]:
    logger.debug(f"Discovering and loading root class for class {class_symbolic_name}")
    query_next_discover_root_class = """
    query getClassMetadata($object_store_name: String!, $class_symbolic_name: String!) {
    classDescription(
        repositoryIdentifier: $object_store_name
        identifier: $class_symbolic_name
    ) {
        superClassDescription {
            symbolicName
            superClassDescription {
                symbolicName
                superClassDescription {
                    symbolicName
                }
            }
        }
    }
    }
    """

    sys_root_class_name: str | None = None

    try:
        cur_class_name: str | None = class_symbolic_name
        while True:
            if cur_class_name in SYSTEM_ROOT_CLASS_TYPES:
                sys_root_class_name = cur_class_name
                break

            super_class: dict = class_gql_data["superClassDescription"]
            super_class_sym_name: str | None = (
                super_class["symbolicName"] if super_class is not None else None
            )
            if super_class_sym_name is None:
                break
            while True:
                logger.debug(f"Looking at super class sym name {sys_root_class_name }")
                if super_class_sym_name in SYSTEM_ROOT_CLASS_TYPES:
                    # Found our root class
                    sys_root_class_name = super_class_sym_name
                    break
                if "superClassDescription" not in super_class:
                    # Reached the end of the superclasses from this gql query. Break out and do another.
                    break
                super_class = super_class["superClassDescription"]
                super_class_sym_name = (
                    super_class["symbolicName"] if super_class is not None else None
                )
                # Reached the end of the superclasses without finding a root class.
                if super_class_sym_name is None:
                    break
            logger.debug(f"System root class name if any so far {sys_root_class_name}")
            logger.debug(
                f"Next super class symbolic name to try if any {super_class_sym_name}"
            )
            # We found our root class
            # Or, we reached the end of superclasses before finding a root class.
            if sys_root_class_name is not None or super_class_sym_name is None:
                break
            # Continue with another gql query to discover the root class from more superclasses
            logger.debug(
                f"Continuing with another query for super class {super_class_sym_name}"
            )
            variables = {
                "object_store_name": graphql_client.object_store,
                "class_symbolic_name": super_class_sym_name,
            }
            response = graphql_client.execute(
                query=query_next_discover_root_class, variables=variables
            )

            # Check for errors in the response
            if "error" in response and response["error"]:
                return ToolError(
                    message=f"Failed to retrieve metadata for class {super_class_sym_name}: {response.get('message', 'Unknown error')}",
                    suggestions=[
                        "Verify the class name is correct",
                        "Check your connection to the repository",
                    ],
                )

            class_gql_data = response.get("data", {}).get("classDescription", {})

            if not class_gql_data:
                return ToolError(
                    message=f"Class '{class_symbolic_name}' not found",
                    suggestions=[
                        "Check the class name",
                        "Use get_root_class_description to see available classes",
                    ],
                )

            cur_class_name = super_class_sym_name

        if sys_root_class_name is None:
            return ToolError(
                message=f"Failed to discover the root class for {initial_class_name}",
                suggestions=[
                    "Check that the class name is correct",
                    "Check that the class name is of a supported root type",
                ],
            )

        logger.debug(
            f"System root class found to be {sys_root_class_name}. Loading root class cache."
        )
        # Load the root class
        load_stat = get_root_class_description_tool(
            graphql_client, sys_root_class_name, metadata_cache
        )
        if isinstance(load_stat, ToolError):
            return load_stat

    except Exception as e:
        return ToolError(
            message=f"Failed to retrieve metadata for class {class_symbolic_name}: {str(e)}",
            suggestions=[
                "Verify the class name is correct",
                "Check your connection to the repository",
            ],
        )

    return True


def get_class_metadata_tool(
    graphql_client,
    class_symbolic_name: str,
    metadata_cache,
) -> Union[CacheClassDescriptionData, ToolError]:
    """
    Retrieves detailed metadata about a repository class including its properties.

    Args:
        graphql_client: The GraphQL client to use for queries
        class_symbolic_name: The symbolic name of the class
        metadata_cache: The metadata cache instance to use

    Returns:
        A ContentClassData object containing class metadata or a ToolError if an error occurs
    """

    query = """
    query getClassMetadata($object_store_name: String!, $class_symbolic_name: String!) {
    classDescription(
        repositoryIdentifier: $object_store_name
        identifier: $class_symbolic_name
    ) {
        namePropertyIndex
        propertyDescriptions {
            symbolicName
            displayName
            descriptiveText
            dataType
            cardinality
            isSearchable
            isSystemOwned
            isHidden
        }
    }
    }
    """

    query_with_discover_root_class = """
    query getClassMetadata($object_store_name: String!, $class_symbolic_name: String!) {
    classDescription(
        repositoryIdentifier: $object_store_name
        identifier: $class_symbolic_name
    ) {
        namePropertyIndex
        propertyDescriptions {
            symbolicName
            displayName
            descriptiveText
            dataType
            cardinality
            isSearchable
            isSystemOwned
            isHidden
        }
        superClassDescription {
            symbolicName
            superClassDescription {
                symbolicName
                superClassDescription {
                    symbolicName
                }
            }
        }
    }
    }
    """
    # First, determine which root class this belongs to
    root_class = metadata_cache.find_root_class_for_class(class_symbolic_name)

    if root_class is None:
        existing_class_data = None
    else:
        existing_class_data = metadata_cache.get_class_data(
            root_class, class_symbolic_name
        )
        if existing_class_data and len(existing_class_data.property_descriptions) > 0:
            return existing_class_data

    initial_query: str = (
        query if existing_class_data else query_with_discover_root_class
    )
    logger.debug(f"initial_query: str = {initial_query}")

    variables = {
        "object_store_name": graphql_client.object_store,
        "class_symbolic_name": class_symbolic_name,
    }

    try:
        response = graphql_client.execute(query=initial_query, variables=variables)

        # Check for errors in the response
        if "error" in response and response["error"]:
            return ToolError(
                message=f"Failed to retrieve metadata for class {class_symbolic_name}: {response.get('message', 'Unknown error')}",
                suggestions=[
                    "Verify the class name is correct",
                    "Check your connection to the repository",
                ],
            )

        # Process the response to make it more useful
        class_gql_data = response.get("data", {}).get("classDescription", {})

        if not class_gql_data:
            return ToolError(
                message=f"Class '{class_symbolic_name}' not found",
                suggestions=[
                    "Check the class name",
                    "Use get_root_class_description to see available classes",
                ],
            )

        if not existing_class_data:
            discover_stat = discover_and_load_root_class(
                graphql_client, metadata_cache, class_symbolic_name, class_gql_data
            )
            if isinstance(discover_stat, ToolError):
                return discover_stat
            root_class = metadata_cache.find_root_class_for_class(class_symbolic_name)
            logger.debug(
                f"Root class for {class_symbolic_name} found to be {root_class}"
            )
            # Root class should be loaded now else there would have been an error.
            assert (
                root_class is not None
            ), f"Root class not found for class '{class_symbolic_name}'"
            existing_class_data = metadata_cache.get_class_data(
                root_class, class_symbolic_name
            )
            assert (
                existing_class_data
            ), f"Class data not found for class '{class_symbolic_name}'"
            # Property descriptions shouldn't be loaded yet but go ahead and check anyway.
            if len(existing_class_data.property_descriptions) > 0:
                return existing_class_data

        # Convert the GraphQL response to our model objects
        property_descriptions = []
        name_prop_idx: int | None = class_gql_data.get("namePropertyIndex", None)
        name_prop_sym_name: str | None = None
        for idx, prop in enumerate(class_gql_data.get("propertyDescriptions", [])):
            prop_sym_name: str = prop.get("symbolicName")
            if name_prop_idx and idx == name_prop_idx:
                name_prop_sym_name = prop_sym_name
            property_descriptions.append(
                CachePropertyDescription(
                    symbolic_name=prop_sym_name,
                    display_name=prop.get("displayName"),
                    descriptive_text=prop.get("descriptiveText", ""),
                    data_type=prop.get("dataType"),
                    cardinality=prop.get("cardinality"),
                    is_searchable=prop.get("isSearchable", False),
                    is_system_owned=prop.get("isSystemOwned", False),
                    is_hidden=prop.get("isHidden", False),
                    valid_search_operators=[],  # This would need to be populated based on data type
                )
            )

        # We already have class data, just update the properties
        existing_class_data.property_descriptions = property_descriptions
        existing_class_data.name_property_symbolic_name = name_prop_sym_name
        content_class_data = existing_class_data

        # Return the ContentClassData object directly
        return content_class_data

    except Exception as e:
        return ToolError(
            message=f"Failed to retrieve metadata for class {class_symbolic_name}: {str(e)}",
            suggestions=[
                "Verify the class name is correct",
                "Check your connection to the repository",
            ],
        )
