#
# Copyright (c) 2022 Modelon AB
#
import enum
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Union
from modelon.impact.client.sal.project import ProjectService
from modelon.impact.client.options import ExecutionOptions

RepoURL = Union['GitRepoURL', 'SvnRepoURL']


@enum.unique
class ContentType(enum.Enum):
    """Supported content types in a project."""

    MODELICA = 'MODELICA'
    VIEWS = 'VIEWS'
    FAVOURITES = 'FAVOURITES'
    CUSTOM_FUNCTIONS = 'CUSTOM_FUNCTIONS'
    REFERENCE_RESULTS = 'REFERENCE_RESULTS'
    GENERIC = 'GENERIC'


@enum.unique
class ProjectType(enum.Enum):
    """Type of project."""

    LOCAL = 'LOCAL'
    RELEASED = 'RELEASED'
    SYSTEM = 'SYSTEM'


@dataclass
class GitRepoURL:
    """GitRepoURL represents a project referenced in a git repo
    String representation is url[@[refname][:sha1]]
    """

    url: str
    """ URL without protocol part, e.g., gitlab.modelon.com/group/project/repo """

    refname: str = ""
    """ Reference name (branch, tag or similar) """

    sha1: str = ""
    """ Commit hash """

    def __str__(self):
        repo_url = self.url
        if self.refname or self.sha1:
            repo_url += '@'
        if self.refname:
            repo_url += self.refname
        if self.sha1:
            repo_url += ':' + self.sha1
        return repo_url

    @classmethod
    def from_dict(cls, data):
        return cls(
            url=data.get("url"), refname=data.get("refname"), sha1=data.get("sha1"),
        )


@dataclass
class SvnRepoURL:
    """SvnRepoURL represents a project referenced in a Subversion repo
    String representation is url/trunk/subdir[@[rev]]
    """

    root_url: str
    """ URL without protocol part up to branch part, e.g., svn.modelon.com/PNNN/ """

    branch: str = ""
    """ Non-empty if it's standard layout and can be either
        trunk or branches/name or tags/name """

    url_from_root: str = ""
    """ URL segment after branch (could be saved in subdir as well) """

    rev: str = ""
    """ Revision number or empty (means HEAD) """

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SvnRepoURL):
            return False
        return (
            self.get_rev() == other.get_rev()
            and self.root_url == other.root_url
            and self.branch == other.branch
            and self.url_from_root == other.url_from_root
        )

    def get_rev(self) -> str:
        rev = self.rev
        if rev == "":
            return 'HEAD'
        return rev

    def __str__(self):
        segments = [self.root_url]
        if self.branch:
            segments.append(self.branch)
        if self.url_from_root:
            segments.append(self.url_from_root)
        repo_url = '/'.join(segments)
        if self.rev:
            repo_url += '@' + self.rev
        return repo_url

    @classmethod
    def from_dict(cls, data):
        return cls(
            root_url=data.get("rootUrl"),
            branch=data.get("branch"),
            url_from_root=data.get("urlFromRoot"),
            rev=data.get("rev"),
        )


@dataclass
class VcsUri:
    service_kind: str
    service_url: str
    repourl: RepoURL
    protocol: str
    subdir: str

    def __str__(self):
        uri = f"{self.service_kind.lower()}+{self.protocol}://{self.repourl}"
        subdir = self.subdir
        if subdir not in ["", "."]:
            uri = uri + "#" + subdir
        return uri

    @classmethod
    def from_dict(cls, data):
        repo_url = data.get("repoUrl")
        service_kind = data.get("serviceKind")
        return cls(
            service_kind=service_kind,
            service_url=data.get("serviceUrl"),
            repourl=GitRepoURL.from_dict(repo_url)
            if service_kind == 'GIT'
            else SvnRepoURL.from_dict(repo_url),
            protocol=data.get("protocol"),
            subdir=data.get("subdir"),
        )


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
        data = data.get('definition')
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
        project_type: ProjectType,
        vcs_uri: Optional[VcsUri],
        project_service: ProjectService,
    ):
        self._project_id = project_id
        self._project_definition = project_definition
        self._vcs_uri = vcs_uri or None
        self._project_type = project_type
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

    @property
    def vcs_uri(self) -> Optional[str]:
        """Project vcs uri"""
        return str(self._vcs_uri) if self._vcs_uri else None

    @property
    def definition(self) -> ProjectDefinition:
        """Project definition"""
        self._refresh()
        return self._project_definition

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
            self._project_sal.project_get(self._project_id)
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
