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

from functools import lru_cache
from typing import List, Union

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from cs_mcp_server.cache.metadata import MetadataCache
from cs_mcp_server.cache.metadata_loader import (
    get_class_metadata_tool,
    get_root_class_description_tool,
)
from cs_mcp_server.client.graphql_client import GraphQLClient
from cs_mcp_server.utils.common import (
    CacheClassDescriptionData,
    CachePropertyDescription,
    ClassDescriptionData,
    ToolError,
)
from cs_mcp_server.utils.scoring import tokenize, word_similarity
from cs_mcp_server.utils.constants import (
    EXACT_SYMBOLIC_NAME_MATCH_SCORE,
    EXACT_DISPLAY_NAME_MATCH_SCORE,
    SYMBOLIC_NAME_SUBSTRING_SCORE,
    DISPLAY_NAME_SUBSTRING_SCORE,
    DESCRIPTIVE_TEXT_SUBSTRING_SCORE,
    HIGH_SIMILARITY_THRESHOLD,
    MEDIUM_SIMILARITY_THRESHOLD,
    DESCRIPTION_HIGH_SIMILARITY_THRESHOLD,
    HIGH_SIMILARITY_MULTIPLIER,
    MEDIUM_SIMILARITY_MULTIPLIER,
    DISPLAY_HIGH_SIMILARITY_MULTIPLIER,
    DISPLAY_MEDIUM_SIMILARITY_MULTIPLIER,
    DESCRIPTION_SIMILARITY_MULTIPLIER,
    PROPERTY_SYMBOLIC_NAME_SCORE,
    PROPERTY_DISPLAY_NAME_SCORE,
    KEYWORD_COVERAGE_BONUS,
    SCORE_NORMALIZATION_EXPONENT,
    MAX_SCORE_CAP,
    SUBSTRING_SIMILARITY_MULTIPLIER,
    PREFIX_SIMILARITY_MULTIPLIER,
    LRU_CACHE_SIZE,
    MAX_CLASS_MATCHES,
)


class ClassMatch(BaseModel):
    """
    Represents a matched class with its score and additional information.

    This class contains information about a class that matched a search query,
    including its class description data and match score.
    The score indicates how well the class matched the search criteria,
    with higher values representing better matches.
    """

    class_description_data: ClassDescriptionData = Field(
        description="The complete class description data object containing class_name, display_name, and descriptive_text"
    )
    score: float = Field(
        description="The match score, higher values indicate better matches"
    )


