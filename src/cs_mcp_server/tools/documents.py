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

import logging
import traceback
import re
from typing import Any, List, Optional, Union, Dict

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from cs_mcp_server.cache.metadata import MetadataCache
from cs_mcp_server.cache.metadata_loader import get_class_metadata_tool
from cs_mcp_server.client.graphql_client import (
    GraphQLClient,
    graphql_client_execute_async_wrapper,
)
from cs_mcp_server.tools.search import get_repository_object_main
from cs_mcp_server.utils import (
    Cardinality,
    Document,
    DocumentPropertiesInput,
    SubCheckinActionInput,
    SubCheckoutActionInput,
    ToolError,
    TypeID,
)
from cs_mcp_server.utils.constants import (
    DEFAULT_DOCUMENT_CLASS,
    VERSION_SERIES_CLASS,
    TEXT_EXTRACT_ANNOTATION_CLASS,
    TEXT_EXTRACT_SEPARATOR,
    EXCLUDED_PROPERTY_NAMES,
    TRACEBACK_LIMIT,
    VERSION_STATUS_RELEASED,
)

from cs_mcp_server.utils.common import SearchParameters, ToolError
from cs_mcp_server.tools import register_search_tools
from cs_mcp_server.utils.utils import (
    get_document_text_extract_content,
    process_search_parameters,
)

# Logger for this module
logger = logging.getLogger(__name__)


