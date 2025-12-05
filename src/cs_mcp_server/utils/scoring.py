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
Scoring utilities for matching objects based on keywords.

This module provides common scoring functionality used across different parts
of the application for matching objects (classes, documents, etc.) against keywords.
"""

from .constants import (
    SUBSTRING_SIMILARITY_MULTIPLIER,
    PREFIX_SIMILARITY_MULTIPLIER,
)


# Helper function for word tokenization
def tokenize(text):
    """Split text into words, handling CamelCase and snake_case"""
    # Handle CamelCase by inserting spaces before capital letters
    text = "".join([" " + c if c.isupper() else c for c in text]).strip()
    # Handle snake_case by replacing underscores with spaces
    text = text.replace("_", " ")
    # Split by spaces and filter out empty strings
    return [word.lower() for word in text.split() if word]


# Helper function for calculating word similarity (simple fuzzy matching)
def word_similarity(word1, word2):
    """Calculate similarity between two words (0-1)"""
    # If words are identical, return 1.0
    if word1 == word2:
        return 1.0

    # If one word is a substring of the other, return high similarity
    if word1 in word2:
        return SUBSTRING_SIMILARITY_MULTIPLIER * (len(word1) / len(word2))
    if word2 in word1:
        return SUBSTRING_SIMILARITY_MULTIPLIER * (len(word2) / len(word1))

    # Count matching characters at the beginning
    prefix_match = 0
    for i in range(min(len(word1), len(word2))):
        if word1[i] == word2[i]:
            prefix_match += 1
        else:
            break

    # Return similarity based on prefix match length
    if prefix_match > 0:
        return PREFIX_SIMILARITY_MULTIPLIER * (
            prefix_match / max(len(word1), len(word2))
        )

    return 0.0