def scoring(class_data: CacheClassDescriptionData, keywords: List[str]) -> float:
    """
    Advanced scoring method that uses tokenization and fuzzy matching to find the best class match.

    This scoring algorithm works by:
    1. Tokenizing text (breaking CamelCase and snake_case into individual words)
    2. Performing fuzzy matching between keywords and tokens
    3. Applying different weights based on where matches are found (symbolic name, display name, description)
    4. Giving bonuses for exact matches and for matching multiple keywords

    :param class_data: The class data to score
    :param keywords: The keywords to match against
    :return: A score indicating how well the class matches the keywords
    """
    match_score = 0

    # Convert all text to lowercase for case-insensitive matching
    symbolic_name = class_data.symbolic_name.lower()
    display_name = class_data.display_name.lower()
    descriptive_text = class_data.descriptive_text.lower()

    # Tokenize class names and description
    symbolic_tokens = tokenize(symbolic_name)
    display_tokens = tokenize(display_name)
    descriptive_tokens = tokenize(descriptive_text)

    # Combine all tokens for full-text search
    all_tokens = symbolic_tokens + display_tokens + descriptive_tokens

    # Process each keyword
    for keyword in keywords:
        keyword = keyword.lower()
        keyword_tokens = tokenize(keyword)

        # 1. Check for exact matches (highest priority)
        if keyword == symbolic_name:
            match_score += EXACT_SYMBOLIC_NAME_MATCH_SCORE
            continue

        if keyword == display_name:
            match_score += EXACT_DISPLAY_NAME_MATCH_SCORE
            continue

        # 2. Check for substring matches in names
        if keyword in symbolic_name:
            match_score += SYMBOLIC_NAME_SUBSTRING_SCORE

        if keyword in display_name:
            match_score += DISPLAY_NAME_SUBSTRING_SCORE

        # 3. Check for token matches with fuzzy matching
        for k_token in keyword_tokens:
            # Check symbolic name tokens (highest priority)
            for token in symbolic_tokens:
                similarity = word_similarity(k_token, token)
                if similarity > HIGH_SIMILARITY_THRESHOLD:
                    match_score += HIGH_SIMILARITY_MULTIPLIER * similarity
                elif similarity > MEDIUM_SIMILARITY_THRESHOLD:
                    match_score += MEDIUM_SIMILARITY_MULTIPLIER * similarity

            # Check display name tokens (medium priority)
            for token in display_tokens:
                similarity = word_similarity(k_token, token)
                if similarity > HIGH_SIMILARITY_THRESHOLD:
                    match_score += DISPLAY_HIGH_SIMILARITY_MULTIPLIER * similarity
                elif similarity > MEDIUM_SIMILARITY_THRESHOLD:
                    match_score += DISPLAY_MEDIUM_SIMILARITY_MULTIPLIER * similarity

            # Check descriptive text (lowest priority)
            for token in descriptive_tokens:
                similarity = word_similarity(k_token, token)
                if similarity > DESCRIPTION_HIGH_SIMILARITY_THRESHOLD:
                    match_score += DESCRIPTION_SIMILARITY_MULTIPLIER * similarity

        # 4. Check for substring in descriptive text (lowest priority)
        if keyword in descriptive_text:
            match_score += DESCRIPTIVE_TEXT_SUBSTRING_SCORE

    # Bonus for classes that match multiple keywords
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


@lru_cache(maxsize=LRU_CACHE_SIZE)
def cached_tokenize(text):
    """
    Cached version of tokenize function that breaks text into individual words.

    This function splits text into tokens (words) by:
    1. Breaking CamelCase (e.g., "DocumentTitle" → ["Document", "Title"])
    2. Breaking snake_case (e.g., "document_title" → ["document", "title"])
    3. Converting all tokens to lowercase for case-insensitive matching

    The function uses LRU caching to improve performance by avoiding
    repeated tokenization of the same text.

    Examples:
        - "DocumentTitle" → ["document", "title"]
        - "document_title" → ["document", "title"]
        - "Document Title" → ["document", "title"]
        - "documentTitle" → ["document", "title"]

    Args:
        text: The text to tokenize

    Returns:
        List of lowercase tokens extracted from the text
    """
    # Handle empty input
    if not text:
        return []

    # Handle CamelCase by inserting spaces before capital letters
    # Example: "DocumentTitle" → " Document Title"
    text = "".join([" " + c if c.isupper() else c for c in text]).strip()

    # Handle snake_case by replacing underscores with spaces
    # Example: "document_title" → "document title"
    text = text.replace("_", " ")

    # Split by spaces and filter out empty strings
    # Convert all tokens to lowercase for case-insensitive matching
    return [word.lower() for word in text.split() if word]


