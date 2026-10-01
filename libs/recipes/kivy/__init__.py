"""Preserve p4a's host stdlib while building without a nested PEP 517 venv."""
from pathlib import Path
from pythonforandroid.recipes import kivy as upstream


import importlib.util
from pathlib import Path
_support_spec = importlib.util.spec_from_file_location(
    '_allma_host_build', Path(__file__).parents[1] / 'host_build_support.py')
_support = importlib.util.module_from_spec(_support_spec)
_support_spec.loader.exec_module(_support)


class KivyRecipe(_support.HostBuildPrerequisites, upstream.KivyRecipe):
    # Match Kivy 2.3.1's declared PEP 517 requirements exactly.
    hostpython_prerequisites = [
        'Cython>=0.29.1,<=3.0.11', 'packaging~=24.0',
        'setuptools~=69.2.0', 'wheel~=0.44.0',
    ]
    extra_build_args = [*upstream.KivyRecipe.extra_build_args, '--no-isolation']

    def get_recipe_dir(self):
        # Keep using upstream patches and included source files.
        return str(Path(upstream.__file__).parent)


recipe = KivyRecipe()
