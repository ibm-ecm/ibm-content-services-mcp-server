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

import logging
import mimetypes
import os
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from cs_mcp_server.utils.model.core import NULL_VALUE
from pydantic import BaseModel, Field


class ContentElementType(str, Enum):
    """Enum for content element types."""

    CONTENT_REFERENCE = "CONTENT_REFERENCE"
    CONTENT_TRANSFER = "CONTENT_TRANSFER"


class CustomInputBase(BaseModel):
    """Base class for input models with property transformation capabilities."""

    # Internal field for content elements
    _contentElements: Optional["ContentElementListInput"] = None

    def add_content_elements(self, content_elements: "ContentElementListInput") -> None:
        """
        Add content elements to the input model.

        Args:
            content_elements: The content elements to add
        """
        self._contentElements = content_elements

    def get_content_elements(self) -> Optional["ContentElementListInput"]:
        """
        Get the content elements for the input model.

        Returns:
            The content elements, or None if not set
        """
        return self._contentElements

    def transform_properties_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """
        Transform a model to a dictionary with properties in the format:
        [{"identifier": "value"}]

        This is particularly useful for models with properties represented as
        a list of PropertyIdentifierAndScalarValue objects.

        Args:
            exclude_none: Whether to exclude None values from the output

        Returns:
            A dictionary with transformed properties
        """
        logger = logging.getLogger(__name__)
        # First get the standard dictionary representation
        base_dict = self.model_dump(exclude_none=exclude_none)

        # If there are no properties, return the original dict
        if "properties" not in base_dict or not base_dict["properties"]:
            pass  # Continue processing even if there are no properties
        else:
            # Transform the properties list
            transformed_properties = []
            for prop in base_dict["properties"]:
                if "identifier" in prop and "value" in prop:
                    # Create a new dict with property_identifier as key and value as value
                    val = prop["value"]
                    if prop["value"] is NULL_VALUE:
                        logger.debug(" None found in property value")
                        val = None
                    transformed_properties.append({prop["identifier"]: val})
                    logger.debug("transformed_properties: %s", transformed_properties)
            # Replace the properties in the base dict
            base_dict["properties"] = transformed_properties

        # Handle DocumentPropertiesInput with _contentElements
        if (
            hasattr(self, "_contentElements")
            and getattr(self, "_contentElements") is not None
        ):
            content_elements = getattr(self, "_contentElements")
            base_dict["contentElements"] = content_elements.model_dump(
                exclude_none=True
            )

        return base_dict

    def process_file_content(
        self,
        file_paths_list: List[str],
    ) -> Dict[str, str]:
        """
        Process file content and prepare document properties and file paths dictionary.
        This method is used by document operations that handle file uploads.

        Args:
            file_paths_list: List of file paths to process

        Returns:
            Dictionary mapping variable names to file paths

        Raises:
            ValueError: If a file path doesn't exist or is invalid
        """
        logger = logging.getLogger(__name__)

        # Create ContentElementListInput with replace action
        content_elements = ContentElementListInput()
        content_elements.replace = []

        # Set up file_paths dictionary for the execute method
        file_paths_dict = {}

        # Check if file_paths_list is empty
        if not file_paths_list:
            raise ValueError("No file paths provided")

        # Filter out non-existent files and collect invalid files
        invalid_files = []
        valid_file_paths = []
        for path in file_paths_list:
            if not path:
                invalid_files.append(f"Empty file path")
                continue
            if not os.path.exists(path):
                invalid_files.append(f"File not found: {path}")
                continue
            if not os.path.isfile(path):
                invalid_files.append(f"Not a file: {path}")
                continue
            valid_file_paths.append(path)

        # Raise error if any invalid files were found
        if invalid_files:
            error_message = "Invalid file(s): " + "; ".join(invalid_files)
            logger.error(error_message)
            raise ValueError(error_message)

        # Raise error if no valid files remain
        if not valid_file_paths:
            error_message = "No valid files to process"
            logger.error(error_message)
            raise ValueError(error_message)

        # Process each file path
        for i, path in enumerate(valid_file_paths):
            # Create a variable name for each file upload
            file_var_name = "contvar" if i == 0 else f"contvar{i+1}"

            # Get mime type for content type
            mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            file_name = os.path.basename(path)

            # Create SubContentTransferInput for this file
            content_transfer = SubContentTransferInput(
                content=file_var_name, retrievalName=file_name
            )

            # Create BaseContentElementInput with ContentTransfer
            content_element = BaseContentElementInput(
                type=ContentElementType.CONTENT_TRANSFER,
                contentType=mime_type,
                subContentTransfer=content_transfer,
                insertAction=InsertDependentActionInput(
                    newIndex=i
                ),  # Use index i instead of hardcoded 0
            )

            # Add to the replace list
            content_elements.replace.append(content_element)

            # Add to file_paths dictionary
            file_paths_dict[file_var_name] = path

        # Add content elements to document properties
        try:
            self.add_content_elements(content_elements)
        except Exception as e:
            logger.error("Error adding content elements: %s", str(e))
            logger.error(traceback.format_exc())

        return file_paths_dict


