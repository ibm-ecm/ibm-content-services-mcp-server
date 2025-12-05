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
mcp_manage_hold.py module define all MCP tools that provide legal hold functionality.

"""

import logging
import traceback
from typing import Union, Optional

from mcp.server.fastmcp import FastMCP

from cs_mcp_server.client import GraphQLClient
from cs_mcp_server.utils import HoldRelationship, ToolError
from cs_mcp_server.utils.constants import (
    CM_HOLD_CLASS,
    CM_HOLD_RELATIONSHIP_CLASS,
    ID_PROPERTY,
    HELD_OBJECT_PROPERTY,
    TRACEBACK_LIMIT,
)


# Logger for this module
logger = logging.getLogger(__name__)


def register_legalhold(mcp: FastMCP, graphql_client: GraphQLClient) -> None:
    """
    Register to MCP server all the legal hold tools.
    """

    def find_hold_relationship_object(
        hold_object_id: str, held_object_id: str
    ) -> Optional[str]:
        """
        :returns: the id of the CmHoldRelationship object, or None if no relationship is found.
        """

        query = """
        query getCmRelationshipObject ($object_store_name: String!, 
            $where_clause: String!
            ) {
                repositoryObjects(
                    repositoryIdentifier: $object_store_name,
                    from: "CmHoldRelationship",
                    where: $where_clause
                ) {
                independentObjects {
                    className
                    properties {
                        id
                        value
                    }
                }
            }
        }
        """

        formatted_hold_value = f"({{hold_object_id}})"
        formatted_held_value = f"({{held_object_id}})"
        condition_string = f"[Hold] = Object {formatted_hold_value} and [HeldObject] = Object {formatted_held_value}"

        var = {
            "object_store_name": graphql_client.object_store,
            "where_clause": condition_string,
        }

        response = graphql_client.execute(query=query, variables=var)

        if "errors" in response:
            return None

        # return the id of the CmRelationshipObject
        hold_relationships = response["data"]["repositoryObjects"]["independentObjects"]
        # walk thru each relationship object,
        for item in hold_relationships:
            properties = item["properties"]
            for prop in properties:
                if prop["id"] == ID_PROPERTY:
                    return prop["value"]

        return None

    @mcp.tool(
        name="release_an_object_from_hold_tool",
    )
    def release_an_object_from_hold_tool(
        hold_id: str, held_id: str
    ) -> Union[dict, ToolError]:
        """
        Remove a hold on a held object given a hold id and a held id.

        :param hold_id: The hold id.
        :param held_id: The held id.

        :returns: If successful, return a dict describing that the hold has been removed from the held object.
                  Else, return a ToolError instance that describes the error.
        """

        #    A CmHoldRelationship is an object that has 2 fields to associate a Hold Id with a Held Id.

        #    To figure out the Hold Id, one can use the tool get_repository_object_main to look for
        #    objects of CmHold class given some criteria to look up a hold, for example a unique displayName.

        #    To figure out the Held Id, one can use the tool get_repository_object_main to look for
        #    objects of CmHoldable class given some criteria to look up a document, annotation, folder that
        #    should be removed from the hold.

        # look for an Object of CmHoldRelationship with the passed in Hold id and Held Id
        method_name = "release_an_object_from_hold_tool"
        try:
            hold_relationship_id = find_hold_relationship_object(hold_id, held_id)
            if hold_relationship_id is None:
                # Return a dictionary with information instead of None
                return {
                    "status": "no_action_needed",
                    "message": "No hold relationship found between the specified hold and held object.",
                }

            mutation = """
            mutation ($object_store_name: String!, 
                $hold_relationship_class_name: String!, 
                $hold_relationship_id: String!
                ) {
                changeObject(
                    repositoryIdentifier: $object_store_name,
                    identifier: $hold_relationship_id,
                    classIdentifier: $hold_relationship_class_name,
                    actions:[
                    {
                        type:DELETE
                    }
                    ]
                ) {
                    className
                    objectReference {
                        repositoryIdentifier
                        classIdentifier
                        identifier
                    }
                    properties {
                        id
                        value
                    }
                }
            }
            """

            var = {
                "object_store_name": graphql_client.object_store,
                "hold_relationship_class_name": CM_HOLD_RELATIONSHIP_CLASS,
                "hold_relationship_id": hold_relationship_id,
            }

            response = graphql_client.execute(query=mutation, variables=var)
            # handling exception, for example bad value for hold id
            if "errors" in response:
                return ToolError(
                    message=f"{method_name} failed: got err {response}.",
                )

            # return the information for all the objects that this hold now has
            return response["data"]["changeObject"]
        except Exception as e:
            return ToolError(
                message=f"{method_name} failed: got err {e}",
            )

    @mcp.tool(
        name="remove_a_hold_tool",
    )
    def remove_a_hold_tool(hold_object_id: str) -> Union[dict, ToolError]:
        """
        Remove a hold.  This action will release all objects that are held by the hold identified
        by the hold_object_id.

        :param hold_object_id: The hold object id to which all the held objects are identified.

        :returns: If successful, return a dict describing that the hold object has just been deleted.
                  Else, return a ToolError instance that describes the error.
        """

        method_name = "remove_a_hold_tool"
        try:
            mutation = """
            mutation ($object_store_name: String!, 
            	$hold_identifier: String!
                ) {
                changeObject(
                    classIdentifier: "CmHold",
                    identifier: $hold_identifier,
                    repositoryIdentifier: $object_store_name,
                    actions:[
                    {  
                        type:DELETE
                    }     
                    ]     
                )     
                {       
                    className
                    objectReference {
                        repositoryIdentifier
                        classIdentifier
                        identifier
                    }   
                    properties(includes:["Id"]) {
                        id  
                        label
                        type
                        cardinality
                        value
                    }
                }
            }
            """
            var = {
                "object_store_name": graphql_client.object_store,
                "hold_identifier": hold_object_id,
            }

            response = graphql_client.execute(query=mutation, variables=var)
            # handling exception, for example bad value for hold id
            if "errors" in response:
                return ToolError(
                    message=f"{method_name} failed: got err {response}.",
                )

            # return the information for all the objects that this hold now has
            return response["data"]["changeObject"]
        except Exception as e:
            return ToolError(
                message=f"{method_name} failed: got err {e}",
            )

    @mcp.tool(
        name="create_a_hold_tool",
    )
    def create_a_hold_tool(display_name: str) -> Union[dict, ToolError]:
        """
        Create a CmHold instance with identifying information

        :param display_name: Value of display name for the newly created hold object.

        :returns: If successful, return a dict that describes the newly created object.
                  Else, return a ToolError instance that describes the error.
        """
        return create_a_hold(display_name, hold_class=CM_HOLD_CLASS)

    def create_a_hold(display_name: str, hold_class: str) -> Union[dict, ToolError]:
        """
        Create a hold with identifying information

        :param hold_class: The hold class to instantiate a new object
        :param display_name: Value of display name for the newly created hold object.

        :returns: If successful, return a dict that describes the newly created object.
                  Else, return a ToolError instance that describes the error.
        """
        method_name = "create_a_hold"
        try:
            # TODO: make sure that the subclass symbolic name is derived from a CmHold class
            if not hold_class:
                hold_class = CM_HOLD_CLASS

            # TODO: extract the properties of the new hold and set the properties string

            mutation = """
                    mutation ($object_store_name: String!, $class_name: String!, $display_name: String!) {
                    changeObject(
                        repositoryIdentifier: $object_store_name,
                        properties: [ {
                            displayName: $display_name
                        }
                        ]
                        actions:[
                        {
                            type:CREATE
                            subCreateAction:{
                                classId: $class_name
                            }
                        }
                        ]
                    )
                    {
                        className
                        properties {
                            id
                            value
                        }
                    }
                }
            """
            var = {
                "object_store_name": graphql_client.object_store,
                "class_name": hold_class,
                "display_name": display_name,
            }
            response = graphql_client.execute(query=mutation, variables=var)
            # handling exception, for example bad value for hold id
            if "errors" in response:
                return ToolError(
                    message=f"{method_name} failed: got err {response}.",
                )

            return response["data"]["changeObject"]
        except Exception as e:
            return ToolError(
                message=f"{method_name} failed: got err {e}",
            )

    @mcp.tool(
        name="put_an_object_on_hold_tool",
    )
    def put_an_object_on_hold_tool(
        hold_id: str, held_class: str, held_id: str
    ) -> Union[HoldRelationship, ToolError]:
        """
        Given an identifier for the hold, a class for the held object,
        an identifier for the held object, this tool will add the held object to the hold.

        If the held object is already in the hold, don't need to add it again.

        One can put multiple types of CmHoldable objects in a CmHold object. A CmHoldRelationship
        object is created to persist this relationship.
        Apply a hold to an object. A hold can be put on multiple objects. This tool allow user to add more objects to an existing hold

        :param hold_id:     The hold object id.
        :param held_class:  The held object class.
        :param held_id:     The held object id that is added to the hold.

        :returns: If successful, return a HoldRelationship instance that describes this relationship.
                  Else, return a ToolError instance that describes the error.
        """

        method_name = "put_an_object_on_hold_tool"

        try:
            mutation = """
            mutation ($object_store_name: String!, 
                $hold_identifier: String!,
                $held_class_name: String!, $held_identifier: String!
                ) {
                changeObject(
                    repositoryIdentifier: $object_store_name
                    objectProperties:[
                    {
                        identifier:"Hold"
                        objectReferenceValue:{
                            identifier: $hold_identifier
                        }
                    }
                    {
                        identifier:"HeldObject"
                        objectReferenceValue:{
                            classIdentifier: $held_class_name
                            identifier: $held_identifier
                        }
                    }
                    ]
                    actions:[
                    {
                        type:CREATE
                        subCreateAction:{
                            classId:"CmHoldRelationship"
                        }
                    }
                    ]
                ) {
                    className
                    properties {
                        id
                        value
                    }
                }
            }
            """
            var = {
                "object_store_name": graphql_client.object_store,
                "hold_identifier": hold_id,
                "held_class_name": held_class,
                "held_identifier": held_id,
            }
            response = graphql_client.execute(query=mutation, variables=var)

            # handling exception, for example bad value for hold id
            if response is None:
                return ToolError(
                    message=f"{method_name} failed: No response returned from gql {mutation}",
                )
            if "errors" in response:
                return ToolError(
                    message=f"{method_name} failed: got err {response}",
                )

            # return the information for the new/updated hold relationship
            # Note: There cam only exist 1 hold relationship between a unique hold and held object
            return HoldRelationship.create_an_instance(response["data"]["changeObject"])
        except Exception as e:
            return ToolError(
                message=f"{method_name} failed: got err {e}",
            )

    def get_all_hold_relationships_for_a_hold(
        hold_object_id: str,
    ) -> Union[dict, ToolError]:
        """
        Given a hold object identified by its class and id, return all the hold relationships

        :param hold_id:     The hold object id.

        :returns: If successful, return a dict for independentObjects.
                  Else, return a ToolError instance that describes the error.
        """
        method_name = "get_all_hold_relationships_for_a_hold"
        try:
            query = """
            query getCmRelationshipObjectsForAHold ($object_store_name: String!, 
                $where_clause: String!, 
                ) {
                repositoryObjects(
                    repositoryIdentifier: $object_store_name,
                    from: "CmHoldRelationship",
                    where: $where_clause
                ) {
                independentObjects {
                    className
                    properties (includes: ["HeldObject", "Hold", "Id"]) {
                        id
                        value
                    }
                }
                }
            }
            """

            formatted_hold_value = f"({hold_object_id})"
            condition_string = f"[Hold] = Object {formatted_hold_value}"

            var = {
                "object_store_name": graphql_client.object_store,
                "where_clause": condition_string,
            }

            response = graphql_client.execute(query=query, variables=var)

            # Check for errors in the response
            if response is None:
                return ToolError(
                    message=f"{method_name} failed: No response returned from GraphQL query"
                )
            if "errors" in response:
                return ToolError(
                    message=f"{method_name} failed: GraphQL errors: {response['errors']}"
                )

            return response
        except Exception as e:
            error_traceback = traceback.format_exc(limit=TRACEBACK_LIMIT)
            logger.error(
                f"{method_name} failed: {e.__class__.__name__} - {str(e)}\n{error_traceback}"
            )
            return ToolError(
                message=f"{method_name} failed: got err {e}",
            )

    @mcp.tool(
        name="list_held_objects_for_a_hold_tool",
    )
    async def list_held_objects_for_a_hold_tool(
        hold_object_id: str,
    ) -> Union[list, ToolError]:
        """
        Given a hold object identified by its id, return all the objects that it held

        :param hold_object_id:     The hold object id.

        :returns: If successful, return a list of held objects.
                  Else, return a ToolError instance that describes the error.
        """
        method_name = "list_held_objects_for_a_hold_tool"
        try:
            response = get_all_hold_relationships_for_a_hold(hold_object_id)

            # handling exception, for example bad value for hold id
            if isinstance(response, ToolError):
                return response

            hold_relationships_list = response["data"]["repositoryObjects"][
                "independentObjects"
            ]

            held_objects = []

            # walk thru each relationship object,
            if hold_relationships_list is None:
                return held_objects

            for item in hold_relationships_list:
                properties = item["properties"]
                for prop in properties:
                    if prop["id"] == HELD_OBJECT_PROPERTY:
                        held_objects.append(prop["value"])

            # the returned data only has the repo_id, class_id and object_id to identify the CmHoldable object
            # for example: {'identifier': '{98CE05E0-0000-C193-B573-ACE942EA2512}', 'repositoryIdentifier': 'p8os1', 'classIdentifier': 'Document'}

            # TODO: call search to return more information for these Holdable objects.
            # find some shareable properties in CmHoldable class
            return held_objects
        except Exception as e:
            formatted_trace = (
                traceback.format_exc()
            )  # Returns the traceback as a string
            return ToolError(
                message=f"{method_name} failed: got err {e}. Trace {formatted_trace}",
            )

    @mcp.tool(
        name="list_holds_by_name_tool", description="List all hold objects given a name"
    )
    async def list_holds_by_name_tool(hold_display_name: str) -> Union[dict, ToolError]:
        """
        Search and return CmHold objects where the displayName contains the specified hold_display_name (case-insensitive).

        This method performs a partial match search using SQL LIKE operator with wildcards,
        so it will find holds where the display name contains the search term anywhere in the string.

        :param hold_display_name: Search term for filtering holds by display name.

        :returns: If successful, returns a dictionary containing 'repositoryObjects' with matching holds.
                Each hold includes its identifier, displayName, and creator properties.
                If no matches are found, returns an empty result set.
                If an error occurs, returns a ToolError instance with error details.
        """
        method_name = "list_holds_by_name_tool"
        logger.info(f"Enter MCP_LEGAL_HOLD {method_name}")
        try:
            query = """
            query getHoldsGivenAName ($object_store_name: String!, 
                $where_clause: String!, 
                ) {
                repositoryObjects(
                    repositoryIdentifier: $object_store_name,
                    from: "CmHold",
                    where: $where_clause
                ) {
                independentObjects {
                    className
                    properties (includes: ["Id", "DisplayName", "Creator"]) {
                        id
                        value
                    }
                }
                }
            }
            """

            formatted_value: str = f"'%{hold_display_name}%'"
            condition_string: str = (
                f"LOWER([DisplayName]) LIKE LOWER({formatted_value})"
            )

            var = {
                "object_store_name": graphql_client.object_store,
                "where_clause": condition_string,
            }

            response = await graphql_client.execute_async(query=query, variables=var)

            # return holds with the display_name
            return response["data"]
        except Exception as ex:
            error_traceback = traceback.format_exc(limit=TRACEBACK_LIMIT)
            logger.error(
                f"{method_name} failed: {ex.__class__.__name__} - {str(ex)}\n{error_traceback}"
            )

            return ToolError(
                message=f"{method_name} failed: got err {ex}. Trace available in server logs.",
            )
