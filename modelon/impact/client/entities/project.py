#
# Copyright (c) 2022 Modelon AB
#
import enum
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from modelon.impact.client.sal.project import ProjectService
from modelon.impact.client.options import ExecutionOptions


@enum.unique
class ContentType(enum.Enum):
    """Supported content types in a project."""

    MODELICA = 'MODELICA'
    VIEWS = 'VIEWS'
    FAVOURITES = 'FAVOURITES'
    CUSTOM_FUNCTIONS = 'CUSTOM_FUNCTIONS'
    REFERENCE_RESULTS = 'REFERENCE_RESULTS'
    GENERIC = 'GENERIC'


@dataclass
class Content:
    """Content entry """

    relpath: Path
    #: Relative path in the project. Can be file (e.g., SomeLib.mo) or folder

    content_type: ContentType
    #: type of content

    id: str
    #: ID is stored as a key in project but not here

    name: Optional[str] = None
    #: Modelica library name or eventually other name for display

    default_disabled: bool = False
    #: Content entry gets disabled by default when included into a new workspace.

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get('id'),
            relpath=data.get('relpath'),
            content_type=ContentType(data.get('contentType')),
            name=data.get('name'),
            default_disabled=data.get('defaultDisabled'),
        )


class ProjectContent:
    """Content entry in a project."""

    def __init__(self, content: Content, project_id: str, project_sal: ProjectService):
        self._content = content
        self._project_id = project_id
        self._project_sal = project_sal

    def __repr__(self):
        return f"Project content with id '{self._content.id}'"

    def delete(self):
        """Deletes a project content.

        Example::

            content.delete()
        """
        self._project_sal.project_content_delete(self._project_id, self._content.id)

    def __eq__(self, obj):
        return (
            isinstance(obj, ProjectContent)
            and obj._content == self._content
            and obj._project_id == self._project_id
        )


@dataclass
class ProjectDependency:
    """Dependency entry for a project"""

    name: str
    #: The name of the project dependency

    version_specifier: Optional[str] = None
    #: Version specifier

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get('name'), version_specifier=data.get('versionSpecifier')
        )


@dataclass
class ProjectDefinition:
    """
    Impact project definition.
    """

    name: str

    version: Optional[str]

    format: str

    dependencies: List[ProjectDependency]

    content: List[Content]

    execution_options: List[ExecutionOptions]

    @classmethod
    def from_dict(cls, data):
        dependencies = data.get('dependencies', [])
        contents = data.get('content', [])
        execution_options = data.get('executionOptions', [])
        return cls(
            name=data.get("name"),
            version=data.get('version'),
            format=data.get('format'),
            dependencies=[
                ProjectDependency.from_dict(dependency) for dependency in dependencies
            ],
            content=[Content.from_dict(content) for content in contents],
            execution_options=[
                ExecutionOptions(execution_option, execution_option['customFunction'])
                for execution_option in execution_options
            ],
        )


class Project:
    """
    Class containing Project functionalities.
    """

    def __init__(
        self,
        project_id: str,
        project_definition: ProjectDefinition,
        project_service: ProjectService,
    ):
        self._project_id = project_id
        self._project_definition = project_definition
        self._project_sal = project_service

    def __repr__(self):
        return f"Project with id '{self._project_id}'"

    def __eq__(self, obj):
        return (
            isinstance(obj, Project)
            and obj._project_id == self._project_id
            and obj._project_definition == self._project_definition
        )

    @property
    def id(self) -> str:
        """Project id"""
        return self._project_id

    def delete(self):
        """Deletes a project.

        Example::

            project.delete()
        """
        self._project_sal.project_delete(self._project_id)

    def _get_project_content(self, content):
        return ProjectContent(content, self._project_id, self._project_sal)

    def _refresh(self):
        self._project_definition = ProjectDefinition.from_dict(
            self._project_sal.project_get(self._project_id)['definition']
        )

    def get_contents(
        self, content_type_filter: Optional[ContentType] = None
    ) -> List[ProjectContent]:
        """Get project contents.

        Example::

            project.get_contents(ContentType.MODELICA)
        """
        self._refresh()
        contents = self._project_definition.content
        if content_type_filter:
            return [
                self._get_project_content(content)
                for content in contents
                if content_type_filter == content.content_type
            ]
        return [self._get_project_content(content) for content in contents]

    def upload_content(
        self, path_to_content: str, content_type: ContentType
    ) -> ProjectContent:
        """Upload content to a project.

        Parameters:

            path_to_content --
                The path for the content to be imported.

            content_type --
                The type of the imported content.

        Example::
            from modelon.impact.client import ContentType

            project.upload_content('/home/test.mo', ContentType.MODELICA)
        """
        resp = self._project_sal.project_content_upload(
            path_to_content, self._project_id, content_type.value
        )
        content = Content.from_dict(resp)
        return self._get_project_content(content)

    def upload_modelica_library(self, path_to_lib: str):
        """Uploads/adds a non-encrypted modelica library or a modelica model to the project.

        Parameters:

            path_to_lib --
                The path for the library to be imported. Only '.mo' or '.zip' file
                extension are supported for upload.

        Example::

            project.upload_model_library('C:/A.mo')
            project.upload_model_library('C:/B.zip')
        """
        if Path(path_to_lib).suffix.lower() == '.mol':
            raise ValueError(
                "Only '.mo' or '.zip' file extension are supported for upload."
            )
        return self.upload_content(path_to_lib, ContentType.MODELICA)
