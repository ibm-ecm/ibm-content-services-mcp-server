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
MCP Server Main Module

This module serves as the main entry point for the Model-Context-Protocol (MCP) server
that integrates with a GraphQL client to provide various content management tools and services.
It handles server initialization, tool registration, and graceful shutdown procedures.
"""

# Standard library imports
import asyncio
import atexit
import logging
import os
from enum import Enum

# Third-party imports
from mcp.server.fastmcp import FastMCP

# Use absolute imports
from cs_mcp_server.cache import MetadataCache
from cs_mcp_server.client import GraphQLClient
from cs_mcp_server.tools.documents import register_document_tools
from cs_mcp_server.tools.classes import register_class_tools
from cs_mcp_server.tools.search import (
    register_search_tools,
)
from cs_mcp_server.tools.mcp_manage_hold import register_legalhold
from cs_mcp_server.tools.vector_search import register_vector_search_tool
from cs_mcp_server.tools.folders import register_folder_tools
from cs_mcp_server.tools.annotations import register_annotation_tools

# Configure logging with dynamic level from environment variable
log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)

logging.basicConfig(
    level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Log the configured level for debugging
logger.debug("Logging configured at %s level", log_level_name)

# Global MCP instance - will be initialized by entry point
mcp = None


class ServerType(str, Enum):
    """Enumeration of available MCP server types."""

    CORE = "core"
    VECTOR_SEARCH = "vector-search"
    LEGAL_HOLD = "legal-hold"
    FULL = "full"


def _initialize_mcp_server(server_name: str) -> FastMCP:
    """
    Initialize the global MCP server instance.

    This function should be called once at the start of each entry point
    before any tool registration occurs.

    Args:
        server_name: The name for the MCP server instance

    Returns:
        FastMCP: The initialized MCP server instance
    """
    global mcp
    if mcp is None:
        mcp = FastMCP(server_name)
        logger.info("Initialized MCP server: %s", server_name)
    return mcp


def parse_ssl_flag(value, default="true"):
    """
    Parse SSL flag which can be either a boolean or a path to a certificate.

    Args:
        value: The SSL flag value from environment variable
        default: Default value if not provided

    Returns:
        bool or str: True/False for boolean values, or the path string for certificates
    """
    if value is None:
        value = default

    # If it's a string representation of a boolean
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    # Otherwise it's a path to a certificate or other value
    return value


def initialize_graphql_client():
    """
    Initialize the GraphQL client for the MCP server.
    Supports both basic authentication and OAuth authentication methods.

    Returns:
        GraphQLClient: The initialized GraphQL client instance
    """
    # Get connection details from environment variables
    graphql_url = os.environ.get("SERVER_URL", "")
    username = os.environ.get("USERNAME", "")
    password = os.environ.get("PASSWORD", "")
    ssl_enabled = parse_ssl_flag(os.environ.get("SSL_ENABLED"), "true")
    token_ssl_enabled = parse_ssl_flag(os.environ.get("TOKEN_SSL_ENABLED"), "true")
    object_store = os.environ.get("OBJECT_STORE", "")
    token_refresh = int(
        os.environ.get("TOKEN_REFRESH", "1800")
    )  # 30 minutes in seconds

    # OAuth specific parameters
    token_url = os.environ.get("TOKEN_URL", "")
    grant_type = os.environ.get("GRANT_TYPE", "")
    scope = os.environ.get("SCOPE", "")
    client_id = os.environ.get("CLIENT_ID", "")
    client_secret = os.environ.get("CLIENT_SECRET", "")

    # ZenIAM specific parameters
    zeniam_zen_url = os.environ.get("ZENIAM_ZEN_URL", "")
    zeniam_iam_url = os.environ.get("ZENIAM_IAM_URL", "")
    zeniam_iam_ssl_enabled = parse_ssl_flag(
        os.environ.get("ZENIAM_IAM_SSL_ENABLED"), "true"
    )
    zeniam_iam_grant_type = os.environ.get("ZENIAM_IAM_GRANT_TYPE", "")
    zeniam_iam_scope = os.environ.get("ZENIAM_IAM_SCOPE", "")
    zeniam_iam_client_id = os.environ.get("ZENIAM_IAM_CLIENT_ID", "")
    zeniam_iam_cient_secret = os.environ.get("ZENIAM_IAM_CLIENT_SECRET", "")
    zeniam_iam_user_name = os.environ.get("ZENIAM_IAM_USER", "")
    zeniam_iam_user_password = os.environ.get("ZENIAM_IAM_PASSWORD", "")
    zeniam_zen_exchange_ssl = parse_ssl_flag(
        os.environ.get("ZENIAM_ZEN_SSL_ENABLED"), "true"
    )

    # Connection settings
    timeout = float(os.environ.get("REQUEST_TIMEOUT", "30.0"))
    pool_connections = int(os.environ.get("POOL_CONNECTIONS", "100"))
    pool_maxsize = int(os.environ.get("POOL_MAXSIZE", "100"))

    # Validate required parameters
    if not graphql_url:
        raise ValueError("SERVER_URL environment variable is required")
    if not username and not zeniam_zen_url:
        raise ValueError("USERNAME environment variable is required")
    if not password and not zeniam_zen_url:
        raise ValueError("PASSWORD environment variable is required")
    if not object_store:
        raise ValueError("OBJECT_STORE environment variable is required")

    # Create and return the GraphQL client
    # Pass all parameters to the constructor and let it handle them appropriately
    return GraphQLClient(
        url=graphql_url,
        username=username,
        password=password,
        ssl_enabled=ssl_enabled,
        object_store=object_store,
        token_url=token_url,
        token_ssl_enabled=token_ssl_enabled,
        grant_type=grant_type,
        scope=scope,
        client_id=client_id,
        client_secret=client_secret,
        timeout=timeout,
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
        token_refresh=token_refresh,
        ZenIAM_iam_url=zeniam_iam_url,
        ZenIAM_iam_ssl_enabled=zeniam_iam_ssl_enabled,
        ZenIAM_iam_grant_type=zeniam_iam_grant_type,
        ZenIAM_iam_scope=zeniam_iam_scope,
        ZenIAM_iam_client_id=zeniam_iam_client_id,
        ZenIAM_iam_client_secret=zeniam_iam_cient_secret,
        ZenIAM_iam_user_name=zeniam_iam_user_name,
        ZenIAM_iam_user_password=zeniam_iam_user_password,
        ZenIAM_zen_url=zeniam_zen_url,
        ZenIAM_zen_exchange_ssl=zeniam_zen_exchange_ssl,
    )


def register_server_tools(
    graphql_client: GraphQLClient,
    metadata_cache: MetadataCache,
    server_type: ServerType,
) -> None:
    """
    Register tools based on the server type.

    Args:
        graphql_client: The initialized GraphQL client
        metadata_cache: The metadata cache instance
        server_type: The type of server (ServerType enum)
    """
    # Ensure mcp is initialized (type narrowing for type checker)
    assert mcp is not None

    logger.info("Registering tools for %s server", server_type.value)

    # Register tools based on server type
    if server_type == ServerType.CORE:
        register_document_tools(mcp, graphql_client, metadata_cache)
        register_folder_tools(mcp, graphql_client)
        register_class_tools(mcp, graphql_client, metadata_cache)
        register_search_tools(mcp, graphql_client, metadata_cache)
        register_annotation_tools(mcp, graphql_client)
        logger.info("Core tools registered")

    elif server_type == ServerType.VECTOR_SEARCH:
        register_vector_search_tool(mcp, graphql_client)
        logger.info("Vector search tools registered")

    elif server_type == ServerType.LEGAL_HOLD:
        register_legalhold(mcp, graphql_client)
        logger.info("Legal hold tools registered")

    elif server_type == ServerType.FULL:
        register_document_tools(mcp, graphql_client, metadata_cache)
        register_folder_tools(mcp, graphql_client)
        register_class_tools(mcp, graphql_client, metadata_cache)
        register_search_tools(mcp, graphql_client, metadata_cache)
        register_annotation_tools(mcp, graphql_client)
        register_vector_search_tool(mcp, graphql_client)
        register_legalhold(mcp, graphql_client)
        logger.info("All tools registered")

    else:
        raise ValueError(f"Unknown server type: {server_type}")


async def shutdown_client(graphql_client):
    """
    Properly close the GraphQL client's aiohttp session.

    Args:
        graphql_client: The GraphQL client to close
    """
    await graphql_client.close()
    logger.info("GraphQL client session closed")


def _run_server(server_type: ServerType) -> None:
    """
    Common server initialization and run logic.

    Args:
        server_type: The type of server to run (ServerType enum)
    """
    server_name = server_type.value
    logger.info("Starting %s MCP Server", server_name)

    # Initialize the global mcp instance
    _initialize_mcp_server(server_name)

    # Initialize GraphQL client
    graphql_client = initialize_graphql_client()
    logger.info("GraphQL client initialized successfully")

    # Create metadata cache
    metadata_cache = MetadataCache()
    logger.info("Metadata cache created successfully")

    # Register tools for this server type
    register_server_tools(graphql_client, metadata_cache, server_type)
    logger.info("Tools registered for %s server", server_type.value)

    # Ensure mcp is initialized before running (type narrowing for type checker)
    assert mcp is not None, "MCP server failed to initialize"

    # Run the MCP server
    logger.info("Starting %s server - Press Ctrl+C to exit", server_name)
    try:

        def exit_handler():
            # Run the async close in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(shutdown_client(graphql_client))
            loop.close()

        atexit.register(exit_handler)

        # Start the MCP server
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server shutting down")
        # Ensure client is closed on keyboard interrupt
        loop = asyncio.get_event_loop()
        loop.run_until_complete(shutdown_client(graphql_client))
        logger.info("Server shut down gracefully")


def main_core() -> None:
    """Entry point for core CS MCP server."""
    _run_server(ServerType.CORE)


def main_vector_search() -> None:
    """Entry point for vector search MCP server."""
    _run_server(ServerType.VECTOR_SEARCH)


def main_legal_hold() -> None:
    """Entry point for legal hold MCP server."""
    _run_server(ServerType.LEGAL_HOLD)


def main() -> None:
    """
    Default entry point for backward compatibility.
    Runs the core server.
    """
    main_core()


if __name__ == "__main__":
    # Calling main
    main()
