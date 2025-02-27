import pytest
import unittest.mock as mock
from modelon.impact.client import exceptions

from modelon.impact.client.entities.experiment import ExperimentStatus
from tests.impact.client.helpers import (
    create_case_entity,
    create_experiment_entity,
    create_experiment_operation,
)
from tests.impact.client.fixtures import *


class TestExperiment:
    def test_execute(self, experiment):
        exp = experiment.entity.execute()
        assert exp == create_experiment_operation('AwesomeWorkspace', 'pid_2009')

    def test_execute_with_case_filter(self, batch_experiment_with_case_filter):
        experiment = batch_experiment_with_case_filter.entity
        exp_sal = batch_experiment_with_case_filter.service
        case_generated = experiment.execute(with_cases=[]).wait()
        exp_sal.experiment_execute.assert_has_calls(
            [mock.call('Workspace', 'Experiment', [])]
        )
        exp_sal.case_put.assert_not_called()

        case_to_execute = case_generated.get_cases()[2]
        result = experiment.execute(with_cases=[case_to_execute]).wait()
        exp_sal.experiment_execute.assert_has_calls(
            [mock.call('Workspace', 'Experiment', ["case_3"])]
        )
        exp_sal.case_put.assert_has_calls(
            [mock.call('Workspace', 'Experiment', "case_3", mock.ANY)]
        )

        assert result == create_experiment_entity('AwesomeWorkspace', 'Experiment')
        assert result.run_info.successful == 1
        assert result.run_info.not_started == 3
        assert experiment.get_case('case_3').is_successful()

    def test_get_cases_label(self, batch_experiment_with_case_filter):
        experiment = batch_experiment_with_case_filter.entity
        cases = experiment.get_cases_with_label('Cruise operating point')
        assert cases == [
            create_case_entity("case_2", "Workspace", "Test"),
            create_case_entity("case_4", "Workspace", "Test"),
        ]

    def test_execute_with_case_filter_no_sync(self, batch_experiment_with_case_filter):
        experiment = batch_experiment_with_case_filter.entity
        exp_sal = batch_experiment_with_case_filter.service
        case_generated = experiment.execute(with_cases=[]).wait()
        case_to_execute = case_generated.get_cases()[2]
        experiment.execute(with_cases=[case_to_execute], sync_case_changes=False).wait()
        exp_sal.experiment_execute.assert_has_calls(
            [mock.call('Workspace', 'Experiment', ["case_3"])]
        )
        exp_sal.case_put.assert_not_called()

    def test_execute_successful(self, experiment):
        experiment = experiment.entity
        assert experiment.id == "Test"
        assert experiment.is_successful()
        assert experiment.run_info.status == ExperimentStatus.DONE
        assert experiment.run_info.errors == []
        assert experiment.run_info.failed == 0
        assert experiment.run_info.successful == 1
        assert experiment.run_info.cancelled == 0
        assert experiment.run_info.not_started == 0
        assert experiment.get_variables() == ["inertia.I", "time"]
        assert experiment.get_cases() == [
            create_case_entity("case_1", "Workspace", "Test")
        ]
        assert experiment.get_case("case_1") == create_case_entity(
            "case_1", "Workspace", "Test"
        )

        exp = experiment.get_trajectories(['inertia.I', 'time'])
        assert exp['case_1']['inertia.I'] == [1, 2, 3, 4]
        assert exp['case_1']['time'] == [5, 2, 9, 4]

    def test_successful_batch_execute(self, batch_experiment):
        assert batch_experiment.is_successful()
        assert batch_experiment.run_info.status == ExperimentStatus.DONE
        assert batch_experiment.run_info.failed == 0
        assert batch_experiment.run_info.successful == 2
        assert batch_experiment.run_info.cancelled == 0
        assert batch_experiment.run_info.not_started == 0
        assert batch_experiment.get_variables() == ["inertia.I", "time"]
        assert batch_experiment.get_cases() == [
            create_case_entity("case_1", "Workspace", "Experiment"),
            create_case_entity("case_2", "Workspace", "Experiment"),
        ]
        exp = batch_experiment.get_trajectories(['inertia.I'])
        assert exp['case_1']['inertia.I'] == [1, 2, 3, 4]
        assert exp['case_2']['inertia.I'] == [14, 4, 4, 74]

    def test_some_successful_batch_execute(self, batch_experiment_some_successful):
        assert not batch_experiment_some_successful.is_successful()
        assert batch_experiment_some_successful.run_info.status == ExperimentStatus.DONE
        assert batch_experiment_some_successful.run_info.failed == 1
        assert batch_experiment_some_successful.run_info.successful == 2
        assert batch_experiment_some_successful.run_info.cancelled == 0
        assert batch_experiment_some_successful.run_info.not_started == 1
        assert batch_experiment_some_successful.get_cases() == [
            create_case_entity("case_1", "Workspace", "Experiment"),
            create_case_entity("case_2", "Workspace", "Experiment"),
            create_case_entity("case_3", "Workspace", "Experiment"),
            create_case_entity("case_4", "Workspace", "Experiment"),
        ]

    def test_running_execution(self, running_experiment):
        assert running_experiment.run_info.status == ExperimentStatus.NOTSTARTED
        assert not running_experiment.is_successful()
        pytest.raises(
            exceptions.OperationNotCompleteError, running_experiment.get_variables
        )
        pytest.raises(
            exceptions.OperationNotCompleteError,
            running_experiment.get_trajectories,
            ['inertia.I'],
        )

    def test_failed_execution(self, failed_experiment):
        assert failed_experiment.run_info.status == ExperimentStatus.FAILED
        assert not failed_experiment.is_successful()
        assert failed_experiment.run_info.errors == [
            'out of licenses',
            'too large experiment',
        ]

    def test_execution_with_failed_cases(self, experiment_with_failed_case):
        assert experiment_with_failed_case.run_info.status == ExperimentStatus.DONE
        assert experiment_with_failed_case.get_cases() == [
            create_case_entity("case_1", "Workspace", "Experiment")
        ]
        assert experiment_with_failed_case.get_case("case_1") == create_case_entity(
            "case_1", "Workspace", "Experiment"
        )
        assert not experiment_with_failed_case.is_successful()
        assert experiment_with_failed_case.get_trajectories(['inertia.I']) == {
            'case_1': {'inertia.I': [1, 2, 3, 4]}
        }

    def test_cancelled_execution(self, cancelled_experiment):
        assert cancelled_experiment.run_info.status == ExperimentStatus.CANCELLED
        assert cancelled_experiment.get_cases() == [
            create_case_entity("case_1", "Workspace", "Test")
        ]
        assert cancelled_experiment.get_case("case_1") == create_case_entity(
            "case_1", "Workspace", "Experiment"
        )

        assert not cancelled_experiment.is_successful()
        pytest.raises(
            exceptions.OperationFailureError, cancelled_experiment.get_variables
        )
        pytest.raises(
            exceptions.OperationFailureError,
            cancelled_experiment.get_trajectories,
            ['inertia.I'],
        )

    def test_exp_trajectories_non_list_entry(self, experiment):
        pytest.raises(TypeError, experiment.entity.get_trajectories, 'hh')

    def test_exp_trajectories_invalid_keys(self, experiment):
        pytest.raises(ValueError, experiment.entity.get_trajectories, ['s'])

    def test_execute_with_user_data(self, workspace):
        user_data = {"workspaceExecuteKey": "workspaceExecuteValue"}
        workspace.entity.execute({}, user_data).wait()

        workspace.service.experiment_create.assert_has_calls(
            [mock.call('AwesomeWorkspace', {}, user_data)]
        )

