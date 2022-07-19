from copy import deepcopy
from collections.abc import Mapping
from typing import Union, List, Dict, Any
from abc import ABC, abstractmethod


def _set_options(options, **modified):
    opts = deepcopy(options)
    for name, value in modified.items():
        opts[name] = value
    return opts


class BaseExecutionOptions(Mapping, ABC):
    """
    Base class for the simulation, compiler, solver and runtime options settings.
    """

    def __init__(
        self, values: Dict[str, Any], custom_function_name: str,
    ):
        self._values = values
        self._custom_function_name = custom_function_name

    def __repr__(self):
        return f"{type(self).__name__} for '{self._custom_function_name}'"

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return self._values.__iter__()

    def __len__(self):
        return self._values.__len__()

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
        values = _set_options(self._values, **modified)
        return self.data(values)


class CompilerOptions(BaseExecutionOptions):
    def data(self, values):
        """Returns a new CompilerOptions class instance.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """
        return CompilerOptions(values, self._custom_function_name)


class RuntimeOptions(BaseExecutionOptions):
    def data(self, values):
        """Returns a new RuntimeOptions class instance.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """
        return RuntimeOptions(values, self._custom_function_name)


class SimulationOptions(BaseExecutionOptions):
    def data(self, values):
        """Returns a new SimulationOptions class instance.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """
        return SimulationOptions(values, self._custom_function_name,)

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


class SolverOptions(BaseExecutionOptions):
    def data(self, values):
        """Returns a new SolverOptions class instance.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """
        return SolverOptions(values, self._custom_function_name)


class ExecutionOptions(BaseExecutionOptions):
    def data(self, values):
        """Returns a new ExecutionOptions class instance.

        Parameters:

            values --
                A keyworded, variable-length argument list of options.
        """
        return ExecutionOptions(values, self._custom_function_name)
