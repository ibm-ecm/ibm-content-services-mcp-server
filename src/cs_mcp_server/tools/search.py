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
from typing import Any, List, Union, Optional
from mcp.server.fastmcp import FastMCP
from cs_mcp_server.cache.metadata import MetadataCache
from cs_mcp_server.cache.metadata_loader import (
    get_class_metadata_tool,
)
from cs_mcp_server.utils.common import (
    SearchParameters,
    ToolError,
    CachePropertyDescription,
)
from cs_mcp_server.client.graphql_client import GraphQLClient
from cs_mcp_server.utils.model.core import DocumentMatch, DocumentFilingMatch
from cs_mcp_server.utils.scoring import tokenize, word_similarity
from cs_mcp_server.utils.constants import (
    DEFAULT_DOCUMENT_CLASS,
    EXACT_SYMBOLIC_NAME_MATCH_SCORE,
    SYMBOLIC_NAME_SUBSTRING_SCORE,
    HIGH_SIMILARITY_THRESHOLD,
    MEDIUM_SIMILARITY_THRESHOLD,
    HIGH_SIMILARITY_MULTIPLIER,
    MEDIUM_SIMILARITY_MULTIPLIER,
    KEYWORD_COVERAGE_BONUS,
    MAX_SEARCH_RESULTS,
    VERSION_STATUS_RELEASED,
    VERSION_STATUS_IN_PROCESS,
    VERSION_STATUS_RESERVATION,
    INITIAL_MAJOR_VERSION,
    INITIAL_MINOR_VERSION,
    DATA_TYPE_STRING,
    DATA_TYPE_INTEGER,
    DATA_TYPE_LONG,
    DATA_TYPE_FLOAT,
    DATA_TYPE_DOUBLE,
    DATA_TYPE_BOOLEAN,
    DATA_TYPE_DATETIME,
    DATA_TYPE_DATE,
    DATA_TYPE_TIME,
    DATA_TYPE_OBJECT,
    CARDINALITY_LIST,
    SQL_LIKE_OPERATOR,
    OPERATOR_CONTAINS,
    OPERATOR_STARTS,
    OPERATOR_ENDS,
)

# Logger for this module
logger: Logger = logging.getLogger(__name__)


def format_value_by_type(value, data_type):
    """
    Format a value according to its data type.

    :param value: The value to format
    :param data_type: The data type of the value
    :return: The formatted value
    """
    # Return value directly for numeric, boolean, and date/time types
    if data_type in [
        DATA_TYPE_INTEGER,
        DATA_TYPE_LONG,
        DATA_TYPE_FLOAT,
        DATA_TYPE_DOUBLE,
        DATA_TYPE_BOOLEAN,
        DATA_TYPE_DATETIME,
        DATA_TYPE_DATE,
        DATA_TYPE_TIME,
    ]:
        return value
    # Default to string (quoted) for all other types
    return f"'{value}'"


def score_name(name: str, keywords: list[str]) -> float:
    """
    Common advanced scoring method that uses tokenization and fuzzy matching to find the best name based on keywords.
    """
    match_score = 0
    # Tokenize names
    name_tokens = tokenize(name)

    # Combine all tokens for full-text search
    all_tokens = name_tokens

    # Process each keyword
    for keyword in keywords:
        keyword = keyword.lower()
        keyword_tokens = tokenize(keyword)

        # 1. Check for exact matches (highest priority)
        if keyword == name:
            match_score += EXACT_SYMBOLIC_NAME_MATCH_SCORE
            continue

        # 2. Check for substring matches in names
        if keyword in name:
            match_score += SYMBOLIC_NAME_SUBSTRING_SCORE

        # 3. Check for token matches with fuzzy matching
        for k_token in keyword_tokens:
            # Check name tokens (highest priority)
            for token in name_tokens:
                similarity = word_similarity(k_token, token)
                if similarity > HIGH_SIMILARITY_THRESHOLD:
                    match_score += HIGH_SIMILARITY_MULTIPLIER * similarity
                elif similarity > MEDIUM_SIMILARITY_THRESHOLD:
                    match_score += MEDIUM_SIMILARITY_MULTIPLIER * similarity

    # Bonus for documents that match multiple keywords
    matched_keywords = set()
    for keyword in keywords:
        keyword = keyword.lower()
        for token in all_tokens:
            if word_similarity(keyword, token) > HIGH_SIMILARITY_THRESHOLD:
                matched_keywords.add(keyword)
                break

    # Add bonus based on percentage of keywords matched
    if len(keywords) > 1:
        keyword_coverage = len(matched_keywords) / len(keywords)
        match_score += KEYWORD_COVERAGE_BONUS * keyword_coverage

    return match_score


