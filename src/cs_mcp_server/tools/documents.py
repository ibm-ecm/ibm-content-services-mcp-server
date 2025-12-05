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
from typing import Any, List, Optional, Union

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from cs_mcp_server.cache.metadata import MetadataCache
from cs_mcp_server.cache.metadata_loader import get_class_metadata_tool
from cs_mcp_server.client.graphql_client import GraphQLClient
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
        query = """
        query getDocumentTextExtract($object_store_name: String!, $identifier: String!) {
            document(repositoryIdentifier: $object_store_name, identifier: $identifier) {
                annotations{
                    annotations{
                        id
                        name
                        className
                        annotatedContentElement
                        descriptiveText
                        contentElements{
                            ... on ContentTransfer{
                                downloadUrl
                                retrievalName
                                contentSize
                            }
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

        # First run execute_async and wait for the result
        result = await graphql_client.execute_async(query=query, variables=variables)

        # Initialize an empty string to store all text content
        all_text_content = ""

        # Check if we have a valid result with annotations
        if (
            result
            and "data" in result
            and result["data"]
            and "document" in result["data"]
            and result["data"]["document"]
            and "annotations" in result["data"]["document"]
            and result["data"]["document"]["annotations"]
            and "annotations" in result["data"]["document"]["annotations"]
        ):
            annotations = result["data"]["document"]["annotations"]["annotations"]

            # Process each annotation
            for annotation in annotations:
                if (
                    "contentElements" in annotation
                    and annotation["className"] == TEXT_EXTRACT_ANNOTATION_CLASS
                    and annotation["annotatedContentElement"] is not None
                ):
                    # Process each content element
                    for content_element in annotation["contentElements"]:
                        if (
                            "downloadUrl" in content_element
                            and content_element["downloadUrl"]
                        ):
                            # Download the text content using the downloadUrl
                            download_url = content_element["downloadUrl"]
                            text_content = await graphql_client.download_text_async(
                                download_url
                            )

                            # Append the text content to our result string
                            if text_content:
                                if all_text_content:
                                    all_text_content += TEXT_EXTRACT_SEPARATOR
                                all_text_content += text_content

        return all_text_content

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

        :param classIdentifier: The class identifier for the document. If not provided, defaults to "Document".
        :param id: The unique GUID for the document. If not provided, a new GUID with curly braces will be generated.
        :param documentProperties: Properties for the document including name, content, mimeType, etc.
        :param fileInFolderIdentifier: The identifier or path of the folder to file the document in. This always starts with "/".
        :param checkinAction: Check-in action parameters. CheckinMinorVersion should always be included.
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
        name="get_class_specific_properties_name",
    )
    async def get_class_specific_properties_name(
        identifier: str,
    ) -> Union[dict, list, ToolError]:
        """
        Retrieves a list of class-specific property names for a document based on its class definition.

        This tool first determines the document's class, then fetches the class metadata to identify
        all available properties specific to that document class. It filters out system properties and
        hidden properties.

        Use this tool when you need to know what custom properties are available for a specific document,
        which can then be used for targeted property extraction or search operations.

        :param identifier: The document id or path (required). This can be either the document's ID (GUID)
                          or its path in the repository (e.g., "/Folder1/document.pdf").

        :returns: A list of property display names that are available for the document's class.
                 These properties can be used for further operations like property extraction or search.
        """
        # First, get the class name of the document
        query = """
        query getDocument($object_store_name: String!, $identifier: String!){
            document(repositoryIdentifier: $object_store_name, identifier: $identifier){
                className
            }
        }
        """

        var: dict[str, Any] = {
            "identifier": identifier,
            "object_store_name": graphql_client.object_store,
        }

        response = graphql_client.execute(query=query, variables=var)

        if "errors" in response:
            return response

        classname = response["data"]["document"]["className"]

        # Use get_class_metadata_tool to get the class properties
        class_metadata = get_class_metadata_tool(
            graphql_client=graphql_client,
            class_symbolic_name=classname,
            metadata_cache=metadata_cache,
        )

        if isinstance(class_metadata, ToolError):
            return class_metadata

        # Apply the same filtering logic as the original implementation
        property_list = []
        not_allowed_cardinality = [Cardinality.ENUM]
        not_allowed_data_type = [TypeID.OBJECT, TypeID.BINARY]
        not_include_property_name = EXCLUDED_PROPERTY_NAMES

        try:
            for prop in class_metadata.property_descriptions:
                if (
                    prop.data_type in not_allowed_data_type
                    or prop.cardinality in not_allowed_cardinality
                    or prop.symbolic_name in not_include_property_name
                    or prop.is_system_owned is True
                    or prop.is_hidden is True
                ):
                    continue
                property_list.append(prop.display_name)
        except Exception as e:
            return ToolError(
                message=f"Error processing property descriptions: {e}",
                suggestions=[
                    "Make sure the class exists",
                    "Check if the metadata cache is properly initialized",
                ],
            )

        return property_list

    @mcp.tool(
        name="update_document_properties",
    )
    async def update_document_properties(
        identifier: str,
        document_properties: Optional[DocumentPropertiesInput] = None,
    ) -> Union[Document, ToolError]:
        """
        **PREREQUISITES IN ORDER**: To use this tool, you MUST call get_class_property_descriptions first
        to get a list of valid properties for the document's current class.

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
        **PREREQUISITES IN ORDER**: To use this tool, you MUST call determine_class first
        to get the new class_identifier.

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
            response = await graphql_client.execute_async(
                query=mutation, variables=variables
            )

            # Handle errors
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")

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
            response = await graphql_client.execute_async(
                query=mutation, variables=variables
            )

            # Handle errors
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")

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
            response = await graphql_client.execute_async(
                query=mutation, variables=variables
            )

            # Handle errors
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")

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
            response = await graphql_client.execute_async(
                query=query, variables=variables
            )

            # Handle errors
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")

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
            response = await graphql_client.execute_async(
                query=mutation, variables=variables
            )

            # Handle errors
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")

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