def register_document_tools(
    mcp: FastMCP, graphql_client: GraphQLClient, metadata_cache: MetadataCache
) -> None:
    @mcp.tool(
        name="get_document_versions",
    )
    async def get_document_versions(identifier: str) -> dict:
        """
        Retrieves all versions in the version series that includes the specified document.
        This returns all versions (past, current, and future) that belong to the same version series.

        :param identifier: The document id or path (required). This can be either the document's ID (GUID)
                          or its path in the repository (e.g., "/Folder1/document.pdf").

        :returns: A dictionary containing the version series details, including:
            - versionSeries (dict): A dictionary containing version series details, including:
                - versions (list): A list of all versions in the series, with each version containing:
                    - versionables (list): A list of versionable objects, each containing:
                        - majorVersionNumber (int): The major version number. The format to print out version number is majorVersionNumber.minorVersionNumber.
                        - minorVersionNumber (int): The minor version number. The format to print out version number is majorVersionNumber.minorVersionNumber.
                        - id (str): The unique identifier of the version's document id.
        """
        query = """
        query getDocumentVersions($object_store_name: String!, $identifier: String!){
            document(
                repositoryIdentifier: $object_store_name
                identifier: $identifier
            ) {
                versionSeries {
                    versions {
                        versionables {
                            id
                            majorVersionNumber
                            minorVersionNumber
                        }
                    }
                }
            }
        }
        """

        variables = {
            "identifier": identifier,
            "object_store_name": graphql_client.object_store,
        }

        return await graphql_client.execute_async(query=query, variables=variables)

    @mcp.tool(
        name="get_document_text_extract",
    )
    async def get_document_text_extract(identifier: str) -> str:
        """
        Retrieves a document's text extract content.

        :param identifier: The document id or path (required). This can be either the document's ID (GUID)
                          or its path in the repository (e.g., "/Folder1/document.pdf").

        :returns: The text content of the document's text extract annotation.
                 If multiple text extracts are found, they will be concatenated.
                 Returns an empty string if no text extract is found.
        """
        return await get_document_text_extract_content(
            graphql_client=graphql_client, identifier=identifier
        )

    @mcp.tool(
        name="create_document",
    )
    async def create_document(
        class_identifier: Optional[str] = None,
        id: Optional[str] = None,
        document_properties: Optional[DocumentPropertiesInput] = None,
        file_in_folder_identifier: Optional[str] = None,
        checkin_action: Optional[SubCheckinActionInput] = SubCheckinActionInput(),
        file_paths: Optional[List[str]] = None,
    ) -> Union[Document, ToolError]:
        """
        **PREREQUISITES IN ORDER**: To use this tool, you MUST call two other tools first in a specific sequence.
        1. determine_class tool to get the class_identifier.
        2. get_class_property_descriptions to get a list of valid properties for the given class_identifier

        Description:
        Creates a document in the content repository with specified properties.

        :param class_identifier: The class identifier for the document. If not provided, defaults to "Document".
        :param id: The unique GUID for the document. If not provided, a new GUID with curly braces will be generated.
        :param document_properties: Properties for the document including name, content, mimeType, etc.
        :param file_in_folder_identifier: The identifier or path of the folder to file the document in. This always starts with "/".
        :param checkin_action: Check-in action parameters. CheckinMinorVersion should always be included.
        :param file_paths: Optional list of file paths to upload as the document's content.

        :returns: If successful, returns a Document object with its properties.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "create_document"
        try:
            # Prepare the mutation
            mutation = """
            mutation ($object_store_name: String!, $class_identifier: String, $id: ID,
                     $document_properties: DocumentPropertiesInput, $file_in_folder_identifier: String,
                     $checkin_action: SubCheckinActionInput) {
              createDocument(
                repositoryIdentifier: $object_store_name
                classIdentifier: $class_identifier
                id: $id
                documentProperties: $document_properties
                fileInFolderIdentifier: $file_in_folder_identifier
                checkinAction: $checkin_action
              ) {
                id
                className
                properties {
                  id
                  value
                }
              }
            }
            """

            # Prepare variables for the GraphQL query with all parameters set to None by default
            variables = {
                "object_store_name": graphql_client.object_store,
                "class_identifier": None,
                "id": None,
                "document_properties": None,
                "file_in_folder_identifier": None,
                "checkin_action": None,
            }

            # Add optional parameters if provided
            if class_identifier:
                variables["class_identifier"] = class_identifier
            if id:
                variables["id"] = id
            if file_in_folder_identifier:
                variables["file_in_folder_identifier"] = file_in_folder_identifier

            # Process file paths
            file_paths_dict = {}

            # Handle file upload if file paths are provided
            if file_paths:
                try:
                    # Initialize document_properties if not provided
                    if not document_properties:
                        document_properties = DocumentPropertiesInput()

                    file_paths_dict = document_properties.process_file_content(
                        file_paths
                    )
                except Exception as e:
                    logger.error("%s failed: %s", method_name, str(e))
                    logger.error(traceback.format_exc())
                    return ToolError(
                        message=f"{method_name} failed: {str(e)}. Trace available in server logs."
                    )

            # Process document properties if provided
            if document_properties:
                try:
                    document_properties.eval()
                    transformed_props = document_properties.transform_properties_dict(
                        exclude_none=True
                    )
                    variables["document_properties"] = transformed_props
                except Exception as e:
                    logger.error("Error transforming document properties: %s", str(e))
                    logger.error(traceback.format_exc())
                    return ToolError(
                        message=f"{method_name} failed: {str(e)}. Trace available in server logs."
                    )

            # Handle checkin action if provided
            if checkin_action:
                # Use model_dump with exclude_none for cleaner code
                variables["checkin_action"] = checkin_action.model_dump(
                    exclude_none=True
                )

            # Execute the GraphQL mutation
            if file_paths_dict:
                # Use execute with file_paths for file upload
                logger.info("Executing document creation with file upload")
                response = graphql_client.execute(
                    query=mutation, variables=variables, file_paths=file_paths_dict
                )
            else:
                # Use execute_async for regular document creation
                logger.info("Executing document creation")
                response = await graphql_client.execute_async(
                    query=mutation, variables=variables
                )

            # Handle errors
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")

            # Create and return a Document instance from the response
            return Document.create_an_instance(
                graphQL_changed_object_dict=response["data"]["createDocument"],
                class_identifier=(
                    class_identifier if class_identifier else DEFAULT_DOCUMENT_CLASS
                ),
            )

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="update_document_properties",
    )
    async def update_document_properties(
        identifier: str,
        document_properties: Optional[DocumentPropertiesInput] = None,
    ) -> Union[Document, ToolError]:
        """
        **PREREQUISITES**: Before using this tool, you MUST call ONE of these tools first:
        1. property_extraction - For content based property extraction workflows (provides class specific property names and document text content for AI-based extraction)
        2. get_class_property_descriptions - For general property updates (provides full property metadata including data types, cardinality, etc.)

        Description:
        Updates an existing document's properties in the content repository.
        This tool ONLY updates properties and does NOT change the document's class.
        To change a document's class, use the update_document_class tool instead.

        :param identifier: The document id or path (required). This can be either the document's ID (GUID) or its path in the repository (e.g., "/Folder1/document.pdf").
        :param document_properties: Properties to update for the document including name, mimeType, etc.

        :returns: If successful, returns a Document object with its updated properties.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "update_document_properties"
        try:
            # Prepare the mutation
            mutation = """
            mutation ($object_store_name: String!, $identifier: String!, $class_identifier: String,
                     $document_properties: DocumentPropertiesInput) {
              updateDocument(
                repositoryIdentifier: $object_store_name
                identifier: $identifier
                classIdentifier: $class_identifier
                documentProperties: $document_properties
              ) {
                id
                className
                properties {
                  id
                  value
                }
              }
            }
            """

            # Prepare variables for the GraphQL query
            variables = {
                "object_store_name": graphql_client.object_store,  # Always use the default object store
                "identifier": identifier,
                "class_identifier": None,  # Always None - use update_document_class to change class
                "document_properties": None,
            }

            # Process document properties if provided
            if document_properties:
                try:
                    document_properties.eval()
                    transformed_props = document_properties.transform_properties_dict(
                        exclude_none=True
                    )
                    variables["document_properties"] = transformed_props
                except Exception as e:
                    logger.error("Error transforming document properties: %s", str(e))
                    logger.error(traceback.format_exc())
                    return ToolError(
                        message=f"{method_name} failed: {str(e)}. Trace available in server logs."
                    )

            # Execute the GraphQL mutation
            logger.info("Executing document update")
            response = await graphql_client.execute_async(
                query=mutation, variables=variables
            )

            # Handle errors
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")

            # Create and return a Document instance from the response
            return Document.create_an_instance(
                graphQL_changed_object_dict=response["data"]["updateDocument"],
                class_identifier=DEFAULT_DOCUMENT_CLASS,
            )

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="update_document_class",
    )
    async def update_document_class(
        identifier: str,
        class_identifier: str,
    ) -> Union[Document, ToolError]:
        """
        **PREREQUISITES**: Before using this tool, you MUST call ONE of these tools first:
        1. list_all_classes - Call this tool only IF IT EXISTS and the user is using a (re)classification workflow where we need highest accuracy.
        2. determine_class - For general class update.

        Description:
        Changes a document's class in the content repository.
        WARNING: Changing a document's class can result in loss of properties if the new class
        does not have the same properties as the old class. Properties that don't exist in the
        new class will be removed from the document.

        This tool ONLY changes the document's class and does NOT update any properties.
        To update properties after changing the class, use the update_document_properties tool.

        :param identifier: The document id or path (required). This can be either the document's ID (GUID) or its path in the repository (e.g., "/Folder1/document.pdf").
        :param class_identifier: The new class identifier for the document (required).

        :returns: If successful, returns a Document object with the new class.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "update_document_class"
        try:
            # Prepare the mutation
            mutation = """
            mutation ($object_store_name: String!, $identifier: String!, $class_identifier: String!) {
              updateDocument(
                repositoryIdentifier: $object_store_name
                identifier: $identifier
                classIdentifier: $class_identifier
              ) {
                id
                className
                properties {
                  id
                  value
                }
              }
            }
            """

            # Prepare variables for the GraphQL query
            variables = {
                "object_store_name": graphql_client.object_store,
                "identifier": identifier,
                "class_identifier": class_identifier,
            }

            # Execute the GraphQL mutation
            logger.info("Executing document class update")
            response: Union[ToolError, Dict[str, Any]] = (
                await graphql_client_execute_async_wrapper(
                    logger,
                    method_name,
                    graphql_client,
                    query=mutation,
                    variables=variables,
                )
            )
            if isinstance(response, ToolError):
                return response

            # Create and return a Document instance from the response
            return Document.create_an_instance(
                graphQL_changed_object_dict=response["data"]["updateDocument"],
                class_identifier=class_identifier,
            )

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="checkin_document",
    )
    async def checkin_document(
        identifier: str,
        checkin_action: Optional[SubCheckinActionInput] = SubCheckinActionInput(),
        document_properties: Optional[DocumentPropertiesInput] = None,
        file_paths: Optional[List[str]] = None,
    ) -> Union[Document, ToolError]:
        """
        Checks in a document in the content repository with specified properties.

        :param identifier: The identifier (required). This can be either a reservation_id or document_id.
                          Reservation ID (GUID) is prioritized.
                          Otherwise, we use document_id (GUID).
        :param checkin_action: Check-in action parameters for the document.
        :param document_properties: Properties to update for the document during check-in.
        :param file_paths: Optional list of file paths to upload as the document's content.

        :returns: If successful, returns a Document object with its updated properties.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "checkin_document"
        try:
            # Prepare the mutation
            mutation = """
            mutation ($object_store_name: String!, $identifier: String!,
                     $document_properties: DocumentPropertiesInput, $checkin_action: SubCheckinActionInput!) {
              checkinDocument(
                repositoryIdentifier: $object_store_name
                identifier: $identifier
                documentProperties: $document_properties
                checkinAction: $checkin_action
              ) {
                id
                className
                reservation{
                    isReserved
                    id
                }
                currentVersion{
                    contentElements{
                        ... on ContentTransferType {
                            retrievalName
                            contentType
                            contentSize
                            downloadUrl
                        }
                    }
                }
                properties {
                  id
                  value
                }
              }
            }
            """

            # Prepare variables for the GraphQL query
            variables = {
                "object_store_name": graphql_client.object_store,
                "identifier": identifier,
                "document_properties": None,
                "checkin_action": None,
            }

            # Process file paths
            file_paths_dict = {}

            # Handle file upload if file paths are provided
            if file_paths:
                try:
                    # Initialize document_properties if not provided
                    if not document_properties:
                        document_properties = DocumentPropertiesInput()

                    file_paths_dict = document_properties.process_file_content(
                        file_paths
                    )
                except Exception as e:
                    logger.error("%s failed: %s", method_name, str(e))
                    logger.error(traceback.format_exc())
                    return ToolError(
                        message=f"{method_name} failed: {str(e)}. Trace available in server logs."
                    )

            # Process document properties if provided
            if document_properties:
                try:
                    document_properties.eval()
                    transformed_props = document_properties.transform_properties_dict(
                        exclude_none=True
                    )
                    variables["document_properties"] = transformed_props
                except Exception as e:
                    logger.error("Error transforming document properties: %s", str(e))
                    logger.error(traceback.format_exc())
                    return ToolError(
                        message=f"{method_name} failed: {str(e)}. Trace available in server logs."
                    )

            if checkin_action:
                # Handle checkin action if provided                # Use model_dump with exclude_none for cleaner code
                variables["checkin_action"] = checkin_action.model_dump(
                    exclude_none=True
                )

            # Execute the GraphQL mutation
            if file_paths_dict:
                # Use execute with file_paths for file upload
                logger.info("Executing document check-in with file upload")
                response = graphql_client.execute(
                    query=mutation,
                    variables=variables,
                    file_paths=file_paths_dict,
                )
            else:
                # Use execute_async for regular document check-in
                logger.info("Executing document check-in")
                response = await graphql_client.execute_async(
                    query=mutation, variables=variables
                )

            # Handle errors
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")

            # Create and return a Document instance from the response
            return Document.create_an_instance(
                graphQL_changed_object_dict=response["data"]["checkinDocument"],
                class_identifier=DEFAULT_DOCUMENT_CLASS,
            )

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="checkout_document",
    )
    async def checkout_document(
        identifier: str,
        document_properties: Optional[DocumentPropertiesInput] = None,
        checkout_action: Optional[SubCheckoutActionInput] = None,
        download_folder_path: Optional[str] = None,
    ) -> Union[Document, ToolError]:
        """
        Checks out a document in the content repository.

        :param identifier: The document id or path (required). This can be either the document's ID (GUID) or its path in the repository (e.g., "/Folder1/document.pdf").
        :param document_properties: Properties to update for the document during check-out.
        :param checkout_action: Check-out action parameters for the document.
        :param download_folder_path: Optional path to a folder where the document content will be downloaded.
                                    If not provided but content download is needed, the user will be prompted to provide it.

        :returns: If successful, returns a Document object with its updated properties.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "checkout_document"
        try:
            # Prepare the mutation
            mutation = """
            mutation ($object_store_name: String!, $identifier: String!,
                     $document_properties: DocumentPropertiesInput, $checkout_action: SubCheckoutActionInput) {
              checkoutDocument(
                repositoryIdentifier: $object_store_name
                identifier: $identifier
                documentProperties: $document_properties
                checkoutAction: $checkout_action
              ) {
                id
                className
                reservation{
                    isReserved
                    id
                }
                currentVersion{
                    contentElements{
                        ... on ContentTransferType {
                            retrievalName
                            contentType
                            contentSize
                            downloadUrl
                        }
                    }
                }
                properties {
                  id
                  value
                }
              }
            }
            """

            # Prepare variables for the GraphQL query
            variables = {
                "object_store_name": graphql_client.object_store,
                "identifier": identifier,
                "document_properties": None,
                "checkout_action": None,
            }

            # Process document properties if provided
            if document_properties:
                try:
                    document_properties.eval()
                    transformed_props = document_properties.transform_properties_dict(
                        exclude_none=True
                    )
                    variables["document_properties"] = transformed_props
                except Exception as e:
                    logger.error("Error transforming document properties: %s", str(e))
                    logger.error(traceback.format_exc())
                    return ToolError(
                        message=f"{method_name} failed: {str(e)}. Trace available in server logs."
                    )

            # Handle checkout action if provided
            if checkout_action:
                # Use model_dump with exclude_none for cleaner code
                variables["checkout_action"] = checkout_action.model_dump(
                    exclude_none=True
                )

            # Execute the GraphQL mutation
            logger.info("Executing document check-out")
            response: Union[ToolError, Dict[str, Any]] = (
                await graphql_client_execute_async_wrapper(
                    logger,
                    method_name,
                    graphql_client,
                    query=mutation,
                    variables=variables,
                )
            )
            if isinstance(response, ToolError):
                return response

            # Create a Document instance from the response
            document = Document.create_an_instance(
                graphQL_changed_object_dict=response["data"]["checkoutDocument"],
                class_identifier=DEFAULT_DOCUMENT_CLASS,
            )

            # Check if we need to download content
            if (
                download_folder_path
                and "currentVersion" in response["data"]["checkoutDocument"]
            ):
                content_elements = response["data"]["checkoutDocument"][
                    "currentVersion"
                ]["contentElements"]

                if content_elements and len(content_elements) > 0:
                    logger.info(
                        "Found %s content elements to download", len(content_elements)
                    )

                    download_results = []
                    download_errors = []

                    for idx, element in enumerate(content_elements):
                        if "downloadUrl" in element and element["downloadUrl"]:
                            download_url = element["downloadUrl"]
                            logger.info(
                                "Downloading content element %s/%s: %s",
                                idx + 1,
                                len(content_elements),
                                element["retrievalName"],
                            )

                            download_result = (
                                await graphql_client.download_content_async(
                                    download_url=download_url,
                                    download_folder_path=download_folder_path,
                                )
                            )

                            if download_result["success"]:
                                download_results.append(download_result)
                                logger.info(
                                    "Content element %s downloaded to %s",
                                    idx + 1,
                                    download_result["file_path"],
                                )
                            else:
                                error_msg = (
                                    "Failed to download content element %s: %s"
                                    % (
                                        idx + 1,
                                        download_result["error"],
                                    )
                                )
                                download_errors.append(error_msg)
                                logger.warning(error_msg)

                    if download_errors:
                        error_message = (
                            "Document checkout was successful, but %s content downloads failed: %s"
                            % (len(download_errors), "; ".join(download_errors))
                        )
                        logger.warning(error_message)
                        return ToolError(
                            message=error_message,
                            suggestions=[
                                "Check if the download folder exists and is writable",
                                "Verify network connectivity to the content server",
                                "Try downloading the files without checking out the document",
                            ],
                        )
                    elif download_results:
                        logger.info(
                            "Successfully downloaded %s content elements",
                            len(download_results),
                        )
            return document

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="delete_version_series", annotations=ToolAnnotations(destructiveHint=True)
    )
    async def delete_version_series(
        version_series_id: str,
    ) -> Union[str, ToolError]:
        """
        Deletes an entire version series (all versions of a document) in the content repository.

        :param version_series_id: The version series ID (GUID) to delete. If you don't have the version series ID,
                                 first call get_document_property on the document to get the version series ID.

        :returns: If successful, returns the deleted version series ID as a string.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "delete_version_series"
        try:
            # Prepare the mutation to delete the version series
            mutation = """
            mutation ($object_store_name: String!, $identifier: String!) {
              deleteVersionSeries(
                repositoryIdentifier: $object_store_name
                identifier: $identifier
              ) {
                id
                className
              }
            }
            """

            # Prepare variables for the GraphQL mutation
            variables = {
                "object_store_name": graphql_client.object_store,
                "identifier": version_series_id,
            }

            # Execute the GraphQL mutation
            logger.info("Executing version series deletion")
            response: Union[ToolError, Dict[str, Any]] = (
                await graphql_client_execute_async_wrapper(
                    logger,
                    method_name,
                    graphql_client,
                    query=mutation,
                    variables=variables,
                )
            )
            if isinstance(response, ToolError):
                return response

            # Return just the id as a string
            return response["data"]["deleteVersionSeries"]["id"]

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="delete_document_version",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    async def delete_document_version(
        identifier: str,
    ) -> Union[str, ToolError]:
        """
        Deletes a specific document version in the content repository.

        :param identifier: The document id or path (required). This can be either the document's ID (GUID)
                          or its path in the repository (e.g., "/Folder1/document.pdf").

        :returns: If successful, returns the deleted Document id.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "delete_document_version"
        try:
            # Delete only the specified version
            mutation = """
            mutation ($object_store_name: String!, $identifier: String!) {
              deleteDocument(
                repositoryIdentifier: $object_store_name
                identifier: $identifier
              ) {
                id
                className
              }
            }
            """

            # Prepare variables for the GraphQL query
            variables = {
                "object_store_name": graphql_client.object_store,
                "identifier": identifier,
            }

            # Execute the GraphQL mutation
            logger.info("Executing single document version deletion")
            response: Union[ToolError, Dict[str, Any]] = (
                await graphql_client_execute_async_wrapper(
                    logger,
                    method_name,
                    graphql_client,
                    query=mutation,
                    variables=variables,
                )
            )
            if isinstance(response, ToolError):
                return response

            # Create and return a Document instance from the response
            return response["data"]["deleteDocument"]["id"]

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="get_document_properties",
    )
    async def get_document_properties(
        identifier: str,
    ) -> Union[Document, ToolError]:
        """
        Retrieves a document's properties from the content repository by ID or path.

        Note: Use this tool ONLY when you need to retrieve a document using its ID or file path.
        For searching documents by other properties, use the repository_search tool instead.

        :param identifier: The document id or path (required). This can be either the document's ID (GUID) or its path in the repository (e.g., "/Folder1/document.pdf").

        :returns: If successful, returns the Document object with its properties.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "get_document"
        try:
            # Prepare the query
            query = """
            query ($object_store_name: String!, $identifier: String!) {
                document(repositoryIdentifier: $object_store_name, identifier: $identifier) {
                    id
                    name
                    properties {
                        id
                        value
                    }
                }
            }
            """

            # Prepare variables for the GraphQL query
            variables = {
                "object_store_name": graphql_client.object_store,
                "identifier": identifier,
            }

            # Execute the GraphQL query
            logger.info("Executing document retrieval")
            response: Union[ToolError, Dict[str, Any]] = (
                await graphql_client_execute_async_wrapper(
                    logger,
                    method_name,
                    graphql_client,
                    query=query,
                    variables=variables,
                )
            )
            if isinstance(response, ToolError):
                return response

            # Check if document was found
            if not response.get("data") or not response["data"].get("document"):
                return ToolError(
                    message=f"Document not found with identifier: {identifier}",
                    suggestions=[
                        "Check if the document ID or path is correct",
                        "Verify that the document exists in the repository",
                        "Try using repository_search tool to find the document by other properties",
                    ],
                )

            # Create and return a Document instance from the response
            return Document.create_an_instance(
                graphQL_changed_object_dict=response["data"]["document"],
                class_identifier=response["data"]["document"].get(
                    "className", DEFAULT_DOCUMENT_CLASS
                ),
            )

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="cancel_document_checkout",
    )
    async def cancel_document_checkout(
        identifier: str,
    ) -> Union[Document, ToolError]:
        """
        Cancels a document checkout in the content repository.

        :param identifier: The identifier (required). This can be either a reservation_id or document_id.
                          Reservation ID (GUID) is prioritized.
                          Otherwise, we use document_id (GUID).

        :returns: If successful, returns a Document object with its updated properties.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "cancel_document_checkout"
        try:
            # Prepare the mutation
            mutation = """
            mutation ($object_store_name: String!, $identifier: String!) {
              cancelDocumentCheckout(
                repositoryIdentifier: $object_store_name
                identifier: $identifier
              ) {
                id
                className
                reservation{
                    isReserved
                    id
                }
                currentVersion{
                    contentElements{
                        ... on ContentTransferType {
                            retrievalName
                            contentType
                            contentSize
                            downloadUrl
                        }
                    }
                }
                properties {
                  id
                  value
                }
              }
            }
            """

            # Prepare variables for the GraphQL query
            variables = {
                "object_store_name": graphql_client.object_store,
                "identifier": identifier,
            }

            # Execute the GraphQL mutation
            logger.info("Executing document checkout cancellation")
            response: Union[ToolError, Dict[str, Any]] = (
                await graphql_client_execute_async_wrapper(
                    logger,
                    method_name,
                    graphql_client,
                    query=mutation,
                    variables=variables,
                )
            )
            if isinstance(response, ToolError):
                return response

            # Create and return a Document instance from the response
            return Document.create_an_instance(
                graphQL_changed_object_dict=response["data"]["cancelDocumentCheckout"],
                class_identifier=DEFAULT_DOCUMENT_CLASS,
            )

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="document_search",
    )
    async def document_search(
        search_parameters: SearchParameters,
        search_term: str = "",
        max_results: int = 10,
    ) -> list | None | ToolError:
        """
        **PREREQUISITES IN ORDER**: To use this tool, you MUST call two other tools first in a specific sequence.
        1. determine_class tool to get the class_name for search_class. The search class must be a document class or
           a document subclass.
        2. get_searchable_property_descriptions to get a list of valid property_name for search_properties

        Description:
        This tool will execute a request to search for documents based on content and the metadata criteria.

        :param search_term: The words for CBR search. This will be used to search for documents based on their CBR indexed content and metadata
            If empty string or None, then only search by metadata.

        :param search_parameters (SearchParameters): provide parameters search_class and addiontal search conditions.
          Note the search_class is filled in by determine_class tool.
          search_properties inside search_parameters include any property being searched for and any search conditions.
          Note: additional properties beside the search_class are used to narrow down the result set, not to expand the result set,
          ie it does not make sense to support prompt such as:
             get me all  XXXCBRDocClass documents that are  created by XXXuser OR contains 'XXX Content' .
          For CBR, Content search will be carried out first to get a result set and additional properties are placed on
          this result set to narrow it down.

        :returns: the released versions of documents that fit the search criteria.
                - if search by content and CBR is not enabled, tool will return a ToolError.


        Example of search by content and class is CBR enabled:
        Prompt: get me all  XXXCBRDocClass documents that are  created by XXXuser and contains 'XXX Content'
        Request: {
            "doc_class": "XXXCBRDocClass",
            "max_results": 50,
            "search_parameters": {
                "search_class": "XXXCBRDocClass",
                "search_properties": [
                {
                    "operator": "=",
                    "property_name": "Creator",
                    "property_value": "XXXuser"
                }
                ]
            },
            "search_term": "XXX Content"
        }
        """

        method_name = "document_search"

        search_properties_string = None
        return_properties = None

        try:
            # if no CONTENT is passed in, search by metadata only, then use the generic repository metadata search,
            # restrict to return on release versions of documents
            if search_term is None or not search_term.strip():
                # restrict to return only RELEASED version of document
                docs = await get_repository_object_main(
                    search_parameters=search_parameters,
                    graphql_client=graphql_client,
                    metadata_cache=metadata_cache,
                    additional_filter_string=f"VersionStatus={VERSION_STATUS_RELEASED}",
                )
                if isinstance(docs, ToolError):
                    return docs

                docslist = docs["data"]["repositoryObjects"]["independentObjects"]
                docs_Pedantic_list = graphql_to_doclist(docslist, "")
                return docs_Pedantic_list

            result = await process_search_parameters(
                graphql_client, metadata_cache, search_parameters=search_parameters
            )
            logger.debug(f"result: {result}")

            # Check if we got an error
            if isinstance(result, ToolError):
                return result

            # Unpack the result tuple
            search_properties_string, return_properties = result
            return_properties_with_d_prefix = [
                f"d.{prop}" for prop in return_properties
            ]
            logger.info("search property string:" + (search_properties_string or ""))
            logger.info(
                "return_properties string:" + str(return_properties_with_d_prefix)
            )

            is_CBR_enabled = await _check_if_doc_class_is_CBR_enabled(
                graphql_client=graphql_client,
                metadata_cache=metadata_cache,
                doc_class=search_parameters.search_class,
            )
            logger.info(
                f"is CBR enabled: {is_CBR_enabled} for class {search_parameters.search_class}"
            )

            if is_CBR_enabled:
                docs = await cbr_search(
                    search_term=search_term,
                    search_properties_string=search_properties_string,  # example: "creator like 'p8admin' or .. and .. "
                    doc_class=search_parameters.search_class,
                    rows_limit=max_results,
                    return_properties_with_brackets=return_properties_with_d_prefix,
                )
                if isinstance(docs, ToolError):
                    return docs

                docslist = docs["data"]["repositoryRows"]["repositoryRows"]
                docs_Pedantic_list = graphql_to_doclist(docslist, "Rank")
                return docs_Pedantic_list

            else:
                return ToolError(
                    message=f"{method_name} failed: Class {search_parameters.search_class} must be CBR-enabled to search for terms <{search_term}>."
                )
        except Exception as ex:
            error_traceback = traceback.format_exc(limit=TRACEBACK_LIMIT)
            logger.error(
                f"{method_name} failed: {ex.__class__.__name__} - {str(ex)}\n{error_traceback}"
            )

            return ToolError(
                message=f"{method_name} failed: got err {ex}. Trace available in server logs.",
            )

    def graphql_to_doclist(
        docslist: dict[Any, Any],
        score_key: str = "",
    ) -> list | ToolError:
        if len(docslist) == 0:
            return []
        else:
            contained_docs = []
            for doc in docslist:
                properties = doc["properties"]
                id_value = None
                score = None
                for prop in properties:
                    if prop["id"] == "Id":
                        id_value = prop["value"]
                        logger.info("doc id is:" + id_value)
                    if score_key and score_key.strip() and prop["id"] == score_key:
                        score = prop["value"]

                doc_with_id = {"id": id_value}
                doc_with_id |= doc
                onedoc = Document.create_an_instance(
                    graphQL_changed_object_dict=doc_with_id,
                )
                onedoc_withscore = {
                    score_key: score,
                    "document": onedoc,
                }
                if score != "":
                    contained_docs.append(onedoc_withscore)
                else:
                    contained_docs.append(onedoc)
            return contained_docs

    async def cbr_search(
        return_properties_with_brackets: list[str],
        search_term: str,
        search_properties_string: str,
        doc_class: str = "Document",
        rows_limit: int = 10,
    ) -> dict | ToolError:
        """
        This tool will perform a CBR (Content-Based Retrieval) search. It's a search method that finds documents
        based on finding the search term in their content or properties. The document and properties must be
        CBR enabled for this to work. The search term can be made up of multiple words.

        :param search_term (str): The search term to use for the search. This can be made up of multiple words.

        :returns: A the repository object details, including:
            - repositoryObjects (dict): a dictionary containing independentObjects:
                - independentObjects (list): A list of independent objects, each containing:
                - properties (list): A list of properties, each containing:
                    - label (str): The name of the property.
                    - value (str): The value of the property.

        Example:
        Prompt:"find me all the docs in the repository using CBR search with these terms 'cont*nt fIL?NET ENGI*'.
        The class of documents should be confined to VanCBRDocClass."
        MCP Client would call this tool with params
        search_term: "cont*nt fIL?NET ENGI*"
        doc_class: "VanCBRDocClass"
        max_results: 10
        """
        method_name = "cbr_search"

        # timeout issue: CBR query can take a long time to execute, so we need to set a timeout and if so how
        # limit by number of rows returned
        CBR_GQL_QUERY = """
            query ($repo: String!, $sql: String!) {
                repositoryRows(repositoryIdentifier: $repo, sql: $sql) 
                {
                    repositoryRows {
                        properties {
                            id
                            type
                            value 
                            ... on ObjectProperty {
                                objectValue {
                                className
                                    ... on CmAbstractPersistable {
                                        creator
                                        dateLastModified
                                        properties {
                                            id
                                            label
                                            type
                                            cardinality
                                            value
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
"""

        try:
            if search_term:
                logger.debug(f"{method_name}, Enter ")

                search_term = search_term.lower()
                logger.debug(
                    f"{method_name}, search_term After to lo-case {search_term} "
                )

                search_term_or_error = _escape_special_characters(search_term)
                if isinstance(search_term_or_error, ToolError):
                    return search_term_or_error
                search_term = search_term_or_error
                logger.debug(
                    f"{method_name}, search_term After escape special char {search_term}"
                )

            CBR_SQL = """SELECT {retrieval_columns} FROM {Document} d INNER JOIN ContentSearch c ON d.This = c.QueriedObject 
                WHERE CONTAINS(d.*, '{terms_list}')
                AND {metadata_filters}
                ORDER BY c.Rank DESC
                OPTIONS (FULLTEXTROWLIMIT {rows_limit})
                """

            retrieval_columns = "d.This, c.Rank, "  # .join(return_properties)
            ### extract the return properties into a list of strings like this: [d.prop1, d.prop2, d.prop3]
            ### then build a string with join, using comma to separate.
            extra_columns = retrieval_columns + ", ".join(
                return_properties_with_brackets
            )
            logger.debug(f"{method_name}, extra_columns: {extra_columns}")
            retrieval_columns = extra_columns
            ####
            metadata_filters = f"d.VersionStatus={VERSION_STATUS_RELEASED}"
            if search_properties_string:
                metadata_filters = metadata_filters + f" and {search_properties_string}"
            sql = CBR_SQL.format(
                Document=doc_class,
                terms_list=search_term,
                metadata_filters=metadata_filters,
                retrieval_columns=retrieval_columns,
                rows_limit=rows_limit,
            )
            logger.debug(f"{method_name}, CBR_SQL After substitution {CBR_SQL}")
            var = {
                "repo": graphql_client.object_store,
                "sql": sql,
            }

            response: Union[ToolError, Dict[str, Any]] = (
                await graphql_client_execute_async_wrapper(
                    logger,
                    method_name,
                    graphql_client,
                    query=CBR_GQL_QUERY,
                    variables=var,
                )
            )
            if isinstance(response, ToolError):
                return response
            return response

        except Exception as ex:
            error_traceback = traceback.format_exc(limit=TRACEBACK_LIMIT)
            logger.error(
                f"{method_name} failed: {ex.__class__.__name__} - {str(ex)}\n{error_traceback}"
            )

            return ToolError(
                message=f"{method_name} failed: got err {ex}. Trace available in server logs.",
            )

    def _escape_special_characters(
        search_term: str,
    ) -> Union[str, ToolError]:  # Return type can be str or ToolError
        """
        Escapes special characters in the search term to prevent SQL injection.
        Args:
            search_term (str): The search term to be sanitized.
        Returns:
            Union[str, ToolError]: The sanitized search term or a ToolError if an error occurs.
        """
        method_name = "escape_special_characters"
        # See https://ibm.ent.box.com/notes/2077071409888 for list of escape characters
        try:

            # Escape special characters using the escape function from the regular expression module

            # Define the pattern for special characters to escape
            pattern = r"([\*\@\[\]\{\}\\\^\:\=\!\/\>\<\-\%\+\?\;\'\~\|])"  # Matches
            # Asterisk (*)	Used as a wildcard character.
            # At sign (@)	A syntax error is generated when an at sign is the first character of a query. In xmlxp expressions, the at sign is used to refer to an attribute.
            # Brackets ([])	Used in xmlxp expressions to search the contents of elements and attributes.
            # Braces ({})	Generates a syntax error.
            # Backslash (\)
            # Caret (^)	Used for weighting (boosting) terms.
            # Colon (:)	Used to search the contents of a field.
            # Equal sign (=)	Generates a syntax error.
            # Exclamation point (!)	A syntax error is generated when an exclamation point is the first character of a query.
            # Forward slash (/)	Used in xmlxp expressions as an element path separator.
            # Greater than symbol (>)	Used in xmlxp expressions to compare the value of an attribute. Otherwise, a syntax error is generated.
            # Less than symbol (<)	Used in xmlxp expressions to compare the value of an attribute. Otherwise, a syntax error is generated.
            # Minus sign (-)	When a minus sign is the first character of a term, only documents that do not contain the term are returned.
            # Parentheses	Used for grouping.
            # Percent sign (%)	Specifies that a search term is optional.
            # Plus sign (+)
            # Question mark (?)	Used as a wildcard character.
            # Semicolon (;)
            # Single quotation mark (')	Used to contain xmlxp expressions. To escape a single quotation mark, use another single quotation mark instead of a backslash.
            # Tilde (~)	Used for proximity and fuzzy searches.
            # Vertical bar (|)

            # Use re.sub to replace each special character with its escaped version
            # Escape the special characters in the search term
            sanitized_search_term = re.sub(pattern, r"\\\1", search_term)
            return sanitized_search_term
        except Exception as e:
            return ToolError(
                message=f"{method_name}: Error executing search: {str(e)}",
                suggestions=[],  # Empty suggestions list
            )

    async def _check_if_doc_class_is_CBR_enabled(
        doc_class: str, graphql_client: GraphQLClient, metadata_cache: MetadataCache
    ) -> Union[bool, ToolError]:

        class_metadata = await get_class_metadata_tool(
            graphql_client=graphql_client,
            class_symbolic_name=doc_class,
            metadata_cache=metadata_cache,
        )
        # If there was an error retrieving the class metadata, return it
        if isinstance(class_metadata, ToolError):
            return class_metadata
        if class_metadata is None:
            return ToolError(message=f"Class {doc_class} not found")
        if class_metadata.is_CBR_enabled:
            return True
        return False  # if flag is not set (None), treat it as false
