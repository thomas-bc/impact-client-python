"""This module provides an entry-point to the client APIs."""
import logging
from typing import List, Optional
from dataclasses import dataclass
from semantic_version import SimpleSpec, Version  # type: ignore
import modelon.impact.client.configuration
from modelon.impact.client.entities.project import Project, ProjectDefinition, VcsUri
from modelon.impact.client.entities.workspace import (
    WorkspaceDefinition,
    Workspace,
    VcsReference,
)
import modelon.impact.client.exceptions
import modelon.impact.client.sal.service
import modelon.impact.client.sal.exceptions
import modelon.impact.client.credential_manager
import modelon.impact.client.jupyterhub
from modelon.impact.client.operations.workspace import WorkspaceImportOperation
from modelon.impact.client.sal.uri import URI
from modelon.impact.client import exceptions


logger = logging.getLogger(__name__)


def _workspace_def_from_dict(data):
    return WorkspaceDefinition.from_dict(data)


def _project_def_from_dict(data):
    return ProjectDefinition.from_dict(data)


def _get_vcs_uri_from_reference_id(
    shared_definition: WorkspaceDefinition, reference_id: str
):
    projects = shared_definition.projects + shared_definition.dependencies
    for project in projects:
        if (
            isinstance(project.reference, VcsReference)
            and project.reference.id == reference_id
        ):
            return project.reference.vcsUri
    raise ValueError(
        f"The {reference_id} doesn't exist in workspace projects or dependencies!"
    )


@dataclass
class Selection:
    entry_id: str
    project: Project

    def to_dict(self):
        return {'id': self.entry_id, 'project': {'id': self.project.id}}


@dataclass
class ProjectMatching:
    entry_id: str
    vcs_uri: str
    projects: List[Project]

    def get_selection(self, index: int) -> Selection:
        return Selection(entry_id=self.entry_id, project=self.projects[index])

    def make_selection_interactive(self) -> Selection:
        if len(self.projects) == 1:
            print(f"Only one project matches the URI {self.vcs_uri}!")
            chosen_project = self.projects[0]
            project_def = chosen_project.definition
            print(
                f"Resolving conflict automatically using project with ID: "
                f"{chosen_project.id} for repository with URI: {self.vcs_uri}."
            )
            return Selection(self.entry_id, chosen_project)

        print(f"Multiple existing projects match the URI {self.vcs_uri}!")
        hash_map = {}
        for i, project in enumerate(self.projects):
            hash_map[i + 1] = project
            project_def = project.definition
            print(f"{i+1}. {project_def.name} {project.vcs_uri}")
        try:
            chosen_project = hash_map[
                int(input('Please enter one of the above choices:-'))
            ]
        except (KeyError, ValueError) as e:
            allowed_choices = map(str, range(len(hash_map)))
            raise ValueError(
                f"Invalid choice. Please select one of {','.join(allowed_choices)}!"
            ) from e

        print(
            f"Resolving conflict using project with ID: {chosen_project.id}"
            f" for repository with URI: {self.vcs_uri}."
        )
        return Selection(self.entry_id, chosen_project)


@dataclass
class ProjectMatchings:
    entries: List[ProjectMatching]

    def make_selections_interactive(self) -> List[Selection]:
        selections = []
        for entry in self.entries:
            selections.append(entry.make_selection_interactive())
        return selections