def improved_word_similarity(word1, word2):
    """
    Calculate similarity between two words with an improved algorithm.

    This function determines how similar two words are on a scale from 0.0 to 1.0,
    where 1.0 means identical and 0.0 means completely different. The algorithm
    considers several factors:

    1. Exact matches: Returns 1.0 for identical words
       Example: "document" and "document" → 1.0

    2. Substring containment: High similarity when one word contains the other
       Example: "doc" and "document" → 0.9 * (3/8) = 0.34
       Example: "documentation" and "document" → 0.9 * (8/13) = 0.55

    3. Prefix matching: Medium similarity for words with matching prefixes
       Example: "doc" and "dog" → 0.7 * (2/3) = 0.47
       Example: "contract" and "contrary" → 0.7 * (5/8) = 0.44

    4. Non-matching: Returns 0.0 for words with no similarity
       Example: "document" and "file" → 0.0

    Args:
        word1: First word to compare
        word2: Second word to compare

    Returns:
        Float between 0.0 and 1.0 representing similarity
    """
    # Convert to lowercase for case-insensitive comparison
    word1, word2 = word1.lower(), word2.lower()

    # CASE 1: EXACT MATCH
    # If words are identical, return perfect similarity
    if word1 == word2:
        return 1.0

    # CASE 2: SUBSTRING CONTAINMENT
    # If one word is contained within the other, return high similarity
    # scaled by the length ratio (shorter/longer)
    if word1 in word2:
        return SUBSTRING_SIMILARITY_MULTIPLIER * (len(word1) / len(word2))
    if word2 in word1:
        return SUBSTRING_SIMILARITY_MULTIPLIER * (len(word2) / len(word1))

    # CASE 3: PREFIX MATCHING
    # Count matching characters at the beginning (prefix match)
    prefix_match = 0
    for i in range(min(len(word1), len(word2))):
        if word1[i] == word2[i]:
            prefix_match += 1
        else:
            break

    # Return similarity based on prefix match length if there is any match
    if prefix_match > 0:
        return PREFIX_SIMILARITY_MULTIPLIER * (
            prefix_match / max(len(word1), len(word2))
        )

    # CASE 4: NO SIMILARITY
    # No match found, return zero similarity
    return 0.0


