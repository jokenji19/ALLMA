
from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.logger import shprint
from pythonforandroid.util import current_directory
from pythonforandroid.toolchain import shprint
import sh
import os

class LlamaCppPythonRecipe(CompiledComponentsPythonRecipe):
    version = '0.3.0'  # Use a recent stable version
    url = 'https://github.com/abetlen/llama-cpp-python/releases/download/v{version}/llama_cpp_python-{version}.tar.gz'
    
    depends = ['python3', 'cmake', 'numpy']
    
    # Critical: Tell the build system this uses scikit-build-core / cmake
    call_hostpython_via_targetpython = False

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        
        # CPU-Only flags for Android compatibility
        # We disable BLAS and Metal to prevent link errors
        env['CMAKE_ARGS'] = (
            f"-DLLAMA_METAL=OFF "
            f"-DLLAMA_BLAS=OFF "
            f"-DLLAMA_K_QUANTS=ON "
            f"-DANDROID_PLATFORM=android-24 "
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ.get('ANDROID_NDK_HOME')}/build/cmake/android.toolchain.cmake "
            f"-DANDROID_ABI={arch.arch}"
        )
        
        # Ensure we use the correct python executable for the build
        env['SKBUILD_CONFIGURE_OPTIONS'] = env['CMAKE_ARGS']
        
        return env

    def build_compiled_components(self, arch):
        # Standard pip install but with our env CMAKE_ARGS
        super().build_compiled_components(arch)

recipe = LlamaCppPythonRecipe()
