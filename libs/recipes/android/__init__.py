"""Preserve p4a's host stdlib while building without a nested PEP 517 venv."""
from pathlib import Path
from pythonforandroid.recipes import android as upstream


import importlib.util
from pathlib import Path
_support_spec = importlib.util.spec_from_file_location(
    '_allma_host_build', Path(__file__).parents[1] / 'host_build_support.py')
_support = importlib.util.module_from_spec(_support_spec)
_support_spec.loader.exec_module(_support)


class AndroidRecipe(_support.HostBuildPrerequisites, upstream.AndroidRecipe):
    hostpython_prerequisites = [*upstream.AndroidRecipe.hostpython_prerequisites, 'wheel']
    extra_build_args = [*upstream.AndroidRecipe.extra_build_args, '--no-isolation']

    def get_recipe_dir(self):
        # Keep using upstream patches and included source files.
        return str(Path(upstream.__file__).parent)


recipe = AndroidRecipe()
