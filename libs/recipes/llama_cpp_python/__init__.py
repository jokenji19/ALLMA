from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory, shprint
import sh
import os

class LlamaCppPythonRecipe(CompiledComponentsPythonRecipe):
    version = '0.2.26'
    url = 'https://github.com/abetlen/llama-cpp-python/archive/refs/tags/v{version}.tar.gz'
    
    depends = ['setuptools', 'numpy']
    
    # Non usiamo hostpython per la compilazione C++
    call_hostpython_via_targetpython = False

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        
        # CMAKE ARGS specifici per Android
        # -DANDROID_ABI è gestito automaticamente da p4a solitamente, ma forziamo
        # Disabilitiamo chiamate di sistema non supportate o non necessarie
        env['CMAKE_ARGS'] = (
            f"-DCMAKE_TOOLCHAIN_FILE={os.environ['ANDROID_NDK_HOME']}/build/cmake/android.toolchain.cmake "
            f"-DANDROID_ABI={arch.arch} "
            f"-DANDROID_PLATFORM=android-21 "
            "-DLLAMA_CUBLAS=OFF "  # Niente CUDA su Android standard
            "-DLLAMA_OPENBLAS=OFF " # OpenBLAS può essere problematico, meglio default
            "-DLLAMA_BUILD_SERVER=OFF " # Non serve il server web
            "-DLLAMA_NATIVE=OFF " # Evita ottimizzazioni CPU specifiche dell'host che rompono cross-compile
            "-DCMAKE_C_FLAGS='-Wno-unused-command-line-argument' "
            "-DCMAKE_CXX_FLAGS='-Wno-unused-command-line-argument' "
        )
        
        # Override flags per sicurezza
        env['CFLAGS'] = f"-target {arch.target} -fPIC"
        env['CXXFLAGS'] = f"-target {arch.target} -fPIC"
        env['LDFLAGS'] = f"-target {arch.target}"
        
        # Variabili ambiente specifiche per llama.cpp build system
        env['LLAMA_NATIVE'] = 'OFF'
        env['LLAMA_OPENBLAS'] = 'OFF'
        
        # Forza l'uso di CMAKE
        env['LLAMA_CPP_LIB_PRELOAD'] = '1'
        return env

recipe = LlamaCppPythonRecipe()
