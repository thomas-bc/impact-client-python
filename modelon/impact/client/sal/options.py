"""Options service module"""
from modelon.impact.client.sal.http import HTTPClient
from modelon.impact.client.sal.uri import URI


class OptionsService:
    def __init__(self, uri: URI, http_client: HTTPClient):
        self._base_uri = uri
        self._http_client = http_client

    def default_options_get(self, workspace_id: str, custom_function: str):
        url = (
            self._base_uri
            / f"api/workspaces/{workspace_id}/custom-functions/{custom_function}"
            "/default-options"
        ).resolve()
        return self._http_client.get_json(url)

    def custom_function_options_get(self, workspace_id: str, custom_function: str):
        url = (
            self._base_uri
            / f"api/workspaces/{workspace_id}/custom-functions/{custom_function}"
            "/options"
        ).resolve()
        return self._http_client.get_json(url)

    def project_default_options_get(self, workspace_id: str, custom_function: str):
        url = (
            self._base_uri
            / f"api/workspaces/{workspace_id}/custom-functions/{custom_function}"
            "/default-options"
        ).resolve()
        return self._http_client.get_json(url)

    def project_options_get(self, workspace_id: str, custom_function: str):
        url = (
            self._base_uri
            / f"api/workspaces/{workspace_id}/custom-functions/{custom_function}"
            "/options"
        ).resolve()
        return self._http_client.get_json(url)
