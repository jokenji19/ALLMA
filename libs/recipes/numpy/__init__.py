"""Build NumPy in p4a's prepared host environment.

An isolated PEP 517 venv created from p4a's relocated host interpreter can
lose its native stdlib extension path (including math) on macOS. p4a already
provides a dedicated host Python; install the backend there and preserve that
cross-compilation environment instead of nesting another virtualenv.
"""
from pythonforandroid.recipes.numpy import NumpyRecipe as UpstreamNumpyRecipe


import importlib.util
from pathlib import Path
_support_spec = importlib.util.spec_from_file_location(
    '_allma_host_build', Path(__file__).parents[1] / 'host_build_support.py')
_support = importlib.util.module_from_spec(_support_spec)
_support_spec.loader.exec_module(_support)


class NumpyRecipe(_support.HostBuildPrerequisites, UpstreamNumpyRecipe):
    hostpython_prerequisites = [
        *UpstreamNumpyRecipe.hostpython_prerequisites,
        'meson-python>=0.15.0',
    ]
    extra_build_args = [*UpstreamNumpyRecipe.extra_build_args, '--no-isolation']


recipe = NumpyRecipe()
