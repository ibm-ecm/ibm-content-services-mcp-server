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

"""Module containing classes to maintain connection to CPE GraphQL Endpoint"""

from datetime import datetime
from enum import Enum, auto
import json
from typing import Union
import uuid
import logging
import mimetypes
import requests

from .audit import (
    AuditLogger,
    _GraphqlRequestEntry,
    _GraphqlLogOperation,
)
from ._implutil import CSDeployException

logger = logging.getLogger(__name__)


class GraphqlConnection:
    """Class containing information for graphql request's authentication"""

    def __init__(
        self,
        url: str,
        ssl_enabled: Union[bool, str] = True,
        token_url: str = None,
        token: str = None,
        token_ssl_enabled: Union[bool, str] = True,
        token_refresh: int = None,
    ) -> None:
        """Initialize GraphQL Connection object with authentication information

        Args:
            url (str): URL to GraphQL Endpoint
            ssl_enabled (bool, optional): Bool as flag if SSL should be enabled to authenticate, or
                string as path to certificate file. Only disable if you're unable
                to validate endpoint certificate.
                Defaults to True.
            token_url (str, optional): URL to Token Authentication endpoint. If using Zen/IAM
                this is IAM endpoint. Defaults to None for basic auth.
            token (str, optional): Custom token to authenticate to GQL endpoint.
                Leave empty unless token is generated with a custom method.
                Defaults to None.
            token_ssl_enabled (bool, optional): Bool as flag if SSL should be enabled to authenticate, or
                string as path to certificate file. Only disable if you're unable
                to validate endpoint certificate.
                Defaults to True.
            token_refresh (int, optional): Time in seconds when token should be refreshed.
                If value is passed in, token will refresh in subsequent requests
                after it's initialized. Defaults to None for no token refresh.
        """
        self.url = url
        self.token_url = token_url
        self.token = token
        self.ssl_enabled = ssl_enabled
        self.token_ssl_enabled = token_ssl_enabled
        self.token_refresh = token_refresh

        self.headers = {}
        self.payload = {}
        self.auth_user = None
        self.auth_pass = None
        self.xsrf_token = None
        self.token_fetched_time = None
        self.zen_exchange_url = None
        self.zen_exchange_ssl = None
        self._auth_type = None

    class AUTH_TYPE(Enum):
        BASIC = auto()
        APIC = auto()
        OAUTH = auto()
        ZEN_IAM = auto()
        ZEN_API = auto()

    def initialize_apic(self, user_id: str, api_key: str) -> None:
        """initialize class with apic auth information
        Args:
            userId (str): user id fetched from API Key Gen
            apiKey (str): api key fetched from API Key Gen
        """
        self.headers = {
            "X-IBM-Client-Id": user_id,
            "X-IBM-Client-Secret": api_key,
        }
        logger.info("GraphQL Connection initialized with APIC")
        logger.debug(
            "GraphQL Connection initialized with APIC with headers: %s", self.headers
        )
        self._auth_type = self.AUTH_TYPE.APIC

    def initialize_oauth(
        self,
        oauth_url: str,
        oauth_ssl_enabled: bool,
        grant_type: str,
        scope: str,
        username: str = None,
        password: str = None,
        client_id: str = None,
        client_secret: str = None,
    ) -> None:
        """initialize connection with oauth information
        Args:

            oauth_url (str): oauth/IAM url
            oauth_ssl_enabled (bool): whether checking for server certificate is enforced
            username (str): username
            password (str): password
            grant_type (str): oauth's grant type
            scope (str): oauth's scope
            client_id (str): oauth client id
            client_secret (str): oauth client secret
        """
        self.token_url = oauth_url
        self.token_ssl_enabled = oauth_ssl_enabled
        self.payload = {
            "grant_type": grant_type,
            "scope": scope,
        }
        self.headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if (username and password) and (
            username != "REPLACE" and password != "REPLACE"
        ):
            self.payload["username"] = username
            self.payload["password"] = password

        if (client_id and client_secret) and (
            client_id != "REPLACE" and client_secret != "REPLACE"
        ):
            self.auth_user = client_id
            self.auth_pass = client_secret
        logger.info("GraphQL Connection initialized with OAuth")
        logger.debug(
            "GraphQL Connection initialized with OAuth with Headers: %s Payload: %s",
            self.headers,
            self.payload,
        )
        self._auth_type = self.AUTH_TYPE.OAUTH

    def initialize_zen_iam(
        self,
        zen_exchange_url: str,
        iam_url: str,
        iam_ssl_enabled: bool,
        iam_grant_type: str,
        iam_scope: str,
        iam_username: str = None,
        iam_password: str = None,
        iam_client_id: str = None,
        iam_client_secret: str = None,
        zen_exchange_ssl: Union[str, bool] = True,
    ):
        """initialize connection with zen iam information
        Args:

            zen_exchange_url (str): url to exchange iam token for zen token
            iam_url (str): url to IAM route
                iam_ssl_enabled (bool): whether SSL check for server cert is enforced on IAM route
            iam_username (str): username
            iam_password (str): password
            iam_grant_type (str): oauth's grant type
            iam_scope (str): oauth's scope
            iam_client_id (str): oauth client id
            iam_client_secret (str): oauth client secret
        """
        self.initialize_oauth(
            oauth_url=iam_url,
            oauth_ssl_enabled=iam_ssl_enabled,
            grant_type=iam_grant_type,
            scope=iam_scope,
            username=iam_username,
            password=iam_password,
            client_id=iam_client_id,
            client_secret=iam_client_secret,
        )
        self.zen_exchange_url = zen_exchange_url
        logger.info("GraphQL Connection initialized with Zen IAM")
        logger.debug(
            "GraphQL Connection initialized with Zen IAM with Zen URL: %s",
            zen_exchange_url,
        )
        self._auth_type = self.AUTH_TYPE.ZEN_IAM
        self.zen_exchange_ssl = zen_exchange_ssl

    def initialize_zen_api(
        self,
        username: str = None,
        apikey: str = None,
    ):
        """initialize connection with zen api information
        Args:
            username (str): username
            apikey (str): apikey
        """
        data = {"username": username, "api_key": apikey}
        self.payload = json.dumps(data).encode("utf-8")
        logger.info("GraphQL Connection initialized with Zen API")
        self.headers = {
            "Content-Type": "application/json",
        }
        self._auth_type = self.AUTH_TYPE.ZEN_API

    def initialize_basic(self, username: str, password: str) -> None:
        """inititialize class with basic auth information
        Args:
            username (str): username
            password (str): password
        """
        self.xsrf_token = str(uuid.uuid4())
        self.auth_user = username
        self.auth_pass = password
        logger.info("GraphQL Connection initialized with Basic auth")
        self._auth_type = self.AUTH_TYPE.BASIC

    def get_token(self) -> None:
        """Execute request to get token after initialized with authentication information.
        Only call this method if using token based authentication.
        """
        self.xsrf_token = str(uuid.uuid4())
        operation = "POST" if self.payload else "GET"
        auth = (
            (self.auth_user, self.auth_pass)
            if (self.auth_user and self.auth_pass)
            else None
        )
        response = requests.request(
            operation,
            self.token_url,
            headers=self.headers,
            data=self.payload,
            timeout=300,
            verify=self.token_ssl_enabled,
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
                raise CSDeployException(
                    "Neither token nor access token is present in response"
                )
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
            raise CSDeployException(
                "Token Failed to fetch with status code: {response.status_code}"
            ) from exception

    def _exchange_iam_token(self) -> None:
        """Execute request to get Zen Token from IAM Token"""
        headers = {"username": self.payload["username"], "iam-token": self.token}
        response = requests.request(
            "GET",
            self.zen_exchange_url,
            headers=headers,
            timeout=300,
            verify=self.zen_exchange_ssl,
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
                logger.error("Response Text: %s, response.text")
            raise CSDeployException(
                "Request failed with status code: " + str(response.status_code)
            ) from exception


class GraphqlRequest:
    """Class used to execute graphql queries and mutations"""

    def __init__(
        self, gql_connection: GraphqlConnection, audit_logger: AuditLogger = None
    ) -> None:
        self.gql_connection = gql_connection
        self.audit_logger = audit_logger

    def execute_request(
        self,
        query: str,
        variables=None,
        log_operation: _GraphqlLogOperation = None,
        file_map: dict[str, str] = None,
    ):
        """Send Post request to graphql endpoint

        Args:
            query (str): query being sent
            variables (_type_, optional): variables to be sent with query. Defaults to None.
            log_operation (str, optional): name of current operation for audit logger
            file_map (dict[str,str], optional): a dictionary with mapping of variable name of content
                as keys and file path as value.
        Returns:
            _type_: _description_
        """
        headers = {
            "ECM-CS-XSRF-Token": self.gql_connection.xsrf_token,
        }
        cookies = {"ECM-CS-XSRF-Token": self.gql_connection.xsrf_token}
        logger.info(
            "Executing graphql request to endpoint: %s", self.gql_connection.url
        )

        if self.gql_connection.token:
            if (
                self.gql_connection.token_refresh
                and int(
                    (
                        datetime.now() - self.gql_connection.token_fetched_time
                    ).total_seconds()
                )
                > self.gql_connection.token_refresh
            ):
                self.gql_connection.get_token()
            headers["Authorization"] = "Bearer " + self.gql_connection.token
            auth = None
        elif self.gql_connection.auth_user and self.gql_connection.auth_pass:
            auth = (self.gql_connection.auth_user, self.gql_connection.auth_pass)
        else:
            auth = None
            logger.error("Invalid Authentication method for gqlconnection")

        if file_map:
            files = []
            variables = json.loads(variables) if variables else {}
            for var_name, file_path in file_map.items():
                file = open(file_path, "rb")
                files.append(
                    (
                        var_name,
                        (file.name, file, mimetypes.guess_type(file.name)),
                    )
                )
                if var_name in variables:
                    continue
                else:
                    variables[var_name] = None
            variables_str = str(variables).replace("None", "null").replace("'", '"')

            operations_str = '{"query":"%s","variables":%s}' % (
                query.replace('"', '\\"'),
                variables_str,
            )
            payload = {
                "operations": operations_str,
            }
            logger.debug(
                "GraphQL Request Details: Query: %s, Verify: %s",
                query,
                self.gql_connection.ssl_enabled,
            )
            start_time = datetime.now()
            response = requests.post(
                url=self.gql_connection.url,
                headers=headers,
                data=payload,
                cookies=cookies,
                timeout=300,
                verify=self.gql_connection.ssl_enabled,
                auth=auth,
                files=files,
            )
        else:
            inclvars = variables if variables else {}
            json_payload = {"query": query, "variables": inclvars}
            headers["Content-Type"] = "application/json"
            logger.debug(
                "GraphQL Request Details: Payload: %s, Verify: %s",
                json_payload,
                self.gql_connection.ssl_enabled,
            )
            start_time = datetime.now()
            response = requests.post(
                url=self.gql_connection.url,
                headers=headers,
                json=json_payload,
                cookies=cookies,
                timeout=300,
                verify=self.gql_connection.ssl_enabled,
                auth=auth,
            )

        end_time = datetime.now()
        if self.audit_logger:
            log_entry = _GraphqlRequestEntry(
                operation=log_operation,
                query=query,
                start_time=start_time,
                time_elapsed=(end_time - start_time).total_seconds(),
                response_code=response.status_code,
            )
            self.audit_logger._add(log_entry=log_entry)
        if response.status_code != 200:
            logger.error("Request failed with status code: %s", response.status_code)
            try:
                error_data = response.json()
                logger.error("Response JSON: %s", error_data)
            except ValueError:
                logger.error("Response Text: %s", response.text)
            raise CSDeployException(
                "Request failed with status code: " + str(response.status_code)
            )
        else:
            logger.debug("Response details: Headers=%s", response.headers)
            try:
                logger.debug(
                    "Response details: Response JSON=%s",
                    json.dumps(response.json(), indent=4),
                )
            except ValueError:
                logger.debug("Response details: Text=%s", response.text)
        return response
