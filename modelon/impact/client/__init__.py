import logging
import modelon.impact.client.entities
import modelon.impact.client.sal.service
from semantic_version import SimpleSpec, Version  # type: ignore
import modelon.impact.client.exceptions as exceptions
import modelon.impact.client.sal.exceptions
import modelon.impact.client.credential_manager

logger = logging.getLogger(__name__)


class Client:
    _SUPPORTED_VERSION_RANGE = ">=1.2.1,<2.0.0"

    def __init__(
        self,
        url=None,
        interactive=False,
        api_key=None,
        credentail_manager=None,
        context=None,
    ):
        if url is None:
            url = "http://localhost:8080/"
            logger.warning("No URL for client was specified, will use: {}".format(url))

        if credentail_manager is None:
            credentail_manager = (
                modelon.impact.client.credential_manager.CredentialManager()
            )

        self.api_key = api_key
        self.uri = modelon.impact.client.sal.service.URI(url)
        self._sal = modelon.impact.client.sal.service.Service(self.uri, context)
        self._credentials = credentail_manager

        self._validate_compatible_api_version()
        self._authenticate_against_api(interactive)

    def _validate_compatible_api_version(self):
        try:
            version = self._sal.api_get_metadata()["version"]
        except modelon.impact.client.sal.exceptions.CommunicationError as exce:
            raise modelon.impact.client.sal.exceptions.NoResponseFetchVersionError(
                f"No response from url {self.uri}, "
                "please verify that the URL is correct"
            ) from exce

        if Version(version) not in SimpleSpec(self._SUPPORTED_VERSION_RANGE):
            raise exceptions.UnsupportedSemanticVersionError(
                f"Version '{version}' of the HTTP REST API is not supported, "
                f"must be in the range '{self._SUPPORTED_VERSION_RANGE}'! "
                "Updgrade or downgrade this package to a version "
                f"that supports version '{version}' of the HTTP REST API."
            )

    def _authenticate_against_api(self, interactive):
        if self.api_key is None:
            self.api_key = self._credentials.get_key(interactive=interactive)

        if self.api_key is None:
            logger.warning(
                "No API key could be found, will log in as anonymous user. "
                "Permissions may be limited"
            )
            login_data = {}
        else:
            login_data = {"secret_key": self.api_key}

        self._sal.api_login(login_data)
        if interactive:
            # Save the api_key for next time if
            # running interactively and login was successfuly
            self._credentials.write_key_to_file(self.api_key)

    def get_workspace(self, workspace_id):
        resp = self._sal.workspace.workspace_get(workspace_id)
        return modelon.impact.client.entities.Workspace(
            resp["id"],
            self._sal.workspace,
            self._sal.model_executable,
            self._sal.experiment,
            self._sal.custom_function,
        )

    def get_workspaces(self):
        resp = self._sal.workspace.workspaces_get()
        return [
            modelon.impact.client.entities.Workspace(
                item["id"],
                self._sal.workspace,
                self._sal.model_executable,
                self._sal.experiment,
                self._sal.custom_function,
            )
            for item in resp["data"]["items"]
        ]

    def create_workspace(self, workspace_id):
        resp = self._sal.workspace.workspace_create(workspace_id)
        return modelon.impact.client.entities.Workspace(
            resp["id"],
            self._sal.workspace,
            self._sal.model_executable,
            self._sal.experiment,
            self._sal.custom_function,
        )

    def upload_workspace(self, workspace_id, path_to_workspace):
        resp = self._sal.workspace.workspace_upload(workspace_id, path_to_workspace)
        return modelon.impact.client.entities.Workspace(
            resp["id"],
            self._sal.workspace,
            self._sal.model_executable,
            self._sal.experiment,
            self._sal.custom_function,
        )