def optimized_scoring(
    class_data: CacheClassDescriptionData, keywords: List[str]
) -> float:
    """
    An optimized version of the scoring function that balances accuracy and performance.

    This algorithm performs class matching through the following steps:
    1. Tokenization: Breaks text into individual words, handling CamelCase and snake_case
       - Example: "DocumentTitle" becomes ["document", "title"]
       - Example: "invoice_number" becomes ["invoice", "number"]

    2. Text Matching: Performs exact, substring, and fuzzy matching with different weights
       - Exact matches (highest priority, score +15-20):
         Example: "document" exactly matches "Document" class name
       - Substring matches (high priority, score +8-10):
         Example: "doc" is contained in "Document"
       - Token fuzzy matches (medium priority, score varies by similarity):
         Example: "docs" partially matches "document" with similarity score

    3. Property Matching: Considers class properties in the scoring calculation
       - Property symbolic name matches (score +2):
         Example: "title" matches "DocumentTitle" property
       - Property display name matches (score +1.5):
         Example: "author" matches "Author" display name

    4. Multi-keyword Handling: Gives bonuses for matching multiple keywords
       - Calculates percentage of keywords matched
       - Adds bonus score based on coverage (up to +5)
       - Example: For ["contract", "legal"], both matching gives higher score

    5. Score Normalization: Adjusts scores based on keyword count for consistency
       - Divides by square root of keyword count to prevent inflation
       - Caps maximum score at 100.0
       - Example: Normalizes scores so 3-keyword queries don't always outscore 1-keyword

    Word similarity calculation details:
    - Exact word matches: 1.0 similarity
    - Substring containment: 0.9 * (length_ratio) similarity
    - Prefix matching: 0.7 * (prefix_length / max_length) similarity
    - Non-matching words: 0.0 similarity

    :param class_data: The class data to score
    :param keywords: The keywords to match against
    :return: A score indicating how well the class matches the keywords
    """
    # Early return for empty keywords
    if not keywords:
        return 0.0

    match_score = 0.0

    # STEP 1: PREPARE TEXT FOR MATCHING
    # Convert all text to lowercase for case-insensitive matching
    symbolic_name = class_data.symbolic_name.lower()
    display_name = class_data.display_name.lower()
    descriptive_text = (
        class_data.descriptive_text.lower() if class_data.descriptive_text else ""
    )

    # Tokenize class names and description using cached function for performance
    # This breaks CamelCase and snake_case into individual words
    symbolic_tokens = cached_tokenize(
        symbolic_name
    )  # e.g., "DocumentTitle" -> ["document", "title"]
    display_tokens = cached_tokenize(
        display_name
    )  # e.g., "Document Title" -> ["document", "title"]
    descriptive_tokens = cached_tokenize(descriptive_text)

    # Combine all tokens for full-text search later
    all_tokens = symbolic_tokens + display_tokens + descriptive_tokens

    # STEP 2: PROCESS EACH KEYWORD FOR MATCHES
    for keyword in keywords:
        keyword = keyword.lower()  # Case-insensitive matching
        keyword_tokens = cached_tokenize(keyword)  # Break keyword into tokens

        # 2.1: Check for exact matches (highest priority)
        # If keyword exactly matches class name, give high score and skip other checks
        if keyword == symbolic_name:
            match_score += EXACT_SYMBOLIC_NAME_MATCH_SCORE
            continue  # Skip other checks for this keyword

        if keyword == display_name:
            match_score += EXACT_DISPLAY_NAME_MATCH_SCORE
            continue  # Skip other checks for this keyword

        # 2.2: Check for substring matches in names
        # If keyword is contained within class name, give high score
        if keyword in symbolic_name:
            match_score += SYMBOLIC_NAME_SUBSTRING_SCORE

        if keyword in display_name:
            match_score += DISPLAY_NAME_SUBSTRING_SCORE

        # 2.3: Check for token matches with fuzzy matching
        # Compare each token in keyword with each token in class names/description
        for k_token in keyword_tokens:
            # Check symbolic name tokens (highest priority)
            for token in symbolic_tokens:
                # Calculate similarity between tokens (0.0-1.0)
                similarity = improved_word_similarity(k_token, token)
                if similarity > HIGH_SIMILARITY_THRESHOLD:
                    match_score += HIGH_SIMILARITY_MULTIPLIER * similarity
                elif similarity > MEDIUM_SIMILARITY_THRESHOLD:
                    match_score += MEDIUM_SIMILARITY_MULTIPLIER * similarity

            # Check display name tokens (medium priority)
            for token in display_tokens:
                similarity = improved_word_similarity(k_token, token)
                if similarity > HIGH_SIMILARITY_THRESHOLD:
                    match_score += DISPLAY_HIGH_SIMILARITY_MULTIPLIER * similarity
                elif similarity > MEDIUM_SIMILARITY_THRESHOLD:
                    match_score += DISPLAY_MEDIUM_SIMILARITY_MULTIPLIER * similarity

            # Check descriptive text (lowest priority)
            # Higher threshold for description to reduce false positives
            for token in descriptive_tokens:
                similarity = improved_word_similarity(k_token, token)
                if similarity > DESCRIPTION_HIGH_SIMILARITY_THRESHOLD:
                    match_score += DESCRIPTION_SIMILARITY_MULTIPLIER * similarity

        # 2.4: Check for substring in descriptive text (lowest priority)
        if keyword in descriptive_text:
            match_score += DESCRIPTIVE_TEXT_SUBSTRING_SCORE

    # STEP 3: PROPERTY-BASED MATCHING
    # Consider class properties in scoring calculation
    if hasattr(class_data, "properties") and class_data.property_descriptions:
        for keyword in keywords:
            keyword = keyword.lower()
            for prop in class_data.property_descriptions:
                # Check if keyword matches property symbolic name
                if keyword in prop.symbolic_name.lower():
                    match_score += PROPERTY_SYMBOLIC_NAME_SCORE
                # Check if keyword matches property display name
                if keyword in prop.display_name.lower():
                    match_score += PROPERTY_DISPLAY_NAME_SCORE

    # STEP 4: MULTI-KEYWORD BONUS CALCULATION
    # Give bonus for classes that match multiple keywords
    matched_keywords = set()
    for keyword in keywords:
        keyword = keyword.lower()
        # Check if any token in the class has high similarity with this keyword
        for token in all_tokens:
            if improved_word_similarity(keyword, token) > HIGH_SIMILARITY_THRESHOLD:
                matched_keywords.add(keyword)
                break

    # Add bonus based on percentage of keywords matched
    # This rewards classes that match more of the user's query terms
    if len(keywords) > 1:
        keyword_coverage = len(matched_keywords) / len(keywords)
        match_score += KEYWORD_COVERAGE_BONUS * keyword_coverage

    # STEP 5: SCORE NORMALIZATION
    # Normalize score based on number of keywords to ensure fair comparison
    if len(keywords) > 0:
        # Adjust score based on keyword count to avoid bias towards more keywords
        # Using square root provides a balanced normalization
        match_score = match_score / (len(keywords) ** SCORE_NORMALIZATION_EXPONENT)

        # Cap the score at a reasonable maximum to prevent extreme values
        match_score = min(match_score, MAX_SCORE_CAP)

    return match_score


