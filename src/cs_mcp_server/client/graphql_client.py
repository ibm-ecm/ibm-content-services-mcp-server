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

import asyncio
from enum import verify
import json
import logging
import mimetypes
import os
import os.path
import re
import ssl
import time
import truststore
import urllib3
import uuid
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Union
from urllib.parse import unquote

import aiohttp
import requests
from aiohttp.helpers import BasicAuth

from .csdeploy.gqlinvoke import GraphqlConnection, GraphqlRequest
from .ssl_adapter import SSLAdapter

# Logger for this module
logger = logging.getLogger("GraphQLClient")


class GraphQLClient(GraphqlConnection):
    """
    A service class to handle all communications with the GraphQL API.
    It manages the client session and authentication headers.
    """

    def __init__(
        self,
        url: str,
        username: str = "",
        password: str = "",
        ssl_enabled: Union[bool, str] = False,
        object_store: str = "",
        token_url: Optional[str] = None,
        token_ssl_enabled: Union[bool, str] = False,
        grant_type: Optional[str] = None,
        scope: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: Optional[float] = 60.0,
        pool_connections: int = 100,
        pool_maxsize: int = 100,
        token_refresh: int = 1800,  # Default to 30 minutes (1800 seconds)
        max_retries: int = 3,  # Maximum number of retries
        retry_delay: float = 1.0,  # Initial delay between retries in seconds
        keepalive_timeout: float = 1800.0,  # Default to 30 minutes
        force_close: bool = False,  # Whether to force close connections
        # ZEN/IAM specific parameters: optional, configure only if GraphQLClient needs to talk to CPE in Cloud Pak.
        # ZEN is an IBM CP4BA front door where all IBM CloudPak services are secured. Zen frontdoor can use IAM for backend
        # authentication. To accomplish this, the front door would redirect the login to IAM. Once the IAM token is retrieved, one would
        # need to exchange the IAM token to a Zen token in order to access any services secured under IBM Cloud Pak.
        # Code in GraphQLRequest and GraphlConnection would do this token retrieval/refresh provided that data is provided.
        #
        # The IAM connection in Zen is similar to OAUTH. One can reuse token_url, grant_type, scope defined above instead
        # of defining similar param with ZENIAM prefix. The spit
        # is just for clarity to define which data is needed for ZEN/IAM connector.
        # For environment variables keys to define value, see caller of this method.
        ZenIAM_iam_url: Optional[
            str
        ] = None,  # IAM url to send user/pwd or client_id/client_secret to IAM to get back IAM token, for example: <iam_host_route>/idprovider/v1/auth/identitytoken
        ZenIAM_iam_ssl_enabled: Union[
            bool, str
        ] = True,  # enforce SSL checking of server cert on IAM route.
        ZenIAM_iam_grant_type: Optional[
            str
        ] = None,  # value passed to IAM url to get back an IAM token. Supported values: 'password'
        ZenIAM_iam_scope: Optional[
            str
        ] = None,  # value passed to IAM url to get back an IAM token. Supported values: 'openid
        ZenIAM_iam_client_id: Optional[
            str
        ] = None,  # value passed to IAM url to get back an IAM token.
        ZenIAM_iam_client_secret: Optional[
            str
        ] = None,  # value passed to IAM url to get back an IAM token.
        ZenIAM_iam_user_name: Optional[
            str
        ] = None,  # value passed to IAM url to get back an IAM token.
        ZenIAM_iam_user_password: Optional[
            str
        ] = None,  # value passed to IAM url to get back an IAM token.
        ZenIAM_zen_url: Optional[
            str
        ] = None,  # Zen url to send IAM to for exchange to Zen token, for example: <zen_host_route>/v1/preauth/validateAuth
        ZenIAM_zen_exchange_ssl: Union[
            bool, str
        ] = True,  # whether ssl checking is enforced on Zen route.
        # END OF:
        # ZEN/IAM specific parameters: optional, configure only if GraphQLClient needs to talk to CPE in Cloud Pak.
    ):
        """
        Initializes the GraphQL client with connection details.

        Args:
            url: The GraphQL API URL
            username: Optional username for authentication
            password: Optional password for authentication
            ssl_enabled: Whether SSL is enabled for the connection (bool) or path to a certificate file (str)
            object_store: Optional object store identifier
            token_url: URL to Token Authentication endpoint for OAuth
            token_ssl_enabled: Whether SSL is enabled for token authentication (bool) or path to a certificate file (str)
            grant_type: OAuth grant type
            scope: OAuth scope
            client_id: OAuth client ID
            client_secret: OAuth client secret
            timeout: Request timeout in seconds
            pool_connections: Number of connections in the pool
            pool_maxsize: Maximum size of the connection pool
            token_refresh: Token refresh interval in seconds
            max_retries: Maximum number of retries for failed requests
            retry_delay: Initial delay between retries in seconds
            keepalive_timeout: Time in seconds to keep idle connections alive (None = keep forever)
            force_close: Whether to force close connections after each request
            ZenIAM_iam_url: Optional[str] = None,  # IAM url to send user/pwd or client_id/client_secret to IAM to get back IAM token, for example: <iam_host_route>/idprovider/v1/auth/identitytoken
            ZenIAM_iam_ssl_enabled: Union[bool, str] = True,  # enforce SSL checking of server cert on IAM route or path to certificate file
            ZenIAM_iam_grant_type: Optional[str] = None,  # value passed to IAM url to get back an IAM token. Supported values: 'password'
            ZenIAM_iam_scope: Optional[str] = None,  # value passed to IAM url to get back an IAM token. Supported values: 'openid
            ZenIAM_iam_client_id: Optional[str] = None,  # value passed to IAM url to get back an IAM token.
            ZenIAM_iam_client_secret: Optional[str] = None,  # value passed to IAM url to get back an IAM token.
            ZenIAM_iam_user_name: Optional[str] = None,  # value passed to IAM url to get back an IAM token.
            ZenIAM_iam_user_password: Optional[str] = None,  # value passed to IAM url to get back an IAM token.
            ZenIAM_zen_url: Optional[str] = None,  # Zen url to send IAM to for exchange to Zen token, for example: <zen_host_route>/v1/preauth/validateAuth
            ZenIAM_zen_exchange_ssl: Union[bool, str] = True,  # whether ssl checking is enforced on Zen route or path to certificate file
        """

        # Sessions for async and sync requests
        self._session = None
        self._sync_session_secure = None
        self._sync_session_insecure = None
        self._ssl_context = None
        self.timeout = timeout
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self._connector = None
        self.keepalive_timeout = keepalive_timeout
        self.force_close = force_close

        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Track last request time for rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms minimum between requests

        # Initialize parent class with required parameters
        kwargs = {
            "url": url,
            "ssl_enabled": ssl_enabled,
            "token_refresh": token_refresh,
            "token_ssl_enabled": token_ssl_enabled,
        }
        if token_url:
            kwargs["token_url"] = token_url

        super().__init__(**kwargs)

        self.object_store = object_store

        # Initialize with OAuth if OAuth parameters are provided
        if ZenIAM_zen_url:
            zeniam_params = {
                "zen_exchange_url": ZenIAM_zen_url,
                "iam_url": ZenIAM_iam_url,
                "iam_ssl_enabled": ZenIAM_iam_ssl_enabled,
                "iam_grant_type": ZenIAM_iam_grant_type,
                "iam_scope": ZenIAM_iam_scope,
                "iam_username": ZenIAM_iam_user_name,
                "iam_password": ZenIAM_iam_user_password,
                "iam_client_id": ZenIAM_iam_client_id,
                "iam_client_secret": ZenIAM_iam_client_secret,
                "zen_exchange_ssl": ZenIAM_zen_exchange_ssl,
            }
            self.initialize_zen_iam(**zeniam_params)
            self.get_token()
        elif token_url and grant_type and scope:
            oauth_params = {
                "oauth_url": token_url,
                "oauth_ssl_enabled": token_ssl_enabled,
                "grant_type": grant_type,
                "scope": scope,
                "username": username,
                "password": password,
            }

            # Only add client_id and client_secret if they are provided
            if client_id:
                oauth_params["client_id"] = client_id
            if client_secret:
                oauth_params["client_secret"] = client_secret

            self.initialize_oauth(**oauth_params)

            # Get the token after initialization
            self.get_token()
        # Initialize with basic auth if credentials are provided and OAuth is not used
        elif username and password:
            self.initialize_basic(username=username, password=password)
        logger.info("Initialized GraphQLClient for %s", url)

    def _get_ssl_context(self):
        """
        Get or create a shared SSL context for both sync and async requests.

        This method creates a unified SSL context that is used by both:
        1. The SSLAdapter for synchronous requests via the requests library
        2. The aiohttp TCPConnector for asynchronous requests

        The method first attempts to create an SSL context using the system's
        truststore via the truststore library. If that fails, it falls back to
        the default SSL context provided by Python's ssl module.

        The method also handles certificate paths provided in any of the SSL flags:
        - ssl_enabled (main API connections)
        - token_ssl_enabled (token authentication connections)
        - iam_ssl_enabled (IAM authentication connections)
        - zen_exchange_ssl (Zen token exchange connections)

        If any of these flags contain a string value, it's treated as a path to
        a certificate file and added to the SSL context's trusted certificates.

        Returns:
            ssl.SSLContext: The configured SSL context object
        """
        if not hasattr(self, "_ssl_context") or self._ssl_context is None:
            # Create an SSL context using truststore for system certificates
            try:
                context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                logger.debug("Created SSL context using system truststore")
            except Exception as e:
                logger.error("Failed to create truststore SSL context: %s", str(e))
                # Fall back to default SSL context
                context = ssl.create_default_context()
                logger.debug("Created default SSL context")

            # Collect certificate paths from all SSL flags
            certificate_paths = []

            # Check all SSL flags and add certificate paths
            ssl_flags = {
                "main": self.ssl_enabled,
                "token": getattr(self, "token_ssl_enabled", None),
                "zeniam_iam": getattr(self, "iam_ssl_enabled", None),
                "zeniam_zen": getattr(self, "zen_exchange_ssl", None),
            }

            for name, flag in ssl_flags.items():
                if isinstance(flag, str):
                    certificate_paths.append(flag)
                    logger.debug("Added certificate path from %s: %s", name, flag)

            # Add all certificate files to the context
            for cert_path in certificate_paths:
                try:
                    context.load_verify_locations(cafile=cert_path)
                    logger.debug("Added certificate file to context: %s", cert_path)
                except Exception as e:
                    logger.error(
                        "Failed to add certificate file %s to context: %s",
                        cert_path,
                        str(e),
                    )

            self._ssl_context = context

        return self._ssl_context

    async def _ensure_session(self):
        """
        Ensure an aiohttp session exists with proper connection pooling and SSL settings.

        This method creates or reuses an aiohttp.ClientSession with a TCPConnector
        that's configured with the same shared SSL context used by synchronous requests.

        The connector is configured with:
        - Connection pooling settings (limit, limit_per_host)
        - Keepalive settings (if not force_close)
        - The shared SSL context from _get_ssl_context()

        This ensures consistent SSL behavior between synchronous and asynchronous
        requests, using the same certificates and verification settings.

        Returns:
            aiohttp.ClientSession: A configured aiohttp session
        """
        if self._session is None or self._session.closed:
            if self._connector is None or self._connector.closed:
                # Configure connector parameters based on settings
                connector_params = {
                    "limit": self.pool_connections,
                    "limit_per_host": self.pool_maxsize,
                    "enable_cleanup_closed": True,
                    "force_close": self.force_close,
                }

                # Only add keepalive_timeout if force_close is False
                if not self.force_close and self.keepalive_timeout is not None:
                    connector_params["keepalive_timeout"] = self.keepalive_timeout

                # Get the shared SSL context
                ssl_context = self._get_ssl_context()
                connector_params["ssl"] = ssl_context

                self._connector = aiohttp.TCPConnector(**connector_params)

                if self.force_close:
                    logger.debug(
                        "Created TCP connector with force_close=True (connections will close after each request)"
                    )
                else:
                    logger.debug(
                        "Created TCP connector with keepalive_timeout=%s",
                        self.keepalive_timeout,
                    )
                logger.debug("Created TCP connector with shared SSL context")
            self._session = aiohttp.ClientSession(connector=self._connector)
        return self._session

    def _get_sync_session(self, use_secure=True):
        """
        Get or create a requests session with appropriate SSL settings.

        This method maintains two separate session objects:
        - A secure session with SSL verification enabled (using a custom SSL adapter)
        - An insecure session with SSL verification disabled

        The method returns the appropriate session based on the use_secure parameter.
        If use_secure is True, it returns the secure session with the custom SSL adapter.
        If use_secure is False, it returns the insecure session with SSL verification disabled.

        Args:
            use_secure: Whether to use the secure session (True) or insecure session (False)

        Returns:
            requests.Session: A configured requests session with appropriate SSL settings
        """
        if use_secure:
            # Return or create the secure session
            if self._sync_session_secure is None:
                # Create a new secure session
                self._sync_session_secure = requests.Session()

                # Get the shared SSL context
                ssl_context = self._get_ssl_context()

                # Create the SSL adapter with the shared SSL context
                ssl_adapter = SSLAdapter(
                    ssl_context=ssl_context,
                    pool_connections=self.pool_connections,
                    pool_maxsize=self.pool_maxsize,
                )

                # Mount the adapter for https
                self._sync_session_secure.mount("https://", ssl_adapter)

                logger.debug(
                    "Created new secure requests session with custom SSL adapter"
                )

            return self._sync_session_secure
        else:
            # Return or create the insecure session
            if self._sync_session_insecure is None:
                # Create a new insecure session
                self._sync_session_insecure = requests.Session()

                # Disable SSL verification
                self._sync_session_insecure.verify = False

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                logger.debug(
                    "Created new insecure requests session with SSL verification disabled"
                )

            return self._sync_session_insecure

    def execute(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        file_paths: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query synchronously with retry logic.

        Args:
            query: The GraphQL query string
            variables: Optional variables for the query
            file_paths: Optional dictionary mapping variable names to file paths for file uploads

        Returns:
            The query result as a dictionary
        """
        # Default error response in case all retries fail
        error_response = {
            "error": True,
            "message": "Unknown error occurred during GraphQL request",
            "timestamp": datetime.now().isoformat(),
        }

        # Apply rate limiting
        self._apply_rate_limiting(is_async=False)

        # Check if token needs to be refreshed
        token_refreshed = self._check_sync_token_refresh()
        if token_refreshed:
            logger.debug("Token refreshed before executing request")

        # Implement retry logic
        retries = 0
        last_exception = None

        # Determine if this is a file upload request
        is_file_upload = file_paths is not None and len(file_paths) > 0

        while retries <= self.max_retries:
            try:
                if is_file_upload:
                    # Handle file upload with multipart form data
                    # Prepare headers and cookies (without Content-Type as it will be set by requests)
                    headers = self._prepare_headers(include_content_type=False)
                    cookies = self._prepare_cookies()

                    # Prepare authentication
                    auth = self._prepare_auth(is_async=False)

                    # Prepare the operations part of the form
                    operations = {
                        "query": query,
                        "variables": variables if variables else {},
                    }

                    # Prepare the multipart form data
                    payload = {"graphql": json.dumps(operations)}
                    files = []

                    # Add each file to the files list
                    if file_paths:
                        for var_name, file_path in file_paths.items():
                            file_name = os.path.basename(file_path)
                            mime_type = (
                                mimetypes.guess_type(file_path)[0]
                                or "application/octet-stream"
                            )
                            files.append(
                                (
                                    var_name,
                                    (file_name, open(file_path, "rb"), mime_type),
                                )
                            )

                    # Determine whether to use secure or insecure session based on ssl_enabled flag
                    use_secure = self.ssl_enabled is not False
                    session = self._get_sync_session(use_secure=use_secure)
                    response = session.post(
                        url=self.url,
                        headers=headers,
                        cookies=cookies,
                        auth=auth,  # pyright: ignore
                        data=payload,
                        files=files,
                        timeout=self.timeout,
                        verify=self.ssl_enabled if self.ssl_enabled else False,
                    )

                    # Close all file handles
                    for _, file_tuple in files:
                        if len(file_tuple) > 1 and hasattr(file_tuple[1], "close"):
                            file_tuple[1].close()

                    # We no longer need to check for 401 and refresh token here
                    # since we proactively refresh tokens before sending requests

                    if response.status_code != 200:
                        raise Exception(
                            f"Request failed with status code: {response.status_code}. Response: {response.text}"
                        )

                    result = response.json()
                else:
                    # Standard GraphQL request using appropriate session based on ssl_enabled flag
                    use_secure = self.ssl_enabled is not False
                    session = self._get_sync_session(use_secure=use_secure)

                    # Prepare headers and cookies
                    headers = self._prepare_headers()
                    cookies = self._prepare_cookies()

                    # Prepare authentication
                    auth = self._prepare_auth(is_async=False)

                    # Prepare the payload
                    json_payload = {
                        "query": query,
                        "variables": variables if variables else {},
                    }

                    # Execute the request using the session with custom SSL adapter
                    response = session.post(
                        url=self.url,
                        headers=headers,
                        cookies=cookies,
                        auth=auth,  # pyright: ignore
                        json=json_payload,
                        timeout=self.timeout,
                        verify=self.ssl_enabled if self.ssl_enabled else False,
                    )

                    if response.status_code != 200:
                        raise Exception(
                            f"Request failed with status code: {response.status_code}. Response: {response.text}"
                        )

                    result = response.json()

                # Check for GraphQL errors
                if "errors" in result:
                    errors = result["errors"]
                    error_message = "; ".join(
                        [error.get("message", "Unknown error") for error in errors]
                    )
                    logger.warning("GraphQL errors: %s", error_message)

                    # Add error details to the result
                    result["_error_details"] = {
                        "timestamp": datetime.now().isoformat(),
                        "query": query,
                        "variables": variables,
                    }

                return result

            except Exception as e:
                last_exception = e
                retries += 1

                # Make sure to close any open file handles on exception if this was a file upload
                if is_file_upload and "files" in locals():
                    try:
                        for _, file_tuple in files:  # pyright: ignore
                            if len(file_tuple) > 1 and hasattr(file_tuple[1], "close"):
                                try:
                                    file_tuple[1].close()
                                except:
                                    pass
                    except UnboundLocalError:
                        pass  # files variable might not be defined

                if retries <= self.max_retries:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** (retries - 1))
                    logger.warning(
                        "Request failed: %s. Retrying in %.2fs (%d/%d)",
                        str(e),
                        delay,
                        retries,
                        self.max_retries,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Request failed after %d retries: %s", self.max_retries, str(e)
                    )
                    # Return an error response instead of raising an exception
                    error_response["message"] = (
                        f"GraphQL request failed after {self.max_retries} retries: {str(last_exception)}"
                    )
                    error_response["error_type"] = type(last_exception).__name__
                    return error_response

        # This should never be reached bc of return statements above,
        # but we include it to satisfy the type checker
        return error_response

    async def _check_token_refresh(self):
        """
        Check if token needs to be refreshed and refresh it if necessary (async version).

        Returns:
            bool: True if token was refreshed, False otherwise
        """
        # Add a safety margin (10% of token_refresh time) to refresh tokens earlier
        # This helps prevent 401 errors by refreshing tokens before they expire
        safety_margin = self.token_refresh * 0.1 if self.token_refresh else 0

        if (
            self.token
            and self.token_refresh
            and self.token_fetched_time
            and int((datetime.now() - self.token_fetched_time).total_seconds())
            > (self.token_refresh - safety_margin)
        ):
            self.get_token()
            return True
        return False

    async def execute_async(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query asynchronously with improved error handling and retry logic.

        Args:
            query: The GraphQL query string
            variables: Optional variables for the query

        Returns:
            The query result as a dictionary
        """
        # Default error response in case all retries fail
        error_response = {
            "error": True,
            "message": "Unknown error occurred during GraphQL request",
            "timestamp": datetime.now().isoformat(),
        }

        # Check if token needs to be refreshed
        try:
            token_refreshed = await self._check_token_refresh()
            if token_refreshed:
                logger.debug("Token refreshed before executing async request")
        except Exception as e:
            logger.error("Failed to refresh token: %s", str(e))
            error_response["message"] = f"Failed to refresh token: {str(e)}"
            return error_response

        # Prepare headers, cookies, and auth
        headers = self._prepare_headers()
        cookies = self._prepare_cookies()
        auth = self._prepare_auth(is_async=True)

        json_payload = {"query": query, "variables": variables if variables else {}}

        try:
            # Get the session which already has the SSL context configured in the connector
            session = await self._ensure_session()
        except Exception as e:
            logger.error("Failed to create session: %s", str(e))
            error_response["message"] = f"Failed to create session: {str(e)}"
            error_response["error_type"] = type(e).__name__
            return error_response

        # Implement retry logic
        retries = 0
        last_exception = None

        while retries <= self.max_retries:
            try:
                # Apply rate limiting
                rate_limit_coro = self._apply_rate_limiting(is_async=True)
                if rate_limit_coro:
                    await rate_limit_coro

                # Execute request with timeout
                async with session.post(
                    url=self.url,
                    headers=headers,
                    json=json_payload,
                    cookies=cookies,
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=False if self.ssl_enabled == False else None,
                ) as response:
                    # We no longer need to check for 401 and refresh token here
                    # since we proactively refresh tokens before sending requests
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Request failed with status code: {response.status}. Response: {error_text}"
                        )
                    else:
                        result = await response.json()

                    # Check for GraphQL errors
                    if "errors" in result:
                        errors = result["errors"]
                        error_message = "; ".join(
                            [error.get("message", "Unknown error") for error in errors]
                        )
                        logger.warning("GraphQL errors: %s", error_message)

                        # Add error details to the result
                        result["_error_details"] = {
                            "timestamp": datetime.now().isoformat(),
                            "query": query,
                            "variables": variables,
                        }

                    return result

            except (
                aiohttp.ClientConnectorError,
                aiohttp.ClientResponseError,
                aiohttp.ClientError,
                asyncio.TimeoutError,
            ) as e:
                last_exception = e
                retries += 1

                if retries <= self.max_retries:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** (retries - 1))
                    logger.warning(
                        "Request failed: %s. Retrying in %.2fs (%d/%d)",
                        str(e),
                        delay,
                        retries,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                else:
                    error_type = type(e).__name__
                    error_message = str(e)
                    logger.error(
                        "%s after %d retries: %s",
                        error_type,
                        self.max_retries,
                        error_message,
                    )

                    # Return an error response instead of raising an exception
                    error_response["error_type"] = error_type
                    error_response["message"] = error_message
                    return error_response
            except Exception as e:
                # Catch any other exceptions
                error_type = type(e).__name__
                error_message = str(e)
                logger.error("Unexpected %s: %s", error_type, error_message)

                error_response["error_type"] = error_type
                error_response["message"] = error_message
                return error_response

        # This should never be reached due to the return statements in the exception handlers,
        # but we include it to satisfy the type checker
        if last_exception:
            error_response["message"] = (
                f"GraphQL request failed after {self.max_retries} retries: {str(last_exception)}"
            )
            error_response["error_type"] = type(last_exception).__name__

        return error_response

    async def close(self):
        """Close the aiohttp session and connector, and the synchronous sessions"""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector and not self._connector.closed:
            await self._connector.close()
        if self._sync_session_secure:
            self._sync_session_secure.close()
        if self._sync_session_insecure:
            self._sync_session_insecure.close()
        self._session = None
        self._connector = None
        self._sync_session_secure = None
        self._sync_session_insecure = None
        logger.info("GraphQL client sessions closed")

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    def _apply_rate_limiting(self, is_async=False):
        """
        Apply rate limiting to prevent too many requests in a short period.

        Args:
            is_async: Whether this is being called from an async method

        Returns:
            None for sync calls, coroutine for async calls (must be awaited)
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.debug("Rate limiting: sleeping for %.3fs", sleep_time)
            if is_async:
                return asyncio.sleep(sleep_time)
            else:
                time.sleep(sleep_time)
        self.last_request_time = time.time()
        return None

    def _prepare_headers(self, include_content_type=True) -> Mapping[str, str | None]:
        """
        Prepare headers for requests including authentication and XSRF token.

        Args:
            include_content_type: Whether to include Content-Type header

        Returns:
            Dictionary of headers
        """
        headers = {"ECM-CS-XSRF-Token": self.xsrf_token}
        if include_content_type:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _prepare_cookies(self):
        """
        Prepare cookies for requests including XSRF token.

        Returns:
            Dictionary of cookies
        """
        return {"ECM-CS-XSRF-Token": str(self.xsrf_token)}

    def _prepare_auth(self, is_async=False) -> BasicAuth | tuple[str, str] | None:
        """
        Prepare authentication for requests.

        Args:
            is_async: Whether this is being called from an async method

        Returns:
            Authentication object appropriate for the request type
        """
        if self.token:
            auth = None
        elif self.auth_user and self.auth_pass:
            if is_async:
                auth = aiohttp.BasicAuth(self.auth_user, self.auth_pass)
            else:
                auth = (self.auth_user, self.auth_pass)
        else:
            auth = None
            logger.warning("No authentication method available")
        return auth

    def _check_sync_token_refresh(self) -> bool:
        """
        Check if token needs to be refreshed and refresh it if necessary (synchronous version).

        Returns:
            bool: True if token was refreshed, False otherwise
        """
        # Add a safety margin (10% of token_refresh time) to refresh tokens earlier
        # This helps prevent 401 errors by refreshing tokens before they expire
        safety_margin = self.token_refresh * 0.1 if self.token_refresh else 0

        if (
            self.token
            and self.token_refresh
            and self.token_fetched_time
            and int((datetime.now() - self.token_fetched_time).total_seconds())
            > (self.token_refresh - safety_margin)
        ):
            self.get_token()
            return True
        return False

    def get_token(self) -> None:
        """
        Override parent class method to use our custom SSL adapter for token requests.

        This method executes a request to get an authentication token after the client
        has been initialized with authentication information. It uses the custom SSL adapter
        via _get_sync_session() to ensure consistent SSL behavior with other requests.

        The method:
        1. Generates a new XSRF token
        2. Gets a session with the custom SSL adapter
        3. Executes the token request with appropriate SSL verification
        4. Processes the response to extract the token
        5. Optionally exchanges the IAM token if zen_exchange_url is configured

        Only call this method if using token-based authentication.

        Raises:
            Exception: If the token request fails or the response doesn't contain a token
        """
        # Generate a new XSRF token
        self.xsrf_token = str(uuid.uuid4())
        operation = "POST" if self.payload else "GET"
        auth = (
            (self.auth_user, self.auth_pass)
            if (self.auth_user and self.auth_pass)
            else None
        )

        # Get a session with appropriate SSL settings based on token_ssl_enabled flag
        use_secure = self.token_ssl_enabled is not False
        session = self._get_sync_session(use_secure=use_secure)

        # Execute the request using our session
        response = session.request(
            operation,
            self.token_url,
            headers=self.headers,
            data=self.payload,
            timeout=self.timeout or 300,
            verify=self.token_ssl_enabled if self.token_ssl_enabled else False,
            auth=auth,
        )

        logger.info("GraphQL Connection sent token request to: %s", self.token_url)
        logger.debug(
            "GraphQL Connection Token Request Details: Headers=%s, Data=%s, Verify=%s "
            "Response details: Headers=%s, Text=%s",
            self.headers,
            self.payload,
            self.token_ssl_enabled,
            response.headers,
            response.text,
        )

        try:
            if "token" in response.json():
                self.token = response.json()["token"]
            elif "access_token" in response.json():
                self.token = response.json()["access_token"]
            else:
                raise Exception("Neither token nor access token is present in response")
            self.token_fetched_time = datetime.now()
            if self.zen_exchange_url:
                self._exchange_iam_token()
        except (ValueError, KeyError) as exception:
            logger.error("Request failed with status code: %s", response.status_code)
            try:
                error_data = response.json()
                logger.error("Response JSON: %s", error_data)
            except ValueError:
                logger.error("Response Text: %s", response.text)
            raise Exception(
                f"Token Failed to fetch with status code: {response.status_code}"
            ) from exception

    def _exchange_iam_token(self) -> None:
        """
        Override parent class method to use our custom SSL adapter for Zen token exchange.

        This method exchanges an IAM token for a Zen token by making a request to the
        Zen exchange URL. It uses the custom SSL adapter via _get_sync_session() to ensure
        consistent SSL behavior with other requests.

        The method:
        1. Prepares headers with the IAM token and username
        2. Gets a session with the custom SSL adapter
        3. Executes the token exchange request with appropriate SSL verification
        4. Processes the response to extract the Zen token

        This method is automatically called by get_token() if zen_exchange_url is configured.

        Raises:
            Exception: If the token exchange request fails or the response doesn't contain a token
        """
        # Handle potential None values safely
        if (
            not self.payload
            or not isinstance(self.payload, dict)
            or not self.zen_exchange_url
        ):
            logger.error("Missing required data for IAM token exchange")
            return

        username = self.payload.get("username", "")
        headers = {"username": username, "iam-token": self.token}

        # Get a session with appropriate SSL settings based on zen_exchange_ssl flag
        use_secure = self.zen_exchange_ssl is not False
        session = self._get_sync_session(use_secure=use_secure)

        # Execute the request using our session
        response = session.request(
            "GET",
            self.zen_exchange_url,
            headers=headers,
            timeout=self.timeout or 300,
            verify=self.zen_exchange_ssl if self.zen_exchange_ssl else False,
        )

        logger.info(
            "GraphQL Connection sent IAM token exchange request to: %s",
            self.zen_exchange_url,
        )
        logger.debug(
            "GraphQL Connection IAM token exchange request details: Headers=%s, Verify=%s "
            "Response details: Headers=%s, Text=%s",
            headers,
            self.zen_exchange_ssl,
            response.headers,
            response.text,
        )

        try:
            self.token = response.json()["accessToken"]
        except (ValueError, KeyError) as exception:
            logger.error("Request failed with status code: %s", response.status_code)
            try:
                error_data = response.json()
                logger.error("Response JSON: %s", error_data)
            except ValueError:
                logger.error("Response Text: %s", response.text)
            raise Exception(
                f"Request failed with status code: {response.status_code}"
            ) from exception

    def _prepare_download_url(self, download_url):
        """
        Prepare download URL by replacing '/graphql' at the end of the base URL.

        Args:
            download_url: The download URL path

        Returns:
            Complete URL for the download
        """
        return self.url.removesuffix("/graphql") + download_url

    def download_text(self, download_url: str) -> str:
        """
        Download text content from a URL by replacing '/graphql' in the base URL.

        Args:
            download_url: The download URL path to append to the base URL (replacing '/graphql')

        Returns:
            The text content of the response or an error message if the request fails
        """
        # Default error response in case of failure
        error_text = "Error: Failed to download text content"

        # Apply rate limiting
        self._apply_rate_limiting(is_async=False)

        # Prepare URL
        url = self._prepare_download_url(download_url)

        # Prepare headers without Content-Type since we're doing a GET request
        headers = self._prepare_headers(include_content_type=False)

        # Prepare cookies
        cookies = self._prepare_cookies()

        # Check if token needs to be refreshed
        token_refreshed = self._check_sync_token_refresh()
        if token_refreshed:
            logger.debug("Token refreshed before downloading text")

        # Prepare authentication
        auth = self._prepare_auth(is_async=False)

        # Implement retry logic
        retries = 0
        last_exception = None

        while retries <= self.max_retries:
            try:
                # Get the session with appropriate SSL settings based on ssl_enabled flag
                use_secure = self.ssl_enabled is not False
                session = self._get_sync_session(use_secure=use_secure)
                response = session.get(
                    url=url,
                    headers=headers,
                    cookies=cookies,
                    auth=auth,  # type: ignore
                    timeout=self.timeout,
                    verify=self.ssl_enabled if self.ssl_enabled else False,
                )

                # We no longer need to check for 401 and refresh token here
                # since we proactively refresh tokens before sending requests

                if response.status_code != 200:
                    raise Exception(
                        f"Request failed with status code: {response.status_code}. Response: {response.text}"
                    )

                return response.text

            except Exception as e:
                last_exception = e
                retries += 1

                if retries <= self.max_retries:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** (retries - 1))
                    logger.warning(
                        "Download request failed: %s. Retrying in %.2fs (%d/%d)",
                        str(e),
                        delay,
                        retries,
                        self.max_retries,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Download request failed after %d retries: %s",
                        self.max_retries,
                        str(e),
                    )
                    return f"{error_text}: {str(e)}"

        # This should never be reached due to the return statements above
        return error_text

    async def download_text_async(self, download_url: str) -> str:
        """
        Download text content from a URL asynchronously by replacing '/graphql' in the base URL.

        Args:
            download_url: The download URL path to append to the base URL (replacing '/graphql')

        Returns:
            The text content of the response
        """
        # Default error response in case of failure
        error_text = "Error: Failed to download text content"

        # Check if token needs to be refreshed
        try:
            token_refreshed = await self._check_token_refresh()
            if token_refreshed:
                logger.debug("Token refreshed before downloading text asynchronously")
        except Exception as e:
            logger.error("Failed to refresh token: %s", str(e))
            return f"{error_text}: Failed to refresh token: {str(e)}"

        # Prepare URL
        url = self._prepare_download_url(download_url)

        # Prepare headers and cookies
        headers = self._prepare_headers(include_content_type=False)
        cookies = self._prepare_cookies()

        # Prepare authentication
        auth = self._prepare_auth(is_async=True)

        try:
            # Get the session which already has the SSL context configured in the connector
            session = await self._ensure_session()
        except Exception as e:
            logger.error("Failed to create session: %s", str(e))
            return f"{error_text}: Failed to create session: {str(e)}"

        # Implement retry logic
        retries = 0
        last_exception = None

        while retries <= self.max_retries:
            try:
                # Apply rate limiting
                rate_limit_coro = self._apply_rate_limiting(is_async=True)
                if rate_limit_coro:
                    await rate_limit_coro

                # Execute request with timeout
                async with session.get(
                    url=url,
                    headers=headers,
                    cookies=cookies,
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    # We no longer need to check for 401 and refresh token here
                    # since we proactively refresh tokens before sending requests
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Request failed with status code: {response.status}. Response: {error_text}"
                        )
                    else:
                        return await response.text()

            except (
                aiohttp.ClientConnectorError,
                aiohttp.ClientResponseError,
                aiohttp.ClientError,
                asyncio.TimeoutError,
            ) as e:
                last_exception = e
                retries += 1

                if retries <= self.max_retries:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** (retries - 1))
                    logger.warning(
                        "Download request failed: %s. Retrying in %.2fs (%d/%d)",
                        str(e),
                        delay,
                        retries,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                else:
                    error_message = str(e)
                    logger.error(
                        "Download request failed after %d retries: %s",
                        self.max_retries,
                        error_message,
                    )
                    return f"{error_text}: {error_message}"
            except Exception as e:
                # Catch any other exceptions
                error_message = str(e)
                logger.error("Unexpected error during download: %s", error_message)
                return f"{error_text}: {error_message}"

        # This should never be reached due to the return statements in the exception handlers
        if last_exception:
            return f"{error_text}: {str(last_exception)}"

        return error_text

    def download_content(
        self, download_url: str, download_folder_path: str
    ) -> Dict[str, Any]:
        """
        Download content from a URL and save it to a file in the specified folder.
        The filename is extracted from the content-disposition header.

        Args:
            download_url: The download URL path to append to the base URL (replacing '/graphql')
            download_folder_path: The folder path where the file will be saved

        Returns:
            A dictionary with status information about the download:
            {
                "success": bool,
                "message": str,
                "file_path": str (if successful),
                "error": str (if failed)
            }
        """
        # Default response
        result = {
            "success": False,
            "message": "Failed to download content",
            "error": "Unknown error",
        }

        # Validate download folder path
        if not os.path.exists(download_folder_path):
            result["error"] = f"Download folder does not exist: {download_folder_path}"
            return result

        if not os.path.isdir(download_folder_path):
            result["error"] = (
                f"Download path is not a directory: {download_folder_path}"
            )
            return result

        # Apply rate limiting
        self._apply_rate_limiting(is_async=False)

        # Prepare URL
        url = self._prepare_download_url(download_url)

        # Prepare headers without Content-Type since we're doing a GET request
        headers = self._prepare_headers(include_content_type=False)

        # Prepare cookies
        cookies = self._prepare_cookies()

        # Check if token needs to be refreshed
        token_refreshed = self._check_sync_token_refresh()
        if token_refreshed:
            logger.debug("Token refreshed before downloading content")

        # Prepare authentication
        auth = self._prepare_auth(is_async=False)

        # Implement retry logic
        retries = 0
        last_exception = None

        while retries <= self.max_retries:
            try:
                # Get the session with appropriate SSL settings based on ssl_enabled flag
                use_secure = self.ssl_enabled is not False
                session = self._get_sync_session(use_secure=use_secure)
                response = session.get(
                    url=url,
                    headers=headers,
                    cookies=cookies,
                    auth=auth,  # type: ignore
                    timeout=self.timeout,
                    stream=True,  # Use streaming to handle large files
                    verify=self.ssl_enabled
                    is not False,  # Disable verification if ssl_enabled is False
                )

                if response.status_code != 200:
                    raise Exception(
                        f"Request failed with status code: {response.status_code}. Response: {response.text}"
                    )

                # Extract filename from content-disposition header
                content_disposition = response.headers.get("content-disposition", "")
                if not content_disposition or "filename=" not in content_disposition:
                    raise Exception(
                        f"Content-disposition header missing or invalid: {content_disposition}"
                    )

                # Parse the filename from the header
                # Format example: attachment; filename="Patient%20282142%20report%2021%20(1).pdf";filename*=utf-8''Patient%20282142%20report%2021%20(1).pdf
                # Search is guaranteed to succeed
                file_path = re.search(r'filename="([^"]+)"', content_disposition)
                filename = file_path.group(1)  # pyright: ignore

                # URL decode the filename if needed
                filename = unquote(filename)

                # Create full file path
                file_path = os.path.join(download_folder_path, filename)

                # Write content to file
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                result["success"] = True
                result["message"] = f"File downloaded successfully to {file_path}"
                result["file_path"] = file_path
                return result

            except Exception as e:
                last_exception = e
                retries += 1

                if retries <= self.max_retries:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** (retries - 1))
                    logger.warning(
                        "Download request failed: %s. Retrying in %.2fs (%d/%d)",
                        str(e),
                        delay,
                        retries,
                        self.max_retries,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Download request failed after %d retries: %s",
                        self.max_retries,
                        str(e),
                    )
                    result["error"] = str(e)
                    return result

        # This should never be reached due to the return statements above
        if last_exception:
            result["error"] = str(last_exception)

        return result

    async def download_content_async(
        self, download_url: str, download_folder_path: str
    ) -> Dict[str, Any]:
        """
        Download content from a URL asynchronously and save it to a file in the specified folder.
        The filename is extracted from the content-disposition header.

        Args:
            download_url: The download URL path to append to the base URL (replacing '/graphql')
            download_folder_path: The folder path where the file will be saved

        Returns:
            A dictionary with status information about the download:
            {
                "success": bool,
                "message": str,
                "file_path": str (if successful),
                "error": str (if failed)
            }
        """
        # Default response
        result = {
            "success": False,
            "message": "Failed to download content asynchronously",
            "error": "Unknown error",
        }

        # Validate download folder path
        if not os.path.exists(download_folder_path):
            result["error"] = f"Download folder does not exist: {download_folder_path}"
            return result

        if not os.path.isdir(download_folder_path):
            result["error"] = (
                f"Download path is not a directory: {download_folder_path}"
            )
            return result

        # Check if token needs to be refreshed
        try:
            token_refreshed = await self._check_token_refresh()
            if token_refreshed:
                logger.debug(
                    "Token refreshed before downloading content asynchronously"
                )
        except Exception as e:
            logger.error("Failed to refresh token: %s", str(e))
            result["error"] = f"Failed to refresh token: {str(e)}"
            return result

        # Prepare URL
        url = self._prepare_download_url(download_url)

        # Prepare headers and cookies
        headers = self._prepare_headers(include_content_type=False)
        cookies = self._prepare_cookies()

        # Prepare authentication
        auth = self._prepare_auth(is_async=True)

        try:
            # Get the session which already has the SSL context configured in the connector
            session = await self._ensure_session()
        except Exception as e:
            logger.error("Failed to create session: %s", str(e))
            result["error"] = f"Failed to create session: {str(e)}"
            return result

        # Implement retry logic
        retries = 0
        last_exception = None

        while retries <= self.max_retries:
            try:
                # Apply rate limiting
                rate_limit_coro = self._apply_rate_limiting(is_async=True)
                if rate_limit_coro:
                    await rate_limit_coro

                # Execute request with timeout
                async with session.get(
                    url=url,
                    headers=headers,
                    cookies=cookies,
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Request failed with status code: {response.status}. Response: {error_text}"
                        )

                    # Extract filename from content-disposition header
                    content_disposition = response.headers.get(
                        "content-disposition", ""
                    )
                    if (
                        not content_disposition
                        or "filename=" not in content_disposition
                    ):
                        raise Exception(
                            f"Content-disposition header missing or invalid: {content_disposition}"
                        )

                    # Parse the filename from the header
                    # Format example: attachment; filename="Patient%20282142%20report%2021%20(1).pdf";filename*=utf-8''Patient%20282142%20report%2021%20(1).pdf
                    # Search is guaranteed to succeed
                    file_path = re.search(r'filename="([^"]+)"', content_disposition)
                    filename = file_path.group(1)  # pyright: ignore

                    filename = unquote(filename)

                    # Create full file path
                    file_path = os.path.join(download_folder_path, filename)

                    # Write content to file
                    with open(file_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            if chunk:
                                f.write(chunk)

                    result["success"] = True
                    result["message"] = f"File downloaded successfully to {file_path}"
                    result["file_path"] = file_path
                    return result

            except (
                aiohttp.ClientConnectorError,
                aiohttp.ClientResponseError,
                aiohttp.ClientError,
                asyncio.TimeoutError,
            ) as e:
                last_exception = e
                retries += 1

                if retries <= self.max_retries:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** (retries - 1))
                    logger.warning(
                        "Download request failed: %s. Retrying in %.2fs (%d/%d)",
                        str(e),
                        delay,
                        retries,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                else:
                    error_message = str(e)
                    logger.error(
                        "Download request failed after %d retries: %s",
                        self.max_retries,
                        error_message,
                    )
                    result["error"] = error_message
                    return result
            except Exception as e:
                # Catch any other exceptions
                error_message = str(e)
                logger.error("Unexpected error during download: %s", error_message)
                result["error"] = error_message
                return result

        # This should never be reached due to the return statements in the exception handlers
        if last_exception:
            result["error"] = str(last_exception)

        return result