class Client:
    """This Class contains methods to authenticate logins, create new workspaces and
    upload or fetch existing workspaces.

    Parameters:

        url --
            The URL for Modelon Impact client host. Defaults to the value specified
            by env variable 'MODELON_IMPACT_CLIENT_URL' if set else uses the URL
            'http://localhost:8080/'.

        interactive --
            If True the client will prompt for an API key if no other login information
            can be found. An API key entered for this prompt will be saved to disk
            and re-used next time the Client is instantiated. If False no prompt will
            be given if no other login information can be found and login will be done
            as if no API key was given (anonymous login).

            For scripts and notebooks that are running interactively by a user in
            a shell it is recommended to use interactive=True. For scripts or
            applications that are automated or for other reasons won't have a user
            ready to enter an API key it is recommended to use interactive=False.

            Default is False. It is possible to change the default value through
            the environment variable 'MODELON_IMPACT_CLIENT_INTERACTIVE'.

        credential_manager --
            Help class for managing credentials for the Impact server. Default is None
            and then the default credential manager is used.

        context --
            Request contexts to pass data alongside a HTTP request. Default is None and
            then the default context is used.

    Examples::
        from modelon.impact.client import Client

        client = Client(url=impact_url)
        client = Client(url=impact_url, interactive=True)
    """

    _SUPPORTED_VERSION_RANGE = ">=1.21.3,<4.0.0"

    def __init__(
        self,
        url=None,
        interactive=None,
        credential_manager=None,
        context=None,
        jupyterhub_credential_manager=None,
    ):
        if url is None:
            url = modelon.impact.client.configuration.get_client_url()

        if interactive is None:
            interactive = modelon.impact.client.configuration.get_client_interactive()

        if credential_manager is None:
            credential_manager = (
                modelon.impact.client.credential_manager.CredentialManager()
            )

        self._uri = URI(url)
        self._sal = modelon.impact.client.sal.service.Service(self._uri, context)
        self._credential_manager = credential_manager

        try:
            self._validate_compatible_api_version()
        except modelon.impact.client.sal.exceptions.AccessingJupyterHubError:
            self._uri, context = modelon.impact.client.jupyterhub.authorize(
                self._uri, interactive, context, jupyterhub_credential_manager,
            )
            self._sal = modelon.impact.client.sal.service.Service(self._uri, context)
            self._validate_compatible_api_version()

        try:
            api_key = self._authenticate_against_api(interactive)
        except modelon.impact.client.sal.exceptions.HTTPError:
            if interactive:
                logger.warning(
                    "The provided Modelon Impact API key is not valid, "
                    "please enter a new key"
                )
                api_key = self._credential_manager.get_key_from_prompt()
                api_key = self._authenticate_against_api(interactive, api_key=api_key)
            else:
                raise

        self._sal.add_login_retry_with(api_key)

        resp = self._sal.users.get_me()
        if 'license' not in resp['data']:
            raise exceptions.NoAssignedLicenseError(
                "No assigned license during login. Either out of floating Deployment "
                "Add-on licenses or your assigned user license could not be validated"
            )

    def _validate_compatible_api_version(self):
        try:
            version = self._sal.api_get_metadata()["version"]
        except modelon.impact.client.sal.exceptions.CommunicationError as exce:
            raise modelon.impact.client.sal.exceptions.NoResponseFetchVersionError(
                f"No response from url {self._uri}, "
                "please verify that the URL is correct"
            ) from exce

        if Version(version) not in SimpleSpec(self._SUPPORTED_VERSION_RANGE):
            raise exceptions.UnsupportedSemanticVersionError(
                f"Version '{version}' of the HTTP REST API is not supported, "
                f"must be in the range '{self._SUPPORTED_VERSION_RANGE}'! "
                "Updgrade or downgrade this package to a version "
                f"that supports version '{version}' of the HTTP REST API."
            )

    def _authenticate_against_api(self, interactive, api_key=None):
        if not api_key:
            api_key = self._credential_manager.get_key(interactive=interactive)

        if not api_key:
            logger.warning(
                "No Modelon Impact API key could be found, "
                "will log in as anonymous user. Permissions may be limited"
            )

        self._sal.api_login(api_key=api_key)
        if api_key and interactive:
            # Save the api_key for next time if
            # running interactively and login was successfuly
            self._credential_manager.write_key_to_file(api_key)

        return api_key

    def get_workspace(self, workspace_id):
        """
        Returns a Workspace class object.

        Parameters:

            workspace_id --
                The name of the workspace.

        Returns:

            workspace --
                Workspace class object.

        Example::

            client.get_workspace('my_workspace')
        """
        resp = self._sal.workspace.workspace_get(workspace_id)
        return Workspace(
            resp["id"],
            _workspace_def_from_dict(resp),
            self._sal.workspace,
            self._sal.model_executable,
            self._sal.experiment,
            self._sal.custom_function,
            self._sal.project,
        )

    def get_workspaces(self):
        """
        Returns a list of Workspace class object.

        Returns:

            workspace --
                A list of Workspace class objects.

        Example::

            client.get_workspaces()
        """
        resp = self._sal.workspace.workspaces_get()
        return [
            Workspace(
                item["id"],
                _workspace_def_from_dict(item),
                self._sal.workspace,
                self._sal.model_executable,
                self._sal.experiment,
                self._sal.custom_function,
                self._sal.project,
            )
            for item in resp["data"]["items"]
        ]

    def get_projects(self):
        """
        Returns a list of project class object.

        Returns:

            project --
                A list of Project class objects.

        Example::

            client.get_projects()
        """
        resp = self._sal.project.projects_get()
        return [
            Project(
                item["id"],
                _project_def_from_dict(item),
                item["projectType"],
                VcsUri.from_dict(item["vcsUri"]) if item.get("vcsUri") else None,
                self._sal.project,
            )
            for item in resp["data"]["items"]
        ]

    def create_workspace(self, workspace_id):
        """Creates and returns a Workspace.
        Returns a workspace class object.

        Parameters:

            workspace_id --
                The name of the workspace to create.

        Returns:

            workspace --
                The created workspace class object.

        Example::

            client.create_workspace('my_workspace')
        """
        resp = self._sal.workspace.workspace_create(workspace_id)
        return Workspace(
            resp["id"],
            _workspace_def_from_dict(resp),
            self._sal.workspace,
            self._sal.model_executable,
            self._sal.experiment,
            self._sal.custom_function,
            self._sal.project,
        )

    def upload_workspace(self, path_to_workspace):
        """Uploads a Workspace
        Returns the workspace class object of the imported workspace.

        Parameters:

            path_to_workspace --
                The path for the compressed workspace(.zip) to be uploaded.

        Returns:

            workspace --
                Workspace class object.

        Example::

            client.upload_workspace(path_to_workspace)
        """
        resp = self._sal.workspace.workspace_upload(path_to_workspace)
        return Workspace(
            resp["id"],
            _workspace_def_from_dict(resp),
            self._sal.workspace,
            self._sal.model_executable,
            self._sal.experiment,
            self._sal.custom_function,
            self._sal.project,
        )

    def _get_versioned_projects_from_ids(
        self, vcs_project_ids: List[str]
    ) -> List[Project]:
        projects = self.get_projects()
        return [project for project in projects if project.id in vcs_project_ids]

    def _import_from_shared_definition(
        self,
        shared_definition: WorkspaceDefinition,
        selections: Optional[List[Selection]] = None,
    ):
        resp = self._sal.workspace.import_from_shared_definition(
            shared_definition.to_dict(),
            selected_matchings=[selection.to_dict() for selection in selections]
            if selections
            else None,
        )
        return WorkspaceImportOperation(
            resp["data"]["location"],
            shared_definition,
            self._sal.workspace,
            self._sal.model_executable,
            self._sal.experiment,
            self._sal.custom_function,
            self._sal.project,
        )

    def import_from_shared_definition(
        self,
        shared_definition: WorkspaceDefinition,
        selections: Optional[List[Selection]] = None,
    ):
        operation = self._import_from_shared_definition(shared_definition, selections)
        return operation.wait()

    def get_project_matchings(
        self, shared_definition: WorkspaceDefinition
    ) -> ProjectMatchings:
        project_matchings = []
        matchings = self._sal.workspace.get_project_matchings(
            shared_definition.to_dict()
        )['data']['vcs']
        for entry in matchings:
            project_ids = [project['id'] for project in entry['projects']]
            vcs_uri = _get_vcs_uri_from_reference_id(
                shared_definition, entry["entryId"]
            )
            projects = self._get_versioned_projects_from_ids(
                vcs_project_ids=project_ids
            )
            project_matchings.append(
                ProjectMatching(entry["entryId"], vcs_uri, projects)
            )
        return ProjectMatchings(project_matchings)
