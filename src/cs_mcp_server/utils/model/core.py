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

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


NULL_VALUE = object()


class Document(BaseModel):
    """Document class for the MCP server."""

    className: str = Field(
        default="Document", description="Class identifier for the document"
    )
    id: str = Field(description="The id of the document")
    name: Optional[str] = Field(default=None, description="The name of the document")
    properties: Optional[List[dict]] = Field(
        default=None, description="Document properties"
    )
    creator: Optional[str] = Field(
        default=None, description="The creator of the document"
    )
    dateCreated: Optional[datetime] = Field(
        default=None, description="Date when document was created"
    )
    lastModifier: Optional[str] = Field(
        default=None, description="The last modifier of the document"
    )
    dateLastModified: Optional[datetime] = Field(
        default=None, description="Date when document was last modified"
    )
    owner: Optional[str] = Field(default=None, description="The owner of the document")
    mimeType: Optional[str] = Field(
        default=None, description="MIME type of the document"
    )
    contentSize: Optional[float] = Field(
        default=None, description="Size of the document content"
    )
    isVersioningEnabled: Optional[bool] = Field(
        default=None, description="Whether versioning is enabled"
    )
    majorVersionNumber: Optional[int] = Field(
        default=None, description="Major version number"
    )
    minorVersionNumber: Optional[int] = Field(
        default=None, description="Minor version number"
    )

    # Commented out fields that will be implemented later
    """
    creatorUser: Optional[dict] = Field(default=None, description="User who created the document")
    lastModifierUser: Optional[dict] = Field(default=None, description="User who last modified the document")
    ownerPrincipal: Optional[dict] = Field(default=None, description="Security principal who owns the document")
    permissions: Optional[List[dict]] = Field(default=None, description="Document permissions")
    containers: Optional[dict] = Field(default=None, description="Container relationships")
    annotations: Optional[dict] = Field(default=None, description="Document annotations")
    lockToken: Optional[str] = Field(default=None, description="Lock token")
    lockTimeout: Optional[int] = Field(default=None, description="Lock timeout")
    lockOwner: Optional[str] = Field(default=None, description="Lock owner")
    foldersFiledIn: Optional[dict] = Field(default=None, description="Folders the document is filed in")
    securityFolder: Optional[dict] = Field(default=None, description="Security folder")
    isReserved: Optional[bool] = Field(default=None, description="Whether document is reserved")
    isCurrentVersion: Optional[bool] = Field(default=None, description="Whether document is current version")
    isFrozenVersion: Optional[bool] = Field(default=None, description="Whether document version is frozen")
    versionSeries: Optional[dict] = Field(default=None, description="Version series")
    versions: Optional[dict] = Field(default=None, description="Document versions")
    currentVersion: Optional[dict] = Field(default=None, description="Current version")
    reservation: Optional[dict] = Field(default=None, description="Reservation")
    versionStatus: Optional[str] = Field(default=None, description="Version status")
    reservationType: Optional[str] = Field(default=None, description="Reservation type")
    releasedVersion: Optional[dict] = Field(default=None, description="Released version")
    dateCheckedIn: Optional[datetime] = Field(default=None, description="Date checked in")
    cmIsMarkedForDeletion: Optional[bool] = Field(default=None, description="Whether marked for deletion")
    objectReference: Optional[dict] = Field(default=None, description="Object reference")
    updateSequenceNumber: Optional[int] = Field(default=None, description="Update sequence number")
    accessAllowed: Optional[int] = Field(default=None, description="Access allowed")
    contentElementsPresent: Optional[List[str]] = Field(default=None, description="Content elements present")
    contentElements: Optional[List[dict]] = Field(default=None, description="Content elements")
    dateContentLastAccessed: Optional[datetime] = Field(default=None, description="Date content last accessed")
    contentRetentionDate: Optional[datetime] = Field(default=None, description="Content retention date")
    currentState: Optional[str] = Field(default=None, description="Current state")
    isInExceptionState: Optional[bool] = Field(default=None, description="Whether in exception state")
    classificationStatus: Optional[str] = Field(default=None, description="Classification status")
    indexationId: Optional[str] = Field(default=None, description="Indexation ID")
    cmIndexingFailureCode: Optional[int] = Field(default=None, description="Indexing failure code")
    compoundDocumentState: Optional[str] = Field(default=None, description="Compound document state")
    childDocuments: Optional[dict] = Field(default=None, description="Child documents")
    parentDocuments: Optional[dict] = Field(default=None, description="Parent documents")
    cmRetentionDate: Optional[datetime] = Field(default=None, description="Retention date")
    cmThumbnails: Optional[dict] = Field(default=None, description="Thumbnails")
    """

    @classmethod
    def create_an_instance(
        cls, graphQL_changed_object_dict: dict, class_identifier: str = "Document"
    ):
        """Create a Document instance from a GraphQL Document"""
        document_data = {"className": class_identifier, "id": None, "properties": []}

        if "id" in graphQL_changed_object_dict:
            document_data["id"] = graphQL_changed_object_dict["id"]

        if "properties" in graphQL_changed_object_dict:
            properties = graphQL_changed_object_dict["properties"]
            document_data["properties"] = properties

            for prop in properties:
                if prop["id"] == "DocumentTitle":
                    document_data["name"] = prop["value"]
                elif prop["id"] == "Creator":
                    document_data["creator"] = prop["value"]
                elif prop["id"] == "DateCreated" and prop["value"]:
                    document_data["dateCreated"] = prop["value"]
                elif prop["id"] == "LastModifier":
                    document_data["lastModifier"] = prop["value"]
                elif prop["id"] == "DateLastModified" and prop["value"]:
                    document_data["dateLastModified"] = prop["value"]
                elif prop["id"] == "Owner":
                    document_data["owner"] = prop["value"]
                elif prop["id"] == "MimeType":
                    document_data["mimeType"] = prop["value"]
                elif prop["id"] == "ContentSize":
                    document_data["contentSize"] = (
                        float(prop["value"]) if prop["value"] else None
                    )
                elif prop["id"] == "MajorVersionNumber":
                    document_data["majorVersionNumber"] = (
                        int(prop["value"]) if prop["value"] else None
                    )
                elif prop["id"] == "MinorVersionNumber":
                    document_data["minorVersionNumber"] = (
                        int(prop["value"]) if prop["value"] else None
                    )
                elif prop["id"] == "IsVersioningEnabled":
                    document_data["isVersioningEnabled"] = (
                        prop["value"] == "true" if prop["value"] else None
                    )

        return cls(**document_data)


