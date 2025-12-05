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

"""Module contains audit logging classes"""

import datetime
from abc import abstractmethod
from collections import deque
from enum import Enum, auto


class _GraphqlLogOperation(Enum):
    """Enum for audit log operation names

    Args:
        Enum (_type_): enum representing operation name
    """

    EXPORT_QUERY = auto()
    DISCOVERY_QUERY = auto()
    IMPORT_MUTATION = auto()
    METADATA_QUERY = auto()
    REFERENCED_OBJECT_RETRIEVAL = auto()
    UPDATE_OOO_PROPERTIES = auto()
    UTIL_QUERY_ALL = auto()


class _AuditLogEntryInterface:
    """Audit log entry"""

    @abstractmethod
    def _to_json(self) -> dict:
        """Converts current log entry into a json(dict)

        Returns:
            dict: json object being returned
        """
        pass

    @abstractmethod
    def _to_string(self) -> str:
        """Converts current log entry into string

        Returns:
            str: string representation of log entry
        """
        pass


class _GraphqlRequestEntry(_AuditLogEntryInterface):
    """Audit log entry for GraphQL requests"""

    def __init__(
        self,
        operation: _GraphqlLogOperation = None,
        start_time: datetime = None,
        time_elapsed: int = None,
        query: str = None,
        response_code: int = None,
    ) -> None:
        self.operation = operation
        self.start_time = start_time
        self.time_elapsed = time_elapsed
        self.query = query
        self.response_code = response_code

    def _to_json(self):
        operation_str = self.operation.name if self.operation else None
        return {
            "start_time": self.start_time,
            "operation": operation_str,
            "time_elapsed": self.time_elapsed,
            "query": self.query,
            "response_code": self.response_code,
        }

    def _to_string(self) -> str:
        operation_str = self.operation.name if self.operation else None
        return (
            f"[{self.start_time}]{operation_str} - "
            f"Time Elapsed: {self.time_elapsed} seconds - "
            f"Response Code: {self.response_code} - Query: {self.query}"
        )


class AuditLogger:
    """Audit loger object recording all requests"""

    def __init__(
        self,
        logs: list[_AuditLogEntryInterface] = None,
        max_entries: int = 50,
        file_path=None,
        write_on_add: bool = False,
    ) -> None:
        """Audit Logger constructor

        Args:
            logs (list[AuditLogEntryInterface], optional): list of existing logs. Defaults to None.
            max_entries (int, optional): max entries kept in memory. Defaults to 50.
            file_path (_type_, optional): write path for audit log file. Defaults to None.
            write_on_add (bool, optional): if true, logs will write to file on add, else only
            when max_entries is reached. Defaults to False for optimization
        """
        self.logs = deque(logs) if logs else deque()
        self.max_entries = max_entries
        self.file_path = file_path
        self.write_on_add = write_on_add

    def _add(self, log_entry: _AuditLogEntryInterface):
        """Add log to list of logs, write to file if
        log count exceed max entriesfile path is specifiecd

        Args:
            log (AuditLogEntry): log to be added
        """

        if self.write_on_add:
            if len(self.logs) >= self.max_entries:
                self.logs.popleft()
            self._write_entry(log_entry)
        else:
            if len(self.logs) >= self.max_entries:
                self.write()
        self.logs.append(log_entry)

    def _write_entry(self, log: _AuditLogEntryInterface) -> None:
        """Write single entry without evicting entry from memory

        Args:
            ofile (_type_, optional): _description_. Defaults to None.
        """
        if not self.file_path:
            return

        with open(self.file_path, "a", encoding="utf-8") as file:
            file.write(log._to_string() + "\n")

    def write(self) -> None:
        """Write all entries to file and evict the entries

        Args:
            ofile (_type_): overwrite AutditLogger's output file path
        """
        if not self.file_path:
            return
        with open(self.file_path, "a", encoding="utf-8") as file:
            while self.logs:
                log = self.logs.popleft()
                file.write(log._to_string() + "\n")
