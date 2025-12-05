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
Custom SSL Adapter for requests library

This module provides a custom HTTPAdapter that uses a provided SSL context
for all HTTPS connections. This ensures consistent SSL behavior across
all requests made through the adapter.

The SSLAdapter is designed to work with the GraphQLClient class to provide
a unified SSL handling approach for both synchronous and asynchronous requests.
"""

import logging
from requests.adapters import HTTPAdapter

# Set up logging
logger = logging.getLogger("SSLAdapter")

__all__ = ["SSLAdapter"]


class SSLAdapter(HTTPAdapter):
    """
    A custom HTTP adapter that uses a provided SSL context for requests library.

    This adapter uses a single SSL context for all HTTPS connections, ensuring
    consistent SSL behavior across all requests. It's designed to be used with
    the GraphQLClient class, which creates and manages the SSL context.

    The adapter is mounted to the 'https://' prefix in a requests.Session object,
    so it will be used for all HTTPS requests made through that session.

    Example usage:
        ssl_context = create_ssl_context()
        session = requests.Session()
        adapter = SSLAdapter(ssl_context=ssl_context)
        session.mount('https://', adapter)
    """

    def __init__(self, ssl_context, **kwargs):
        """
        Initialize the SSL adapter with the given SSL context.

        Args:
            ssl_context: The SSL context to use for all HTTPS connections.
                         This should be a properly configured ssl.SSLContext object.
            **kwargs: Additional arguments to pass to HTTPAdapter, such as
                      pool_connections, pool_maxsize, etc.
        """
        self.ssl_context = ssl_context
        super().__init__(**kwargs)
        logger.debug("SSLAdapter initialized with custom SSL context")

    def init_poolmanager(self, *args, **kwargs):
        """
        Initialize the connection pool manager with the provided SSL context.

        This method is called by requests when creating a new connection pool.
        By providing our SSL context here, we ensure all connections made through
        this adapter use the same SSL configuration.

        Args:
            *args: Positional arguments to pass to the parent init_poolmanager
            **kwargs: Keyword arguments to pass to the parent init_poolmanager
        """
        kwargs["ssl_context"] = self.ssl_context
        logger.debug("Connection pool manager initialized with custom SSL context")
        return super().init_poolmanager(*args, **kwargs)
