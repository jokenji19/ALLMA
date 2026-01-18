from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory, shprint
import sh
import os
import logging

class LlamaCppPythonRecipe(CompiledComponentsPythonRecipe):
    version = '0.2.26'
    version = '0.2.26'
    # Use PyPI source because GitHub tarballs often lack submodules (vendor/llama.cpp)
    # causing the patch to miss the files, or the build to fetch fresh (unpatched) code.
    url = 'https://files.pythonhosted.org/packages/source/l/llama_cpp_python/llama_cpp_python-{version}.tar.gz'
    
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
            f"-DCMAKE_SYSTEM_NAME=Android "
            f"-DANDROID_ABI={arch.arch} "
            f"-DANDROID_PLATFORM=android-21 "
            "-DLLAMA_CUBLAS=OFF "  # Niente CUDA su Android standard
            "-DLLAMA_OPENBLAS=OFF " # OpenBLAS può essere problematico, meglio default
            "-DLLAMA_BUILD_SERVER=OFF " # Non serve il server web
            "-DLLAMA_NATIVE=OFF " # Evita ottimizzazioni CPU specifiche dell'host che rompono cross-compile
            "-DCMAKE_C_FLAGS='-march=armv8-a' "
            "-DCMAKE_CXX_FLAGS='-march=armv8-a' "
        )
        
        # Override flags per sicurezza
        
        # KEY FIX: Set these as ENV VARS, which CMake reads as defaults.
        # This overrides internal CMake logic better than command line args sometimes.
        env['CMAKE_C_FLAGS'] = "-march=armv8-a"
        env['CMAKE_CXX_FLAGS'] = "-march=armv8-a"
        
        env['CFLAGS'] = f"-target {arch.target} -fPIC -march=armv8-a"
        env['CXXFLAGS'] = f"-target {arch.target} -fPIC -march=armv8-a"
        env['LDFLAGS'] = f"-target {arch.target}"
        
        env['LLAMA_NATIVE'] = 'OFF'
        env['GGML_NATIVE'] = 'OFF'
        
        # Duplicate args for scikit-build specific env var
        env['SKBUILD_CMAKE_ARGS'] = env['CMAKE_ARGS']
        
        # Forza l'uso di CMAKE
        env['LLAMA_CPP_LIB_PRELOAD'] = '1'
        return env

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        build_dir = self.get_build_dir(arch.arch)
        logging.info(f"Scanning {build_dir} for -march=native...")
        
        # DEBUG: List all files to understand structure
        try:
            logging.info("File Structure Check:")
            # sh.ls("-R", build_dir, _out=lambda L: logging.info(L.strip()))
        except Exception:
            pass

        count = 0
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    # Skip binary files/images to avoid encoding errors
                    if file.endswith(('.c', '.h', '.cpp', '.hpp', '.txt', '.cmake', '.make', '.sh')):
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        if "-march=native" in content:
                            logging.info(f"FOUND POISON in {filepath}. REMOVING...")
                            
                            # Pure Python replacement - Robust and Dumb
                            new_content = content.replace("-march=native", "")
                            
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                                
                            count += 1
                except Exception as e:
                    logging.warning(f"Could not process {filepath}: {e}")
                    
        logging.info(f"OPERATION CLEAN SLATE: Removed '-march=native' from {count} files.") 
        
        # VERIFICATION: Did we miss anything?
        logging.info("VERIFICATION SCAN:")
        try:
            # Check if ANY file still contains the poison
            grep_res = sh.grep("-r", "-march=native", build_dir, _ok_code=[0,1])
            if grep_res.exit_code == 0:
                logging.error("CRITICAL: POISON STILL PRESENT!")
                logging.error(grep_res.stdout.decode('utf-8')[:500]) # Print first 500 chars
            else:
                logging.info("VERIFICATION PASSED: No -march=native found in build_dir.")
        except Exception as e:
            logging.error(f"Verification failed: {e}") 

        # BUILD 170: TROJAN HORSE
        # Patch setup.py to force CMAKE_ARGS even if environment is stripped by pip
        logging.info("Applying TROJAN HORSE patch to setup.py...")
        count_setup = 0
        for root, dirs, files in os.walk(build_dir):
            if "setup.py" in files:
                setup_path = os.path.join(root, "setup.py")
                try:
                    with open(setup_path, 'r') as f:
                        content = f.read()
                    
                    # We look for where it reads env vars and hijack it.
                    # Usually: CMAKE_ARGS = os.environ.get("CMAKE_ARGS", "")
                    if "os.environ.get" in content:
                        logging.info(f"Injecting payload into {setup_path}")
                        
                        # Force our flags. Note: We keep the original get() call just in case, but prepend our flags.
                        # We use a naive replace for the most common pattern or just prepend variables at the top.
                        
                        # Better approach: Prepend a hard overwrite at the top of the file (after imports)
                        # But imports might be scattered.
                        
                        # Let's replace the common pattern:
                        # CMAKE_ARGS = os.environ.get("CMAKE_ARGS", "")
                        # with:
                        # CMAKE_ARGS = "-DLLAMA_NATIVE=OFF -DANDROID=1 -DCMAKE_SYSTEM_NAME=Android -DCMAKE_C_FLAGS='-march=armv8-a' -DCMAKE_CXX_FLAGS='-march=armv8-a' " + os.environ.get("CMAKE_ARGS", "")
                        
                        # Since we don't know the exact line, let's just REPLACE 'os.environ.get("CMAKE_ARGS"' with our hacked version.
                        
                        new_content = content.replace(
                            'os.environ.get("CMAKE_ARGS"', 
                            '"-DLLAMA_NATIVE=OFF -DANDROID=1 -DCMAKE_SYSTEM_NAME=Android -DCMAKE_C_FLAGS=\'-march=armv8-a\' -DCMAKE_CXX_FLAGS=\'-march=armv8-a\' " + os.environ.get("CMAKE_ARGS"'
                        )
                        
                        with open(setup_path, 'w') as f:
                            f.write(new_content)
                        count_setup += 1
                except Exception as e:
                    logging.error(f"Trojan Horse failed on {setup_path}: {e}")
        
        logging.info(f"Trojan Horse deployed in {count_setup} setup.py files.") 
                    
        logging.info(f"Sanitization complete. Patched {count} files.")

recipe = LlamaCppPythonRecipe()