class SubCheckinActionInput(BaseModel):
    """Input for document check-in action."""

    autoClassify: Optional[bool] = Field(
        default=None,
        description="Whether to automatically classify the document. User must explicitly set this value, else it will be None by default",
    )
    checkinMinorVersion: Optional[bool] = Field(
        default=False,
        description="Whether to check in as a minor version. By default, this is False since we always check in as major version unless specified by the user.",
    )


class PropertyIdentifierAndScalarValue(BaseModel):
    """Represents a property with an identifier and scalar value."""

    identifier: str = Field(description="Property identifier")
    value: Optional[Union[str, int, float, bool, object]] = Field(
        default=None, description="Property value"
    )


class ObjectReferenceInput(BaseModel):
    """Reference to an object in the repository."""

    repositoryIdentifier: Optional[str] = Field(
        default=None, description="Repository identifier"
    )
    classIdentifier: Optional[str] = Field(default=None, description="Class identifier")
    identifier: str = Field(description="Object identifier")


class DependentItemReferenceInput(BaseModel):
    """
    An input type that references an existing object in a list of dependent objects.
    Only one of these fields needs to be specified to reference the existing object.
    """

    id: Optional[str] = Field(
        default=None,
        description="References the existing item by its Id property value",
    )
    identifier: Optional[str] = Field(
        default=None,
        description="References the existing item by some other identifier, for example a symbolic name",
    )
    originalIndex: Optional[int] = Field(
        default=None,
        description="References the existing item by its index in the list",
    )
    sequenceNumber: Optional[int] = Field(
        default=None, description="References the existing item by a sequence number"
    )


class InsertDependentActionInput(BaseModel):
    """Input for inserting a new object in a list of dependent objects."""

    classIdentifier: Optional[str] = Field(
        default=None,
        description="Identifies the class of the new dependent object being inserted",
    )
    newIndex: Optional[int] = Field(
        default=None,
        description="Indicates the index at which to place the new object in the list",
    )


class UpdateDependentActionInput(BaseModel):
    """Input for updating an existing object in a list of dependent objects."""

    itemReference: DependentItemReferenceInput = Field(
        description="References the existing dependent object being updated"
    )


class MoveDependentActionInput(BaseModel):
    """Input for moving an existing object in a list of dependent objects."""

    itemReference: DependentItemReferenceInput = Field(
        description="References the existing dependent object to be moved"
    )
    newIndex: int = Field(
        description="Indicates the new index in the list where the object is being moved"
    )


class DeleteDependentActionInput(BaseModel):
    """Input for deleting an existing object from a list of dependent objects."""

    itemReference: DependentItemReferenceInput = Field(
        description="References the existing dependent object being deleted"
    )


class ContentElementInput(BaseModel):
    """Base class for content element inputs."""

    pass


class ContentReference(ContentElementInput):
    """Reference to content in the repository."""

    pass


class SubContentTransferInput(BaseModel):
    """
    An input type that represents a ContentTransfer.
    Content is matched with a part of a multi-part form submission using a variable and its variable name.
    """

    content: Optional[str] = Field(
        default=None, description="Content variable reference for file upload"
    )
    retrievalName: Optional[str] = Field(
        default=None, description="The retrieval name of the content element"
    )


class SubContentReferenceInput(BaseModel):
    """
    An input type that represents a ContentReference.
    """

    contentLocation: Optional[str] = Field(default=None, description="Content location")


class BaseContentElementInput(BaseModel):
    """
    An input type that represents any type of Content Element (ContentReference or ContentTransfer).

    Only one of the fields -- insertAction, updateAction, moveAction or deleteAction -- can be
    set and indicates the action that this input object represents. If none
    of the fields are set the action defaults to insert.

    When the action is taken on an existing object, for example by specifying the updateAction field, the
    itemReference sub-field must be specified. Content elements can be referenced by the originalIndex sub-field
    of that itemReference object. The sequenceNumber sub-field can also be specified as the ElementSequenceNumber
    property value of the content element.
    """

    type: Optional[ContentElementType] = Field(
        default=None, description="Type of content element"
    )
    insertAction: Optional[InsertDependentActionInput] = Field(
        default=None, description="Action to insert a new content element"
    )
    updateAction: Optional[UpdateDependentActionInput] = Field(
        default=None, description="Action to update an existing content element"
    )
    moveAction: Optional[MoveDependentActionInput] = Field(
        default=None, description="Action to move an existing content element"
    )
    deleteAction: Optional[DeleteDependentActionInput] = Field(
        default=None, description="Action to delete an existing content element"
    )
    contentType: Optional[str] = Field(default=None, description="Content type")
    subContentReference: Optional[SubContentReferenceInput] = Field(
        default=None,
        description="A sub-field to specify fields specific to a ContentReference content element",
    )
    subContentTransfer: Optional[SubContentTransferInput] = Field(
        default=None,
        description="A sub-field to specify fields specific to a ContentTransfer content element",
    )