def score_folder(fold: dict, keywords: list[str]) -> float:
    """
    Advanced scoring method that uses tokenization and fuzzy matching to find the best document match.

    :param fold: The folder to score. A dictionary returned from the graphql search.
    :param keywords: The keywords to match against
    :return: A score indicating how well the folder matches the keywords
    """

    # Convert all text to lowercase for case-insensitive matching
    name = fold["name"].lower()

    match_score: float = score_name(name, keywords)

    return match_score


def score_document(doc: dict, keywords: List[str]) -> float:
    """
    Advanced scoring method that uses tokenization and fuzzy matching to find the best document match.

    This scoring algorithm works by:
    1. Tokenizing text (breaking CamelCase and snake_case into individual words)
    2. Performing fuzzy matching between keywords and tokens
    3. Giving bonuses for exact matches and for matching multiple keywords

    :param doc: The document to score. A dictionary returned from the graphql search.
    :param keywords: The keywords to match against
    :return: A score indicating how well the document matches the keywords
    """
    # Convert all text to lowercase for case-insensitive matching
    name = doc["name"].lower()

    match_score: float = score_name(name, keywords)

    return match_score


def register_search_tools(
    mcp: FastMCP,
    graphql_client: GraphQLClient,
    metadata_cache: MetadataCache,
) -> None:
    @mcp.tool(
        name="get_searchable_property_descriptions",
    )
    def get_searchable_property_descriptions(
        class_symbolic_name: str,
    ) -> Union[List[CachePropertyDescription], ToolError]:
        """
        Retrieves only the searchable properties of a class.

        :param class_symbolic_name: The symbolic name of the class to retrieve searchable properties for

        :returns: A list of CachePropertyDescription objects for properties that are searchable
        """
        class_metadata = get_class_metadata_tool(
            graphql_client=graphql_client,
            class_symbolic_name=class_symbolic_name,
            metadata_cache=metadata_cache,
        )

        # If there was an error retrieving the class metadata, return it
        if isinstance(class_metadata, ToolError):
            return class_metadata

        # Filter the properties to include only searchable ones
        searchable_properties = [
            prop for prop in class_metadata.property_descriptions if prop.is_searchable
        ]

        # Return only the list of searchable property descriptions
        return searchable_properties

    @mcp.tool(
        name="repository_object_search",
    )
    async def get_repository_object_main(
        search_parameters: SearchParameters,
    ) -> dict | ToolError:
        """
        **PREREQUISITES IN ORDER**: To use this tool, you MUST call two other tools first in a specific sequence.
        1. determine_class tool to get the class_name for search_class.
        2. get_searchable_property_descriptions to get a list of valid property_name for search_properties

        Description:
        This tool will execute a request to search for a repository object(s).

        :param search_parameters (SearchParameters): parameters for the searching including the object being searched for and any search conditions.

        :returns: A the repository object details, including:
            - repositoryObjects (dict): a dictionary containing independentObjects:
                - independentObjects (list): A list of independent objects, each containing:
                - properties (list): A list of properties, each containing:
                    - label (str): The name of the property.
                    - value (str): The value of the property.
        """
        # First, get the class metadata from the cache
        class_data = get_class_metadata_tool(
            graphql_client, search_parameters.search_class, metadata_cache
        )

        # Check if we got an error instead of class data
        if isinstance(class_data, ToolError):
            return class_data

        # Extract property information from the class data
        return_properties = []
        property_types = {}

        for prop in class_data.property_descriptions:
            # Skip properties with LIST cardinality or OBJECT data type
            if (
                prop.cardinality == CARDINALITY_LIST
                or prop.data_type == DATA_TYPE_OBJECT
            ):
                continue

            property_name = prop.symbolic_name
            return_properties.append(property_name)
            property_types[property_name] = prop.data_type

        return_properties_string = ", ".join(
            [f'"{item}"' for item in return_properties]
        )
        return_properties_string = f"[{return_properties_string}]"

        # Process search conditions
        query_conditions = []
        for item in search_parameters.search_properties:
            try:
                prop_name = item.property_name
            except AttributeError:
                return {"ERROR": "search_properties missing 'property_name' key"}
            try:
                prop_value = item.property_value.replace("*", "")
            except AttributeError:
                return {"ERROR": "search_properties missing 'property_value' key"}
            try:
                operator = item.operator.value
            except AttributeError:
                return {"ERROR": "search_properties missing 'operator' key"}

            if not all([prop_name, prop_value, operator]):
                print(f"Skipping invalid filter item: {item}")
                continue

            # Get the data type of the property
            data_type = property_types.get(
                prop_name, DATA_TYPE_STRING
            )  # Default to STRING if not found

            # Format the value according to its data type
            formatted_value = format_value_by_type(prop_value, data_type)

            # Get the appropriate SQL operator

            # Handle string operations
            if data_type == DATA_TYPE_STRING:
                if operator.upper() == OPERATOR_CONTAINS:
                    operator = SQL_LIKE_OPERATOR
                    formatted_value = f"'%{prop_value}%'"
                elif operator.upper() == OPERATOR_STARTS:
                    operator = SQL_LIKE_OPERATOR
                    formatted_value = f"'{prop_value}%'"
                elif operator.upper() == OPERATOR_ENDS:
                    operator = SQL_LIKE_OPERATOR
                    formatted_value = f"'%{prop_value}'"

            condition_string = f"{prop_name} {operator} {formatted_value}"
            query_conditions.append(condition_string)

        search_properties_string = " AND ".join(query_conditions)

        query = """
        query repositoryObjectsSearch($object_store_name: String!,
            $class_name: String!, $where_statement: String!, $return_props: [String!]){
            repositoryObjects(
            repositoryIdentifier: $object_store_name,
            from: $class_name,
            where: $where_statement
            ) {
            independentObjects {
                properties (includes: $return_props){
                label
                value
                }
            }
            }
        }
        """
        var = {
            "object_store_name": graphql_client.object_store,
            "where_statement": search_properties_string,
            "class_name": search_parameters.search_class,
            "return_props": return_properties,
        }

        try:
            response = await graphql_client.execute_async(query=query, variables=var)
            return response  # Return response only if no exception occurs
        except Exception as e:
            return ToolError(
                message=f"Error executing search: {str(e)}",
                suggestions=[
                    "Check that all property names are valid for the class",
                    "Ensure property values match the expected data types",
                    "Verify that the operators are appropriate for the property data types",
                ],
            )

    @mcp.tool(
        name="lookup_documents_by_name",
    )
    async def lookup_documents_by_name(
        keywords: List[str],
        class_symbolic_name: Optional[str] = None,
    ) -> Union[List[DocumentMatch], ToolError]:
        """

        :param keywords: Up to 3 words from the user's message that might contain the document's name.
                         Avoid using very common words such as "and", "or", "the", etc.
        :param class_symbolic_name: If specified, a specific document class to look in for matching documents.
                                    The root Document class is used by default. Specify a class only if the user indicates
                                    that the documents should belong to a specific class. Use the determine_class tool to lookup
                                    the class symbolic name based on the user's message.

        :returns: A list of matching documents, or a ToolError if no matches are found or there is some other problem.
                 Each match is a DocumentMatch object with information about the document including its name and a confidence score.

        Description:
        This tool will execute a search to lookup documents by name. A list of the most likely documents
        matching the keywords is returned. Use this list to select the appropriate document based on the user's message.
        """
        method_name = "lookup_documents_by_name"

        if not class_symbolic_name:
            class_symbolic_name = DEFAULT_DOCUMENT_CLASS

        class_data = get_class_metadata_tool(
            graphql_client,
            class_symbolic_name=class_symbolic_name,
            metadata_cache=metadata_cache,
        )
        # Check if we got an error instead of class data
        if isinstance(class_data, ToolError):
            return class_data

        logger.debug(
            msg=f"class_data.name_property_symbolic_name = {class_data.name_property_symbolic_name}"
        )
        if class_data.name_property_symbolic_name is None:
            return ToolError(
                message=f"Class {class_symbolic_name} does not have a name property",
            )

        keyword_conditions: list[str] = []
        for keyword in keywords:
            # query_conditions.append(
            #    f"LOWER({class_data.name_property_symbolic_name}) LIKE %{keyword.lower()}%"
            # )
            keyword_conditions.append(
                "LOWER("
                + class_data.name_property_symbolic_name
                + ") LIKE '%"
                + keyword.lower()
                + "%'"
            )

        keyword_conditions_string: str = " OR ".join(keyword_conditions)
        logger.debug("keyword_conditions_string: str = " + keyword_conditions_string)
        # Include condition to search only against commonly retrieved documents -- released if any; in-process version if any; initial reservation
        where_statement: str = (
            f"(VersionStatus = {VERSION_STATUS_RELEASED} OR (VersionStatus = {VERSION_STATUS_IN_PROCESS} AND MajorVersionNumber = {INITIAL_MAJOR_VERSION}) OR (VersionStatus = {VERSION_STATUS_RESERVATION} AND MajorVersionNumber = {INITIAL_MAJOR_VERSION} AND MinorVersionNumber = {INITIAL_MINOR_VERSION})) AND ("
            + keyword_conditions_string
            + ")"
        )
        logger.debug("where_statement: str = " + where_statement)
        query_text = """
        query documentsByNameSearch(
        $object_store_name: String!,
        $class_name: String!, $where_statement: String!) {
            documents(
            repositoryIdentifier: $object_store_name,
            from: $class_name,
            where: $where_statement
            ) {
            documents {
                className
                id
                name
                majorVersionNumber
                minorVersionNumber
                versionStatus
            }
            }
        }"""
        var = {
            "object_store_name": graphql_client.object_store,
            "where_statement": where_statement,
            "class_name": class_symbolic_name,
        }

        docs: list[dict]
        try:
            response = await graphql_client.execute_async(
                query=query_text, variables=var
            )
            if "errors" in response:
                logger.error("GraphQL error: %s", response["errors"])
                return ToolError(message=f"{method_name} failed: {response['errors']}")
            docs = response["data"]["documents"]["documents"]
        except Exception as e:
            return ToolError(
                message=f"Error executing search: {str(e)}",
            )
        logger.debug(f"Search for documents returned {len(docs)} documents")

        matches: list[Any] = []

        for doc in docs:
            match_score: float = score_document(doc, keywords)
            logger.debug(
                msg=f"document {doc['name']} matched with score of {match_score}"
            )

            if match_score > 0:
                matches.append((doc, match_score))

        # Sort matches by score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        # if we found matches, return up to the maximum matches
        max_results = MAX_SEARCH_RESULTS
        if matches:
            doc_matches: list[DocumentMatch] = []
            # Convert all available matches (up to max) to DocumentMatch objects
            for doc, score in matches[:max_results]:
                doc_name = doc["name"]
                logger.debug(
                    f"Document {doc_name} selected with matched score of {score}"
                )
                match: DocumentMatch = DocumentMatch(
                    id=doc["id"],
                    name=doc["name"],
                    class_name=doc["className"],
                    score=score,
                )
                doc_matches.append(match)
            return doc_matches

        return ToolError(
            message=f"No document matching keywords {keywords} found in the class '{class_symbolic_name}'",
            suggestions=[
                "Try using different keywords",
                "Check if the keywords are spelled correctly",
                "Ask the user for the specific document they want to use",
            ],
        )

    @mcp.tool(name="lookup_documents_by_path")
    async def lookup_documents_by_path(
        keywords_at_path_levels: List[List[str]],
        class_symbolic_name: Optional[str] = None,
    ) -> Union[List[DocumentFilingMatch], ToolError]:
        """
        **PREREQUISITE**: To use this tool, you MUST call the determine_class tool first to get the class_symbolic_name.
                          If the user does not specify a specific clas then call determine_class with the root Document class.

        :param keywords_at_path_levels: A list of lists of keywords to search for at each path level.
                                        The first dimension list is the number of path
                                        levels entered by the user. For each path level a sub list contains up to 3 words
                                        from the user's message for that level that might contain either the intermediate folder
                                        name or the actual document's containment name.
                                        Avoid using very common words such as "and", "or", "the", etc. for these keywords.
                                        Note that the matching of documents by path is based on the containment names of the documents
                                        filed in the folder, not the name of the documents themselves.
                                        The containment names of documents are usually the same or similar to the documents but
                                        they can be different in some scenarios.
        :param class_symbolic_name: If specified, a specific document class to look in for matching documents.
                                    The root Document class is used by default. Specify a class only if the user indicates
                                    that the documents should belong to a specific class.

        :returns: A list of matching document filings, or a ToolError if no matches are found or if there is some other problem.
                   Each match is a DocumentMatch object with information about the document filing including its name.

        Description:
        This tool will execute a search to lookup documents based on where they are filed in a folder hierarchy.
        One indication that a lookup by path is appropriate rather than a more basic lookup by name is if the user has used a
        path separator character ('/') to describe the document.
        A list of the most likely documents matching the keywords is returned. Use this list to select the appropriate document based on the user's message.
        """
        method_name = "lookup_documents_by_path"

        if not class_symbolic_name:
            class_symbolic_name = DEFAULT_DOCUMENT_CLASS

        class_data = get_class_metadata_tool(
            graphql_client,
            class_symbolic_name=class_symbolic_name,
            metadata_cache=metadata_cache,
        )

        # Check if we got an error instead of class data
        if isinstance(class_data, ToolError):
            return class_data

        logger.debug(
            msg=f"class_data.name_property_symbolic_name = {class_data.name_property_symbolic_name}"
        )
        if class_data.name_property_symbolic_name is None:
            return ToolError(
                message=f"Class {class_symbolic_name} does not have a name property",
            )

        # Collect folders from the intermediate levels we match. The dict is keyed
        # by the folder id. Each tuple contains the folder json and scoring for that folder.
        all_matched_intermediate_folders: dict[str, tuple[dict[str, Any], float]] = {}

        intermediate_query_text = """
        query intermediateFoldersByNameSearch(
        $object_store_name: String!, 
        $where_statement: String!) {
        folders(
          repositoryIdentifier: $object_store_name
          where: $where_statement
        ) {
          folders {
            id
            name
            pathName
          }
        }
        }"""

        for level_idx, intermediate_keywords in enumerate(keywords_at_path_levels[:-1]):
            logger.debug(
                f"Looking for intermediate folders using keywords at path level {level_idx}"
            )
            intermediate_keyword_conditions: list[str] = []
            for keyword in intermediate_keywords:
                intermediate_keyword_conditions.append(
                    "LOWER(FolderName) LIKE '%" + keyword.lower() + "%'"
                )
            intermediate_keyword_conditions_string: str = " OR ".join(
                intermediate_keyword_conditions
            )
            logger.debug(
                "intermediate_keyword_conditions_string: str = "
                + intermediate_keyword_conditions_string
            )
            # No other conditions in the overall where statement right now
            intermediate_where_statement: str = intermediate_keyword_conditions_string
            intermediate_var: dict[str, str] = {
                "object_store_name": graphql_client.object_store,
                "where_statement": intermediate_where_statement,
            }

            intermediate_folds: list[dict]
            try:
                interresponse: dict[str, Any] = await graphql_client.execute_async(
                    query=intermediate_query_text, variables=intermediate_var
                )
                if "errors" in interresponse:
                    logger.error("GraphQL error: %s", interresponse["errors"])
                    return ToolError(
                        message=f"{method_name} failed: {interresponse['errors']}"
                    )
                intermediate_folds = interresponse["data"]["folders"]["folders"]
            except Exception as e:
                return ToolError(
                    message=f"Error executing search: {str(e)}",
                )
            logger.debug(
                f"Search for intermediate folders returned {len(intermediate_folds)} folders"
            )

            intermediate_matches: list[Any] = []
            for interfold in intermediate_folds:
                interfold_path = interfold["pathName"]

                # Skip if we have already come across this at a previous level.
                if interfold["id"] in all_matched_intermediate_folders:
                    logger.debug(
                        f"Previously encountered intermediate folder {interfold_path}"
                    )
                    continue

                interf_match_score: float = score_folder(
                    interfold, intermediate_keywords
                )
                logger.debug(
                    f"Intermediate folder {interfold_path} match score is {interf_match_score}"
                )
                if interf_match_score <= 0:
                    continue

                if level_idx > 0:
                    logger.debug(
                        f"Adjusting score based on matching levels at level {level_idx}"
                    )
                    # adjust the score based on if the path of this folder comes after any
                    # previously matched intermediate folders.
                    inter_weight_each_level: float = 1 / (level_idx + 1)
                    interf_match_score *= inter_weight_each_level
                    for (
                        matched_intermediate,
                        miscore,
                    ) in all_matched_intermediate_folders.values():
                        if interfold_path.startswith(matched_intermediate["pathName"]):
                            logger.debug(
                                f"Matched previous level folder {interfold_path} and its score of {miscore}"
                            )
                            interf_match_score += miscore * inter_weight_each_level

                logger.debug(
                    f"Intermediate folder {interfold_path} match score after adjustment is {interf_match_score}"
                )
                intermediate_matches.append((interfold, interf_match_score))

            for interm_fold, match_score in intermediate_matches:
                all_matched_intermediate_folders[interm_fold["id"]] = (
                    interm_fold,
                    match_score,
                )

        document_filings_query_text = """
        query documentsByPathSearch(
          $object_store_name: String!,
          $from_condition: String!, 
          $where_statement: String!) 
        {
          repositoryObjects(repositoryIdentifier:$object_store_name,
          	from: $from_condition,
            where: $where_statement
          )
          {
            independentObjects {
              className
              ... on ReferentialContainmentRelationship {
                id
                containmentName
                tail {
                  className
                  id
                  name
                  pathName
                }
                head {
                  className
                  id
                  name
                  ... on Document {
                    versionStatus
                    minorVersionNumber
                    majorVersionNumber
                  }
                }
              }
            }
          }
        } """

        filings_from_condition: str = (
            "ReferentialContainmentRelationship r INNER JOIN "
            + class_symbolic_name
            + " d ON r.Head = d.This"
        )
        logger.debug("filings_from_condition: %s", filings_from_condition)
        filings_keywords: list[str] = keywords_at_path_levels[-1]
        filings_keyword_conditions: list[str] = []
        for keyword in filings_keywords:
            filings_keyword_conditions.append(
                "LOWER(r.ContainmentName) LIKE '%" + keyword.lower() + "%'"
            )
        filings_keyword_conditions_string: str = " OR ".join(filings_keyword_conditions)
        # No other conditions in the overall where statement right now
        filings_where_statement: str = filings_keyword_conditions_string
        logger.debug("filings_where_statement: %s", filings_where_statement)
        filings_var: dict[str, str] = {
            "object_store_name": graphql_client.object_store,
            "from_condition": filings_from_condition,
            "where_statement": filings_where_statement,
        }

        filings: list[dict]
        try:
            response: dict[str, Any] = await graphql_client.execute_async(
                query=document_filings_query_text, variables=filings_var
            )
            if "errors" in response:
                errors = response["errors"]
                logger.error("GraphQL error: %s", errors)
                return ToolError(message=f"{method_name} failed: {errors}")
            filings = response["data"]["repositoryObjects"]["independentObjects"]
        except Exception as e:
            return ToolError(
                message=f"Error executing search: {str(e)}",
            )
        logger.debug(f"Search for document filings returned {len(filings)} filings")

        filing_matches: list[Any] = []
        for filing in filings:
            match_score: float = score_name(
                filing["containmentName"].lower(), filings_keywords
            )
            logger.debug(f"Filing {filing['containmentName']} has score {match_score}")
            if match_score <= 0:
                continue
            filing_path: str = (
                filing["tail"]["pathName"] + "/" + filing["containmentName"]
            )

            if len(keywords_at_path_levels) > 1:
                logger.debug(
                    f"Adjusting score based on matching {len(keywords_at_path_levels)} number of levels"
                )
                weight_each_level: float = 1.0 / len(keywords_at_path_levels)
                match_score *= weight_each_level
                for (
                    matched_intermediate,
                    miscore,
                ) in all_matched_intermediate_folders.values():
                    if filing_path.startswith(matched_intermediate["pathName"]):
                        matched_path = matched_intermediate["pathName"]
                        logger.debug(
                            f"Matched previous level folder {matched_path} and its score of {miscore}"
                        )
                        match_score += miscore * weight_each_level
            logger.debug(
                f"Filing {filing_path} match score after adjustment is {match_score}"
            )
            filing_matches.append((filing, filing_path, match_score))

        # Sort matches by score (highest first)
        filing_matches.sort(key=lambda x: x[2], reverse=True)

        # if we found matches, return up to the maximum matches
        max_results = MAX_SEARCH_RESULTS
        if filing_matches:
            doc_filing_matches: list[DocumentFilingMatch] = []
            # Convert all available matches (up to max) to DocumentFilingMatch objects
            for doc_filing, filing_path, score in filing_matches[:max_results]:
                logger.debug(
                    msg=f"Document filing {filing_path} selected with matched score of {score}"
                )
                match: DocumentFilingMatch = DocumentFilingMatch(
                    containment_id=doc_filing["id"],
                    containment_name=doc_filing["containmentName"],
                    containment_path=filing_path,
                    document_class_name=doc_filing["head"]["className"],
                    document_id=doc_filing["head"]["id"],
                    document_name=doc_filing["head"]["name"],
                    folder_id=doc_filing["tail"]["id"],
                    folder_name=doc_filing["tail"]["name"],
                    folder_path=doc_filing["tail"]["pathName"],
                    score=score,
                )
                doc_filing_matches.append(match)
            return doc_filing_matches

        return ToolError(
            message=f"No document filings matching the keywords were found in the class '{class_symbolic_name}'",
            suggestions=[
                "Try using different keywords",
                "Check if the keywords are spelled correctly",
                "Ask the user for the specific document they want to use",
            ],
        )
