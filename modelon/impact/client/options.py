from copy import deepcopy
from collections.abc import Mapping
from typing import Union, List, Dict, Any
from abc import ABC, abstractmethod


def _set_options(options, **modified):
    opts = deepcopy(options)
    for name, value in modified.items():
        opts[name] = value
    return opts


class ExecutionOptions(Mapping, ABC):
    """
    Base class for the simulation, compiler, solver and runtime options settings.
    """

    def __init__(
        self,
        workspace_id: str,
        values: Dict[str, Any],
        custom_function_name: str,
        custom_function_service=None,
    ):
        self._workspace_id = workspace_id
        self._values = values
        self._custom_function_name = custom_function_name
        self._custom_func_sal = custom_function_service

    def __repr__(self):
        return f"{self.name} option for '{self._custom_function_name}'"

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return self._values.__iter__()

    def __len__(self):
        return self._values.__len__()

    @property
    @abstractmethod
    def name(self):
        """
        Returns the option name.
        """

    @abstractmethod
    def data(self, values):
        """
        Returns the option class with values.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """

    def with_values(self, **modified):
        """Sets/updates the options.

        Parameters:

            parameters --
                A keyworded, variable-length argument list of options.

        Example::

            cmp_opts = custom_function.get_compiler_options().with_values(
                c_compiler='gcc')
            runtime_opts = custom_function.get_runtime_options().with_values(
                cs_solver=0)
            sol_opts = custom_function.get_solver_options().with_values(rtol=1e-7)
            sim_opts = custom_function.get_simulation_options().with_values(ncp=500)
        """
        values = _set_options(self._values, **modified,)
        return self.data(values)

    def with_defaults(self):
        """Sets/overrides the options with default options.

        Parameters:

            parameters --
                A keyworded, variable-length argument list of options.

        Example::

            cmp_opts = custom_function.get_compiler_options().with_defaults()
            runtime_opts = custom_function.get_runtime_options().with_defaults()
            sol_opts = custom_function.get_solver_options().with_defaults()
            sim_opts = custom_function.get_simulation_options().with_defaults()
        """
        default_opts = self._custom_func_sal.custom_function_default_options_get(
            self._workspace_id, self._custom_function_name
        )[self.name]
        return self.with_values(**default_opts)


class CompilerOptions(ExecutionOptions):
    @property
    def name(self):
        return "compiler"

    def data(self, values):
        """Returns a new CompilerOptions class instance.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """
        return CompilerOptions(
            self._workspace_id,
            values,
            self._custom_function_name,
            self._custom_func_sal,
        )


class RuntimeOptions(ExecutionOptions):
    @property
    def name(self):
        return "runtime"

    def data(self, values):
        """Returns a new RuntimeOptions class instance.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """
        return RuntimeOptions(
            self._workspace_id,
            values,
            self._custom_function_name,
            self._custom_func_sal,
        )


class SimulationOptions(ExecutionOptions):
    @property
    def name(self):
        return "simulation"

    def data(self, values):
        """Returns a new SimulationOptions class instance.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """
        return SimulationOptions(
            self._workspace_id,
            values,
            self._custom_function_name,
            self._custom_func_sal,
        )

    def with_result_filter(self, pattern: Union[str, List[str]]):
        """Sets the variable filter for results.

        Parameters:

            parameters --
                A keyworded, variable-length argument list of options.

        Example::

            sim_opts = custom_function.get_simulation_options().with_result_filter(
                pattern = ["*.phi"])
        """
        if not isinstance(pattern, str):
            pattern = str(pattern)
        return self.with_values(**{'filter': pattern})


class SolverOptions(ExecutionOptions):
    @property
    def name(self):
        return "solver"

    def data(self, values):
        """Returns a new SolverOptions class instance.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """
        return SolverOptions(
            self._workspace_id,
            values,
            self._custom_function_name,
            self._custom_func_sal,
        )