def register_class_tools(
    mcp: FastMCP,
    graphql_client: GraphQLClient,
    metadata_cache: MetadataCache,
) -> None:
    """
    Register common tools with the MCP server.

    Args:
        mcp: The FastMCP instance to register tools with
        graphql_client: The GraphQL client to use for queries
        metadata_cache: The metadata cache to use for class information
    """

    @mcp.tool(
        name="list_root_classes",
    )
    def list_root_classes_tool() -> List[str]:
        """
        List all available root class types in the repository.

        This tool should be called first to get a list of valid root class names
        before using the list_all_classes tool.

        :returns: A list of all available root class types (e.g., ["Document", "Folder", "Annotation", "CustomObject"])
        """
        return metadata_cache.get_root_class_keys()

    @mcp.tool(
        name="list_all_classes",
    )
    def list_all_classes_tool(
        root_class: str,
    ) -> Union[List[ClassDescriptionData], ToolError]:
        """
        List all available classes for a specific root class type.

        IMPORTANT: Only use this tool when the user explicitly asks to see a list of classes of a specific root class.
        If a user does not specify a root_class, you **MUST** request the root class from them.
        To get a list of all valid root class names that can be used with this tool, you can call the `list_root_classes_tool` tool.

        :param root_class: The root class to list all classes for (e.g., "Document", "Folder", "Annotation", "CustomObject")

        :returns: A list of all classes for the specified root class, or a ToolError if an error occurs
        """
        # Validate root_class parameter by checking the cache keys
        if root_class not in metadata_cache.get_root_class_keys():
            return ToolError(
                message=f"Invalid root class '{root_class}'. Root class must be one of: {metadata_cache.get_root_class_keys()}",
                suggestions=[
                    "Use list_root_classes tool first to get valid root class names",
                ],
            )

        # First, ensure the root class cache is populated
        root_class_result = get_root_class_description_tool(
            graphql_client=graphql_client,
            root_class_type=root_class,
            metadata_cache=metadata_cache,
        )

        # If there was an error populating the root class cache, return it
        if isinstance(root_class_result, ToolError):
            return root_class_result

        # Get all classes for the specified root class
        all_classes = metadata_cache.get_class_cache(root_class)

        if not all_classes:
            return ToolError(
                message=f"No classes found for root class '{root_class}'",
                suggestions=[
                    "Check if the metadata cache is properly populated",
                    "Try refreshing the class metadata",
                ],
            )

        # Convert all classes to ClassDescriptionData objects
        result = []
        for class_name, class_data in all_classes.items():
            # Skip if class_data is not a CacheClassDescriptionData object
            if not isinstance(class_data, CacheClassDescriptionData):
                continue

            # Use model_validate to convert CacheClassDescriptionData to ClassDescriptionData
            class_desc_data = ClassDescriptionData.model_validate(class_data)
            result.append(class_desc_data)

        # Sort results by symbolic name for consistency
        result.sort(key=lambda x: x.symbolic_name)

        return result

    @mcp.tool(
        name="determine_class",
    )
    def determine_class(
        root_class: str, keywords: List[str]
    ) -> Union[List[ClassMatch], ToolError]:
        """
        Find classes that match the given keywords by looking for substring matches in class names and descriptions.

        IMPORTANT:
        To get a list of all valid class names that can be used with this tool, you **MUST** first call the `list_root_classes_tool` tool.

        :param root_class: The root class to search within (eg. "Document", "Folder")
        :param keywords: Up to 3 words from the user's message that might contain the class's name

        :returns: A list of up to 3 matching classes with their scores, or a ToolError if no matches are found
                 Each match is a ClassMatch object with class_name and score fields
        """
        # Validate root_class parameter by checking the cache keys
        valid_root_classes = list_root_classes_tool()
        if root_class not in valid_root_classes:
            return ToolError(
                message=f"Invalid root class '{root_class}'. Root class must be one of: {valid_root_classes}",
                suggestions=[
                    "Use list_root_classes tool first to get valid root class names",
                ],
            )

        # First, ensure the root class cache is populated
        root_class_result = get_root_class_description_tool(
            graphql_client=graphql_client,
            root_class_type=root_class,
            metadata_cache=metadata_cache,
        )

        # If there was an error populating the root class cache, return it
        if isinstance(root_class_result, ToolError):
            return root_class_result

        # Get all classes for the specified root class
        all_classes = metadata_cache.get_class_cache(root_class)

        if not all_classes:
            return ToolError(
                message=f"No classes found for root class '{root_class}'",
                suggestions=[
                    "Check if the metadata cache is properly populated",
                    "Try refreshing the class metadata",
                ],
            )

        # Look for matches in class names and descriptions
        matches = []

        for class_name, class_data in all_classes.items():
            # Skip if class_data is not a ContentClassData object
            if not isinstance(class_data, CacheClassDescriptionData):
                continue

            # Use the scoring method
            match_score = scoring(class_data, keywords)

            # If we have any matches, add to our list
            if match_score > 0:
                # Store class name, display name, description, and score
                matches.append(
                    (
                        class_name,
                        class_data.display_name,
                        class_data.descriptive_text,
                        match_score,
                    )
                )

        # Sort matches by score (highest first)
        matches.sort(key=lambda x: x[3], reverse=True)

        # If we found matches, return up to MAX_CLASS_MATCHES top matches
        if matches:
            # Convert all available matches to ClassMatch objects
            result = []
            for class_name, display_name, descriptive_text, score in matches[
                :MAX_CLASS_MATCHES
            ]:
                # Get the class description data from the cache
                cache_class_data = all_classes[class_name]

                # Use model_validate to convert CacheClassDescriptionData to ClassDescriptionData
                class_desc_data = ClassDescriptionData.model_validate(cache_class_data)

                # Create ClassMatch object with the class_description_data field
                match = ClassMatch(class_description_data=class_desc_data, score=score)
                result.append(match)

            return result

        # If no matches were found, return an error with suggestions
        return ToolError(
            message=f"No class matching keywords {keywords} found in root class '{root_class}'",
            suggestions=[
                "Try using different keywords",
                "Check if the keywords are spelled correctly",
                "Ask the user for the specific class they want to use",
            ],
        )

    @mcp.tool(
        name="get_class_property_descriptions",
    )
    def get_class_property_descriptions(
        class_symbolic_name: str,
    ) -> Union[List[CachePropertyDescription], ToolError]:
        """
        Retrieves properties of a class.

        :param class_symbolic_name: The symbolic name of the class to retrieve properties for

        :returns: A list of CachePropertyDescription objects for each property
        """
        class_metadata = get_class_metadata_tool(
            graphql_client=graphql_client,
            class_symbolic_name=class_symbolic_name,
            metadata_cache=metadata_cache,
        )

        # If there was an error retrieving the class metadata, return it
        if isinstance(class_metadata, ToolError):
            return class_metadata
        else:
            return class_metadata.property_descriptions