class Folder(BaseModel):
    """Folder class for the MCP server."""

    class_identifier: str = Field(
        default="Folder", description="Class identifier for the folder"
    )
    id: str = Field(description="The id of the folder")
    name: Optional[str] = Field(default=None, description="The name of the folder")
    parent_folder_id: Optional[str] = Field(
        default=None, description="The id of the parent folder"
    )
    creator: Optional[str] = Field(
        default=None, description="The creator of the folder"
    )
    properties: Optional[List[dict]] = Field(
        default=None, description="Folder properties"
    )
    dateCreated: Optional[datetime] = Field(
        default=None, description="Date when folder was created"
    )
    lastModifier: Optional[str] = Field(
        default=None, description="The last modifier of the folder"
    )
    dateLastModified: Optional[datetime] = Field(
        default=None, description="Date when folder was last modified"
    )
    owner: Optional[str] = Field(default=None, description="The owner of the folder")

    @classmethod
    def create_an_instance(
        cls, graphQL_changed_object_dict: dict, class_identifier: str = "Folder"
    ):
        "create a Folder instance from a GraphQL Folder"
        folder_data = {"className": class_identifier, "id": None, "properties": []}

        if "id" in graphQL_changed_object_dict:
            folder_data["id"] = graphQL_changed_object_dict["id"]

        if "properties" in graphQL_changed_object_dict:
            properties = graphQL_changed_object_dict["properties"]
            folder_data["properties"] = properties

            for prop in properties:
                if prop["id"] == "FolderName":
                    folder_data["name"] = prop["value"]
                elif prop["id"] == "Parent":
                    folder_data["parent_folder_id"] = prop["value"]["identifier"]
                elif prop["id"] == "Creator":
                    folder_data["creator"] = prop["value"]
                elif prop["id"] == "DateCreated" and prop["value"]:
                    folder_data["dateCreated"] = prop["value"]
                elif prop["id"] == "LastModifier":
                    folder_data["lastModifier"] = prop["value"]
                elif prop["id"] == "DateLastModified" and prop["value"]:
                    folder_data["dateLastModified"] = prop["value"]
                elif prop["id"] == "Owner":
                    folder_data["owner"] = prop["value"]

        return cls(**folder_data)


