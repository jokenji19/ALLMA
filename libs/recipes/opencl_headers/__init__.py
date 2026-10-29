"""Pinned build headers only; no runtime library is installed."""
from pythonforandroid.recipe import Recipe


class OpenCLHeadersRecipe(Recipe):
    name = 'opencl_headers'
    version = '2025.07.22'
    url = 'https://github.com/KhronosGroup/OpenCL-Headers/archive/refs/tags/v{version}.tar.gz'
    sha512sum = 'e8a338e501783d778ced2e5d0cf5ed735a2372ba9bbd809cc6a1f2d6c7c0d16ded731272fbb5ffe4fd7ce37aa5d739d898869843149f861937aa35890b23c69a'


recipe = OpenCLHeadersRecipe()
