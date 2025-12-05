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
from typing import Union

from mcp.server.fastmcp import FastMCP

from cs_mcp_server.client.graphql_client import GraphQLClient
from cs_mcp_server.utils.constants import TRACEBACK_LIMIT
from cs_mcp_server.utils import ToolError, Annotation

# Logger for this module
logger = logging.getLogger(__name__)


def register_annotation_tools(mcp: FastMCP, graphql_client: GraphQLClient) -> None:

    @mcp.tool(
        name="get_document_annotations_tool",
    )
    async def get_document_annotations_tool(
        document_id: str,
    ) -> Union[list[Annotation], ToolError]:
        """
        Retrieves all annotations associated with a document.

        This tool fetches annotation metadata including creator, dates, descriptive text,
        and content element information. Use this to analyze document annotations or
        to identify specific annotations for further processing.

        :param document_id: The document ID to retrieve annotations for.

        :returns: A dictionary containing document annotations with the following structure:
                - data.document.annotations.annotations: List of annotation objects, each containing:
                    - className: The class name of the annotation
                    - creator: The creator of the annotation
                    - dateCreated: Creation timestamp
                    - dateLastModified: Last modification timestamp
                    - id: Unique identifier of the annotation
                    - name: Name of the annotation
                    - owner: Owner of the annotation
                    - descriptiveText: Text description of the annotation
                    - contentSize: Size of the annotation content
                    - mimeType: MIME type of the annotation
                    - annotatedContentElement: Content element being annotated
                    - contentElementsPresent: Whether content elements are present
                    - contentElements: List of content elements with className, contentType, and sequence

                Returns ToolError if the document doesn't exist or another error occurs.
        """
        method_name: str = "get_document_annotations"

        if not document_id or not isinstance(document_id, str):
            return ToolError(
                message="Invalid document ID provided",
                suggestions=["Provide a valid document ID string"],
            )

        # Extract query to a constant for better maintainability
        ANNOTATIONS_QUERY = """
        query getDocumentAnnotations($object_store_name: String!, $document_id: String!){
            document(repositoryIdentifier: $object_store_name, identifier: $document_id){
                annotations {
                    annotations {
                        className
                        creator
                        dateCreated
                        dateLastModified
                        id
                        name
                        owner
                        descriptiveText
                        contentSize
                        mimeType
                        annotatedContentElement
                        contentElementsPresent
                        contentElements {
                            className
                            contentType
                            elementSequenceNumber
                        }
                    }
                }
            }
        }
        """

        variables = {
            "document_id": document_id,
            "object_store_name": graphql_client.object_store,
        }

        try:
            result = await graphql_client.execute_async(
                query=ANNOTATIONS_QUERY, variables=variables
            )

            # Check for no result returned before checking if there is "errors" key in the result dictionary
            if result is None:
                return ToolError(
                    message="No annotations found or invalid document",
                    suggestions=[
                        "Verify the document exists",
                        "Check if the document has any annotations",
                    ],
                )

            # Check for GraphQL errors
            if "errors" in result:
                return ToolError(
                    message=f"GraphQL error: {result['errors'][0]['message']}",
                    suggestions=[
                        "Verify the document ID exists",
                        "Check if you have permission to access this document",
                    ],
                )

            # Check for empty or invalid response
            if (
                not result
                or "data" not in result
                or not result["data"]
                or "document" not in result["data"]
                or not result["data"]["document"]
                or "annotations" not in result["data"]["document"]
            ):
                return ToolError(
                    message="No annotations found or invalid document",
                    suggestions=[
                        "Verify the document exists",
                        "Check if the document has any annotations",
                    ],
                )

            annotations_list = result["data"]["document"]["annotations"]["annotations"]
            if len(annotations_list) == 0:
                return []
            else:
                contained_annotations = []
                for annotation in annotations_list:
                    a_annotation = Annotation.create_an_instance(
                        graphQL_changed_object_dict=annotation,
                        class_name=annotation["className"],
                    )
                    contained_annotations.append(a_annotation)
                return contained_annotations

        except Exception as e:
            error_traceback = traceback.format_exc(limit=TRACEBACK_LIMIT)
            logger.error(
                f"{method_name} failed: {e.__class__.__name__} - {str(e)}\n{error_traceback}"
            )
            return ToolError(
                message=f"Error retrieving annotations: {str(e)}",
                suggestions=[
                    "Check network connectivity",
                    "Verify GraphQL endpoint is accessible",
                    "Ensure document ID is valid",
                ],
            )
