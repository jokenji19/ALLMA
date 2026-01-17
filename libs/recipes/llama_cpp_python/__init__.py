from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory, shprint
import sh
import os
import logging

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
        
        # Copilot Solution: set GGML flags to override default
        env['GGML_CMAKE_CFLAGS'] = ""
        env['GGML_CMAKE_CXXFLAGS'] = ""
        
        # Duplicate args for scikit-build specific env var
        env['SKBUILD_CMAKE_ARGS'] = env['CMAKE_ARGS']
        
        # Forza l'uso di CMAKE
        env['LLAMA_CPP_LIB_PRELOAD'] = '1'
        return env

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        # Nuclear Option V2: Broad Search & Destroy
        build_dir = self.get_build_dir(arch.arch)
        logging.info(f"Scanning {build_dir} for -march=native...")
        
        count = 0
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    # Check if file is text/cmake/params
                    if file.endswith('.txt') or file.endswith('.cmake') or file.endswith('.make'):
                        # Read file to check for string (avoid grep dependency issues)
                        with open(filepath, 'r', errors='ignore') as f:
                            content = f.read()
                        
                        if "-march=native" in content:
                            logging.info(f"Found poison in {file}. Sanitizing...")
                            # Replace string
                            sh.sed("-i", "s/-march=native//g", filepath)
                            count += 1
                except Exception as e:
                    pass # Ignore binary read errors
                    
        logging.info(f"Sanitization complete. Patched {count} files.")

recipe = LlamaCppPythonRecipe()
