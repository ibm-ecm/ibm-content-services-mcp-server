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

from enum import Enum

from pydantic import BaseModel, Field


class HoldableRootClassEnum(str, Enum):
    Document = "Document"
    Annotation = "Annotation"
    Folder = "Folder"
    CustomObject = "CustomObject"


class HoldRelationship(BaseModel):
    """
    A hold relationship class
    """

    hold_relationship_id: str = Field(
        description="The id of the hold relationship object."
    )
    held_id: str = Field(description="The id of the held object.")

    held_root_class: HoldableRootClassEnum = Field(
        description="The symbolic name of the root class of the held object."
    )

    hold_id: str = Field(description="The id of the hold object.")
    creator: str = Field(description="The creator of this hold relationship object.")
    last_modifier: str = Field(
        description="The last modifier of this hold relationship object."
    )

    @classmethod
    def create_an_instance(cls, graphQL_changed_object_dict: dict):
        properties = graphQL_changed_object_dict["properties"]
        for prop in properties:
            if prop["id"] == "HeldObject":
                held_id = prop["value"]["identifier"]
                held_root_class = prop["value"]["classIdentifier"]
            if prop["id"] == "Hold":
                hold_id = prop["value"]["identifier"]
            if prop["id"] == "Id":
                hold_relationship_id = prop["value"]
            if prop["id"] == "Creator":
                creator = prop["value"]
            if prop["id"] == "LastModifier":
                last_modifier = prop["value"]
        return cls(
            hold_id=hold_id,
            held_id=held_id,
            held_root_class=held_root_class,
            hold_relationship_id=hold_relationship_id,
            creator=creator,
            last_modifier=last_modifier,
        )
