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

import json
import logging
import re
import traceback
import uuid
from typing import Optional, Union

from mcp.server.fastmcp import FastMCP

from cs_mcp_server.client import GraphQLClient
from cs_mcp_server.utils import ToolError
from cs_mcp_server.utils.model.core import NULL_VALUE, Document, Folder
from cs_mcp_server.utils.model.coreInput import FolderPropertiesInput
from cs_mcp_server.utils.constants import (
    DEFAULT_FOLDER_CLASS,
    TRACEBACK_LIMIT,
)

# Logger for this module
logger = logging.getLogger(__name__)


def register_folder_tools(mcp: FastMCP, graphql_client: GraphQLClient) -> None:
    @mcp.tool(
        name="create_folder",
    )
    def create_folder(
        name: str,
        parent_folder: str,
        class_identifier: Optional[str] = None,
        id: Optional[str] = None,
        folder_properties: Optional[FolderPropertiesInput] = None,
    ) -> Union[Folder, ToolError]:
        """
        **PREREQUISITES IN ORDER**: To use this tool, you MUST call two other tools first in a specific sequence.
        1. determine_class tool to get the class_identifier.
        2. get_class_property_descriptions to get a list of valid properties for the given class_identifier


        Creates a folder in the content repository with specified properties. This tool interfaces with the GraphQL API
        to create a new folder object with the provided parameters.

        :param name	string	Yes	The name of the folder to be created.
        :param parent_folder	string	Yes	The identifier of the parent folder where this folder will be created.
        :param class_identifier	string	No	The class identifier for the folder. If not provided, defaults to "Folder".
        :param id	string	No	The unique identifier for the folder. If not provided, a new UUID with curly braces will be generated (format: {uuid}).
        :param folder_properties	FolderPropertiesInput No properties of to set.

        :returns: If successful, return a folder object with the following properties:
            id: The identifier of the created folder
            name: The name of the folder
            parent_folder: The identifier of the parent folder
            creator: The user who created the folder
            class_identifier: The class identifier of the folder
         Else, return a ToolError instance that describes the error.
        """
        method_name = "create_folder"
        try:
            if not id:
                id = "{" + str(uuid.uuid4()) + "}"
            if not class_identifier:
                class_identifier = DEFAULT_FOLDER_CLASS
            mutation = """
                    mutation createFolder($repo:String!, $id:ID!
                    $className:String, $folderProperties:FolderPropertiesInput!)
                    {
                    createFolder(repositoryIdentifier: $repo,
                        classIdentifier:$className,
                        id: $id
                        folderProperties: $folderProperties
                    )
                    {
                        id
                        className
                        properties {
                        id
                        value
                    }
                    }
                    }
            """

            # Build base folder properties
            base_properties = {"name": name, "parent": {"identifier": parent_folder}}

            # Process folder properties if provided
            all_properties = base_properties
            if folder_properties:
                base_dict = folder_properties.model_dump(exclude_none=True)
                if "properties" not in base_dict or not base_dict["properties"]:
                    pass  # Continue processing even if there are no properties
                else:
                    try:
                        transformed_props = folder_properties.transform_properties_dict(
                            exclude_none=True
                        )
                        all_properties = {**base_properties, **transformed_props}
                    except Exception as e:
                        logger.error("Error transforming folder properties: %s", str(e))
                        logger.error(traceback.format_exc())
                        return ToolError(
                            message=f"{method_name} failed: {str(e)}. Trace available in server logs."
                        )
            logger.info(json.dumps(all_properties, indent=2))
            var = {
                "repo": graphql_client.object_store,
                "folderProperties": all_properties,
                "id": id,
                "className": class_identifier,
            }

            response = graphql_client.execute(query=mutation, variables=var)
            # handling exception, for example duplicate folder name
            if "errors" in response:
                return ToolError(
                    message=f"create_folder failed: got err {response}.",
                )

            # return response["data"]["createFolder"]
            return Folder.create_an_instance(
                graphQL_changed_object_dict=response["data"]["createFolder"],
                class_identifier=response["data"]["createFolder"]["className"],
            )

        except Exception as e:
            error_traceback = traceback.format_exc(limit=TRACEBACK_LIMIT)
            logger.error(
                f"{method_name} failed: {e.__class__.__name__} - {str(e)}\n{error_traceback}"
            )

            return ToolError(
                message=f"{method_name} failed: got err {e}. Trace available in server logs.",
            )

    @mcp.tool(
        name="delete_folder",
    )
    def delete_folder(id_or_path: str) -> Union[str, ToolError]:
        """
        Deletes a folder in the content repository. This tool interfaces with the GraphQL API
        to delete a folder object with the provided id.


        :param id_or_path	string	Yes	The unique identifier or path for the folder. If not provided, an error will be returned.

        :returns: If successful, return the folder id.
         Else, return a ToolError instance that describes the error.
        """
        method_name = "delete_folder"
        try:
            # dcheck id or path
            if not id_or_path:
                return ToolError(
                    message=f"delete_folder failed: id is a required input.",
                )

            mutation = """
                    mutation deleteFolder( $id_or_path:String!
                    $repo: String!)
                    {
                    deleteFolder(repositoryIdentifier: $repo, 
                        identifier: $id_or_path
                    )
                    {
                        id
                        className
                    }
                    }
            """
            var = {
                "repo": graphql_client.object_store,
                "id_or_path": id_or_path,
            }
            response = graphql_client.execute(query=mutation, variables=var)
            # handling exception, for example duplicate folder name
            if "errors" in response:
                return ToolError(
                    message=f"delete_folder failed: got err {response}.",
                )
            return_id = response["data"]["deleteFolder"]["id"]

            return response["data"]["deleteFolder"]["id"]

        except Exception as e:
            error_traceback = traceback.format_exc(limit=TRACEBACK_LIMIT)
            logger.error(
                f"{method_name} failed: {e.__class__.__name__} - {str(e)}\n{error_traceback}"
            )

            return ToolError(
                message=f"{method_name} failed: got err {e}. Trace available in server logs.",
            )

    @mcp.tool(
        name="unfile_document",
    )
    async def unfile_document(
        folder_id_or_path: str, document_id: str
    ) -> Union[str, ToolError]:
        """
        Unfile a document from a folder in the content repository. This tool interfaces with the GraphQL API
        to unfile document from folder with the provided ids.


        :param folder_id_or_path	string	Yes	The unique identifier or path for the folder. If not provided, an error will be returned.
        :param document_id	string	Yes	The unique identifier for the document. If not provided, an error will be returned.

        :returns: If successful, return the folder id.
         Else, return a ToolError instance that describes the error.
        """
        method_name = "unfile_document"
        try:
            # check folder id or path and documetn id
            if not folder_id_or_path:
                return ToolError(
                    message=f"unfile_document failed: folder id or path is a required input.",
                )
            if not document_id:
                return ToolError(
                    message=f"unfile_document failed: document id is a required input.",
                )

            mutation = """
            query rcr($repo:String!,$where_clause: String!)
                {
                repositoryObjects(repositoryIdentifier:$repo
                from: "ReferentialContainmentRelationship"
                where : $where_clause)
                {
                    independentObjects
                    {
                    ... on ReferentialContainmentRelationship
                    {
                        id
                        tail {
                        id
                        }
                        head
                        {
                        id
                        }
                    }
                    }
                }
                }
                    
            """

            formatted_folder_value = ""
            if is_guid_with_braces(folder_id_or_path):
                formatted_folder_value = f"({folder_id_or_path})"
            else:
                formatted_folder_value = lookup_folder_id(
                    folder_name=folder_id_or_path, graphql_client=graphql_client
                )
            if type(formatted_folder_value) is ToolError:
                return formatted_folder_value
            formatted_document_value = f"({document_id})"
            condition_string = (
                f"tail = {formatted_folder_value} and head = {formatted_document_value}"
            )
            var = {
                "repo": graphql_client.object_store,
                "where_clause": condition_string,
            }
            response = graphql_client.execute(query=mutation, variables=var)
            # handling exception
            if "errors" in response:
                return ToolError(
                    message=f"unfile_document failed: got err {response}.",
                )

            return_rcr = response["data"]["repositoryObjects"]["independentObjects"]
            return_id = ""
            if len(return_rcr) > 0:
                if len(return_rcr) > 1:
                    return ToolError(
                        message=f"unfile_document failed: this document has been filed more than once in the folder.",
                    )
                return_id = return_rcr[0]["id"]
            else:
                return ToolError(
                    message=f"unfile_document failed: no such document in the folder.",
                )

            mutation = """
                mutation deleteRcr($repo:String!,
                    $id:String!)
                    {
                    deleteReferentialContainmentRelationship(repositoryIdentifier: $repo, 
                        identifier:$id
                    )
                    {
                    
                    id
                    }                 
                    }
            """
            var = {"repo": graphql_client.object_store, "id": return_id}
            response = await graphql_client.execute_async(query=mutation, variables=var)
            if "errors" in response:
                return ToolError(
                    message=f"unfile_document failed: got err {response}.",
                )
            return response["data"]["deleteReferentialContainmentRelationship"]["id"]

        except Exception as e:
            error_traceback = traceback.format_exc(limit=TRACEBACK_LIMIT)
            logger.error(
                f"{method_name} failed: {e.__class__.__name__} - {str(e)}\n{error_traceback}"
            )

            return ToolError(
                message=f"{method_name} failed: got err {e}. Trace available in server logs.",
            )

    def lookup_folder_id(
        folder_name: str, graphql_client: GraphQLClient
    ) -> Union[str, ToolError]:
        """
        Retrieves the folder id for the given folder name.
        """
        query = """ 
                        query folder($repo:String!, $folder_name: String!)   
            {
            folder(repositoryIdentifier:$repo
            identifier:$folder_name)
            {
                id
            }
            } 
        """

        vars = {"repo": graphql_client.object_store, "folder_name": folder_name}
        response = graphql_client.execute(
            query, vars
        )  # Changed from execute_graphql to execute

        if "errors" in response:
            return ToolError(
                message=f"lookup_folder_id failed: got err {response}.",
            )
        else:
            return response["data"]["folder"]["id"]

    def is_guid_with_braces(input_string):
        """
        Check if a string is a valid GUID/UUID with curly braces.

        Args:
            input_string (str): The string to check

        Returns:
            bool: True if the string is a valid GUID with curly braces, False otherwise
        """
        # Check if string starts with '{' and ends with '}'
        if not (input_string.startswith("{") and input_string.endswith("}")):
            return False

        # Remove the curly braces
        guid_string = input_string[1:-1]

        # Pattern for UUID: 8-4-4-4-12 hexadecimal digits
        pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

        # Case-insensitive match
        if re.match(pattern, guid_string, re.IGNORECASE):
            return True

        # Alternative validation using uuid module
        try:
            uuid_obj = uuid.UUID(guid_string)
            return str(uuid_obj) == guid_string.lower()
        except ValueError:
            return False

    @mcp.tool(
        name="update_folder",
    )
    async def update_folder(
        identifier: str,
        class_identifier: Optional[str] = None,
        folder_properties: Optional[FolderPropertiesInput] = None,
    ) -> Union[Folder, ToolError]:
        """
        **PREREQUISITES IN ORDER**: To use this tool, you MUST call two other tools first in a specific sequence.
        1. determine_class tool to get the class_identifier.
        2. get_class_property_descriptions to get a list of valid properties for the given class_identifier

        Description:
        Updates an existing folder in the content repository with specified properties.

        :param identifier: String The folder identifier or path (required). This can be either the folder's ID (GUID) or its path in the repository (e.g., "/Folder1/folder123").
        :param class_identifier: String Optional. The class identifier for the folder. If provided, allows changing the folder's class.
        :param folder_properties: FolderPropertiesInput Properties to update for the folder including name, etc

        :returns: If successful, returns a Folder object with its updated properties.
                 If unsuccessful, returns a ToolError with details about the failure.
        """
        method_name = "update_folder"
        try:
            # Prepare the mutation
            if class_identifier:
                mutation = """
                mutation ($object_store_name: String!, $identifier: String!, $class_identifier: String,
                        $folder_properties: FolderPropertiesInput) {
                updateFolder(
                    repositoryIdentifier: $object_store_name
                    identifier: $identifier
                    classIdentifier: $class_identifier
                    folderProperties: $folder_properties
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
            else:
                mutation = """
                mutation ($object_store_name: String!, $identifier: String!, 
                        $folder_properties: FolderPropertiesInput) {
                updateFolder(
                    repositoryIdentifier: $object_store_name
                    identifier: $identifier
                    
                    folderProperties: $folder_properties
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
                # "class_identifier": class_identifier if class_identifier else NULL_VALUE,
                "folder_properties": None,
            }
            if class_identifier:
                variables["class_identifier"] = class_identifier
            # Process folder properties if provided
            if folder_properties:
                try:
                    transformed_props = folder_properties.transform_properties_dict(
                        exclude_none=True
                    )

                    variables["folder_properties"] = transformed_props
                except Exception as e:
                    logger.error("Error transforming folder properties: %s", str(e))
                    logger.error(traceback.format_exc())
                    return ToolError(
                        message=f"{method_name} failed: {str(e)}. Trace available in server logs."
                    )

            # Execute the GraphQL mutation
            logger.info("Executing folder update")
            response = await graphql_client.execute_async(
                query=mutation, variables=variables
            )

            # Handle errors
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")

            # Create and return a folder instance from the response
            return Folder.create_an_instance(
                graphQL_changed_object_dict=response["data"]["updateFolder"],
                class_identifier=(
                    class_identifier if class_identifier else DEFAULT_FOLDER_CLASS
                ),
            )

        except Exception as e:
            logger.error("%s failed: %s", method_name, str(e))
            logger.error(traceback.format_exc())
            return ToolError(
                message=f"{method_name} failed: {str(e)}. Trace available in server logs."
            )

    @mcp.tool(
        name="get_folder_documents",
    )
    async def get_folder_documents(
        folder_id_or_path: str,
    ) -> Union[list[Document], ToolError]:
        """
        Retrieves a folder's contained documents.

        :param folder_id_or_path: The folder id or path.

        :returns: A list contains documents in the folder
        """

        method_name = "get_folder_documents"
        logger.info("%s started", method_name)
        try:
            query = """
            query getContainedDocuments($object_store_name: String!, $folder_id_or_path: String!){
                folder(
                    repositoryIdentifier: $object_store_name
                    identifier: $folder_id_or_path
                ) {
                    containedDocuments
                        {
                        documents
                        {
                            id
                            name
                            className
                            properties
                            {
                            id
                            value
                            }
                        }
                        }
                }
            }
            """

            variables = {
                "folder_id_or_path": folder_id_or_path,
                "object_store_name": graphql_client.object_store,
            }

            # return await graphql_client.execute_async(query=query, variables=variables)
            docs = await graphql_client.execute_async(query=query, variables=variables)

            if "errors" in docs:
                return ToolError(
                    message=f"get_folder_documents failed: got err {docs}.",
                )

            docslist = docs["data"]["folder"]["containedDocuments"]["documents"]
            if len(docslist) == 0:
                return []
            else:
                contained_docs = []
                for doc in docslist:
                    onedoc = Document.create_an_instance(
                        graphQL_changed_object_dict=doc,
                        class_identifier=doc["className"],
                    )
                    contained_docs.append(onedoc)
                return contained_docs
        except Exception as ex:
            error_traceback = traceback.format_exc(limit=TRACEBACK_LIMIT)
            logger.error(
                f"{method_name} failed: {ex.__class__.__name__} - {str(ex)}\n{error_traceback}"
            )

            return ToolError(
                message=f"{method_name} failed: got err {ex}. Trace available in server logs.",
            )