class ContentElementListInput(BaseModel):
    """
    An input type that represents a list of Content Elements.

    Either the replace field or modify field must be specified. The replace field is equivalent to deleting
    all existing content elements and inserting some number of new content elements.

    Only the insertAction field of each BaseContentElementInput object can be specified if the list
    of objects is passed in the replace field. The insertAction sub-field of those objects is also optional
    as it is the default action. Passing a list of objects to the modify field allows a finer grain
    manipulation of the list of objects.
    """

    replace: Optional[List[BaseContentElementInput]] = Field(
        default=None,
        description="Replace all existing content elements with these new ones",
    )
    modify: Optional[List[BaseContentElementInput]] = Field(
        default=None,
        description="Modify the list of content elements with these actions",
    )


class PermissionInput(BaseModel):
    """Permission input for an object."""

    pass


class PermissionListInput(BaseModel):
    """List of permissions."""

    pass


class ObjectPropertyInput(BaseModel):
    """Object property input."""

    pass


class ReservationType(str, Enum):
    """Specifies the type of reservation created for a checked-out document."""

    COLLABORATIVE = "COLLABORATIVE"
    EXCLUSIVE = "EXCLUSIVE"
    OBJECT_STORE_DEFAULT = "OBJECT_STORE_DEFAULT"


class SubCheckoutActionInput(BaseModel):
    """Input for document check-out action."""

    reservationId: Optional[str] = Field(
        default=None, description="ID for the reservation"
    )
    reservationType: Optional[ReservationType] = Field(
        default=None,
        description="Type of reservation (COLLABORATIVE, EXCLUSIVE, or OBJECT_STORE_DEFAULT)",
    )
    reservationClass: Optional[str] = Field(
        default=None, description="Class for the reservation"
    )
    reservationProperties: Optional[List[PropertyIdentifierAndScalarValue]] = Field(
        default=None, description="Properties for the reservation"
    )
    reservationObjectProperties: Optional[List[ObjectPropertyInput]] = Field(
        default=None, description="Object properties for the reservation"
    )


class DocumentPropertiesInput(CustomInputBase):
    """Input for document properties."""

    properties: Optional[List[PropertyIdentifierAndScalarValue]] = Field(
        default=None, description="Properties for Document"
    )
    name: Optional[str] = Field(
        default=None,
        description="Name sets DocumentTitle or whatever property is configured as the Name property",
    )
    owner: Optional[str] = Field(default=None, description="Owner")
    content: Optional[str] = Field(
        default=None,
        description="Content can be specified if this represents a Reservation document or document creation",
    )
    mimeType: Optional[str] = Field(default=None, description="Mime type")
    compoundDocumentState: Optional[str] = Field(
        default=None, description="Compound document state"
    )
    cmRetentionDate: Optional[datetime] = Field(
        default=None, description="Retention date"
    )
    # contentElements field removed from the model to prevent agents from interpreting and creating this field
    # Instead, we use the methods from CustomInputBase to add content elements programmatically

    # Commented out references to ObjectReferenceInput, PermissionListInput, ObjectPropertyInput
    """
    objectProperties: Optional[List[ObjectPropertyInput]] = Field(
        default=None, description="Object properties"
    )
    replicationGroup: Optional[ObjectReferenceInput] = Field(
        default=None, description="Replication group"
    )
    permissions: Optional[PermissionListInput] = Field(
        default=None, description="Permissions"
    )
    securityPolicy: Optional[ObjectReferenceInput] = Field(
        default=None, description="Security policy"
    )
    securityFolder: Optional[ObjectReferenceInput] = Field(
        default=None, description="Security folder"
    )
    storagePolicy: Optional[ObjectReferenceInput] = Field(
        default=None, description="Storage policy"
    )
    documentLifecyclePolicy: Optional[ObjectReferenceInput] = Field(
        default=None, description="Document lifecycle policy"
    )
    storageArea: Optional[ObjectReferenceInput] = Field(
        default=None, description="Storage area"
    )
    """


class FolderPropertiesInput(CustomInputBase):
    """Input for folder properties."""

    properties: Optional[List[PropertyIdentifierAndScalarValue]] = Field(
        default=None, description="Properties for Folder"
    )
    name: Optional[str] = Field(
        default=None,
        description="Name sets folder name or whatever property is configured as the Name property",
    )
    owner: Optional[str] = Field(default=None, description="Owner")
