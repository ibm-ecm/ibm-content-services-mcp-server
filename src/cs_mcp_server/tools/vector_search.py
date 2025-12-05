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
import os
import uuid
from typing import Union

from mcp.server.fastmcp import FastMCP

from cs_mcp_server.client.graphql_client import GraphQLClient
from cs_mcp_server.utils.common import ToolError
from cs_mcp_server.utils.constants import (
    DEFAULT_MAX_CHUNKS,
    DEFAULT_RELEVANCE_SCORE,
    GENAI_VECTOR_QUERY_CLASS,
)

# Environment variables for configuration
MAX_CHUNKS = int(os.environ.get("MAX_CHUNKS", DEFAULT_MAX_CHUNKS))
RELEVANCE_SCORE = float(os.environ.get("RELEVANCE_SCORE", DEFAULT_RELEVANCE_SCORE))


def register_vector_search_tool(mcp: FastMCP, graphql_client: GraphQLClient) -> None:
    @mcp.tool(name="vector_search_tool")
    async def vector_search_tool(prompt: str) -> Union[dict, ToolError]:
        """
        Get document ids matching the prompt. Execute only if the user requests for vector search specifically.

        :returns: A dict of doc ids
        """
        max_chunks = MAX_CHUNKS
        query = """
            mutation createVectorQuery($repo:String!, $prompt:String!, $maxchunks:Int,
            $className:String!){
            createCmAbstractPersistable(repositoryIdentifier: $repo,
            classIdentifier:$className,
            cmAbstractPersistableProperties:
            {
                properties:
                [
                {
                GenaiLLMPrompt: $prompt
                },
                {
                GenaiPerformLLMQuery: false
                },
                {
                GenaiMaxDocumentChunks: $maxchunks
                }
                ]
            })
            {
                id
                name
                creator
                properties(includes:[
                "GenaiVectorChunks"
                
                ])
                {
                
                value
                }
            }
            }
            """

        variables = {
            "repo": graphql_client.object_store,
            "prompt": prompt,
            "maxchunks": max_chunks,
            "className": GENAI_VECTOR_QUERY_CLASS,
        }

        response = await graphql_client.execute_async(query=query, variables=variables)

        try:
            chunks = response["data"]["createCmAbstractPersistable"]["properties"][0][
                "value"
            ]

            if not chunks:
                return {}
            data = json.loads(chunks)

            docs_list = data.get("docs", [])  # Provide an empty list as a default
            id_dict = {}
            if not docs_list:
                pass  # TODO
            else:
                index = 0
                for i, item in enumerate(docs_list):
                    # Use chaining .get() methods to safely access nested values

                    onedoc = item.get("doc", {})
                    doc_id = onedoc.get("metadata", {}).get("id")

                    score = item.get("score")
                    if doc_id and score >= RELEVANCE_SCORE:

                        guid_doc_id = convert_guid(doc_id)
                        if guid_doc_id not in id_dict.keys():
                            doc_title = onedoc.get("metadata", {}).get("originaltitle")
                            id_dict[guid_doc_id] = doc_title
                            index = index + 1

            return id_dict
        except Exception as e:

            return ToolError(
                message=f"{vector_search_tool} failed: got err {e}",
            )

    def convert_guid(hex_string: str) -> str:
        """
        Convert a 32-character hex string to standard GUID format (8-4-4-4-12).

        Uses Python's uuid module for validation and formatting.

        :param hex_string: A 32-character hexadecimal string without hyphens
        :return: A formatted GUID string with hyphens, or the original string if invalid
        """
        try:
            # Try to create a UUID object from the hex string
            # This validates the format and handles the conversion
            uuid_obj = uuid.UUID(hex_string)
            # Return the string representation which is in 8-4-4-4-12 format
            return str(uuid_obj)
        except (ValueError, AttributeError):
            # Return the original string if it's not a valid hex string
            return hex_string
