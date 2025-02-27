import os
import tempfile
import unittest.mock as mock

from tests.files.paths import SINGLE_FILE_LIBRARY_PATH
from tests.impact.client.helpers import (
    create_experiment_entity,
    create_model_entity,
    create_model_exe_entity,
    create_workspace_entity,
    create_experiment_operation,
)
from tests.impact.client.fixtures import *


class TestWorkspace:
    def test_get_custom_function(self, workspace):
        custom_function = workspace.entity.get_custom_function('dynamic')
        assert 'dynamic' == custom_function.name

    def test_get_custom_functions(self, workspace):
        custom_function_list = [
            custom_function.name
            for custom_function in workspace.entity.get_custom_functions()
        ]
        assert ['dynamic'] == custom_function_list

    def test_delete(self):
        workspace_sal = mock.MagicMock()
        workspace = create_workspace_entity("toDeleteWorkspace", workspace_sal)
        workspace.delete()
        workspace_sal.workspace_delete.assert_called_with("toDeleteWorkspace")

    def test_import_library(self):
        workspace_sal = mock.MagicMock()
        workspace = create_workspace_entity("importLibraryWorkspace", workspace_sal,)

        workspace.upload_model_library(SINGLE_FILE_LIBRARY_PATH)
        workspace_sal.library_import.assert_called_with(
            "importLibraryWorkspace", SINGLE_FILE_LIBRARY_PATH
        )

    def test_import_fmu(self):
        workspace_sal = mock.MagicMock()
        workspace = create_workspace_entity("importFMUWorkspace", workspace_sal)
        workspace.upload_fmu("test.fmu", "Workspace")
        workspace_sal.fmu_import.assert_called_with(
            "importFMUWorkspace",
            "test.fmu",
            "Workspace",
            None,
            False,
            None,
            None,
            None,
            step_size=0.0,
        )

    def test_upload_result(self, workspace_sal_upload_base):
        workspace_service = workspace_sal_upload_base
        workspace = create_workspace_entity('uploadResultWorksapce', workspace_service,)
        upload_op = workspace.upload_result("test.mat", "Workspace")
        workspace_service.result_upload.assert_called_with(
            'uploadResultWorksapce', 'test.mat', description=None, label='Workspace'
        )
        assert upload_op.id == "2f036b9fab6f45c788cc466da327cc78workspace"

    def test_download_workspace(self, workspace):
        t = os.path.join(tempfile.gettempdir(), workspace.entity.id + '.zip')
        resp = workspace.entity.download({}, tempfile.gettempdir())
        assert resp == t

    def test_clone(self, workspace):
        clone = workspace.entity.clone()
        assert clone == create_workspace_entity('MyClonedWorkspace')

    def test_get_custom_function_from_clone(self, workspace):
        clone = workspace.entity.clone()
        custom_function = clone.get_custom_function('dynamic')
        assert 'dynamic' == custom_function.name

    def test_get_model(self, workspace):
        model = workspace.entity.get_model("Modelica.Blocks.PID")
        assert model == create_model_entity("Modelica.Blocks.PID", workspace.entity.id)

    def test_model_repr(self, workspace):
        model = create_model_entity("Modelica.Blocks.PID", workspace.entity.id)
        assert "Class name 'Modelica.Blocks.PID'" == model.__repr__()

    def test_get_fmus(self, workspace):
        fmus = workspace.entity.get_fmus()
        assert fmus == [
            create_model_exe_entity('AwesomeWorkspace', 'as9f-3df5'),
            create_model_exe_entity('AwesomeWorkspace', 'as9D-4df5'),
        ]

    def test_get_fmu(self, workspace):
        fmu = workspace.entity.get_fmu('pid_20090615_134')
        assert fmu == create_model_exe_entity('AwesomeWorkspace', 'pid_20090615_134')

    def test_get_experiment(self, workspace):
        exp = workspace.entity.get_experiment('pid_20090615_134')
        assert exp == create_experiment_entity('AwesomeWorkspace', 'pid_20090615_134')

    def test_get_experiments(self, workspace):
        exps = workspace.entity.get_experiments()
        assert exps == [
            create_experiment_entity('AwesomeWorkspace', 'as9f-3df5'),
            create_experiment_entity('AwesomeWorkspace', 'dd9f-3df5'),
        ]

    def test_create_experiment(self, workspace):
        exp = workspace.entity.create_experiment({})
        assert exp == create_experiment_entity('AwesomeWorkspace', 'pid_2009')

    def test_create_experiment_with_user_data(self, workspace):
        user_data = {"customWsGetKey": "customWsGetValue"}
        exp = workspace.entity.create_experiment({}, user_data)

        workspace.service.experiment_create.assert_has_calls(
            [mock.call('AwesomeWorkspace', {}, user_data)]
        )

    def test_execute_options_dict(self, workspace):
        exp = workspace.entity.execute({})
        assert exp == create_experiment_operation('AwesomeWorkspace', 'pid_2009')