class DocumentMatch(BaseModel):
    """Information about a document that matches a search."""

    class_name: str = Field(
        default="Document", description="Class identifier for the document"
    )
    id: str = Field(description="The id of the document")
    name: Optional[str] = Field(default=None, description="The name of the document")
    score: float = Field(
        description="The match score, higher values indicate better matches"
    )


class DocumentFilingMatch(BaseModel):
    """Information about a document where it is filed in a folder that matches a search."""

    containment_id: str = Field(
        description="The id of the containment relationship where the document is filed"
    )
    containment_name: str = Field(
        description="The containment name of the document where filed in the folder"
    )
    containment_path: str = Field(
        description="The containment path of the document where filed in the folder"
    )
    document_class_name: str = Field(
        default="Document",
        description="Class identifier for the document that is filed",
    )
    document_id: str = Field(
        description="The id of the document that is filed in the folder"
    )
    document_name: str = Field(
        description="The name of the document that is filed in the folder"
    )
    folder_id: str = Field(
        description="The id of the folder where the document is filed"
    )
    folder_name: str = Field(
        description="The name of the folder where the document is filed"
    )
    folder_path: str = Field(
        description="The path of the folder where the document is filed"
    )
    score: float = Field(
        description="The match score, higher values indicate better matches"
    )


class Annotation(BaseModel):
    """Pydantic Annotation class for the MCP server."""

    class_name: Optional[str] = Field(
        default="Annotation", description="Class name of the annotation"
    )
    creator: Optional[str] = Field(
        default=None, description="The creator of the annotation"
    )
    date_created: Optional[datetime] = Field(
        default=None, description="Creation timestamp"
    )
    date_last_modified: Optional[datetime] = Field(
        default=None, description="Last modification timestamp"
    )
    id: str = Field(description="The id of the annotation")
    name: Optional[str] = Field(default=None, description="The name of the annotation")
    owner: Optional[str] = Field(
        default=None, description="The owner of the annotation"
    )
    descriptive_text: Optional[str] = Field(
        default=None, description="The descriptive text of the annotation"
    )
    content_size: Optional[int] = Field(
        default=None, description="The size of the annotation content"
    )
    mime_type: Optional[str] = Field(
        default=None, description="The mimetype of the content"
    )
    annotated_content_element: Optional[str] = Field(
        default=None, description="Content element being annotated"
    )
    content_elements_present: Optional[List[str]] = Field(
        None, description="Whether content elements are present"
    )
    content_elements: Optional[List[dict]] = Field(
        default=None,
        description="List of content elements with className, contentType, and sequence",
    )

    @classmethod
    def create_an_instance(
        cls, graphQL_changed_object_dict: dict, class_name: str = "Annotation"
    ):
        """Create a Annotation instance from a GraphQL Annotation"""

        annotation_data = {"className": class_name, "id": None}

        # for now, define a mapping of field names returned from the GraphQL API to the field names in the pydantic model
        # instead of write some method to transform field names. Reason: Decoupling. Pydantic model is returned to LLM and test, so
        # in case GraghQL API changes, we don't want to change the pydantic model and upstream test.
        graphQL_to_pydantic_field_name_map: dict[str, str] = {
            "id": "id",
            "creator": "creator",
            "dateCreated": "date_created",
            "dateLastModified": "date_last_modified",
            "name": "name",
            "owner": "owner",
            "descriptiveText": "descriptive_text",
            "contentSize": "content_size",
            "mimeType": "mime_type",
            "annotatedContenttElement": "annotated_content_element",
            "contentElementsPresent": "content_elements_present",
            "contentElemnents": "content_elements",
        }
        required_fields = ["id"]

        for name in graphQL_to_pydantic_field_name_map:
            if name in graphQL_changed_object_dict:
                annotation_data[graphQL_to_pydantic_field_name_map[name]] = (
                    graphQL_changed_object_dict[name]
                )
            elif name in required_fields:
                raise ValueError(
                    f"Annotation: Missing required property '{name}' in GraphQL response"
                )

        # TODO: Content Elements is a list of dictionary.. Might need to define structure for return
        return cls(**annotation_data)
