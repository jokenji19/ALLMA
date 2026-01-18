from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory, shprint
import sh
import os
import logging
import subprocess
import sys

class LlamaCppPythonRecipe(CompiledComponentsPythonRecipe):
    name = 'llama-cpp-python'
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
            f"-DCMAKE_TOOLCHAIN_FILE={self.ctx.ndk_dir}/build/cmake/android.toolchain.cmake "
            f"-DCMAKE_SYSTEM_NAME=Android "
            f"-DANDROID_ABI={arch.arch} "
            f"-DANDROID_PLATFORM=android-21 "
            "-DLLAMA_CUBLAS=OFF "  # Niente CUDA su Android standard
            "-DLLAMA_OPENBLAS=OFF " # OpenBLAS può essere problematico, meglio default
            "-DLLAMA_BUILD_SERVER=OFF " # Non serve il server web
            "-DLLAVA_BUILD=OFF " # Disable Llava
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
                            '"-DGGML_NATIVE=OFF -DLLAMA_NATIVE=OFF -DANDROID=1 -DCMAKE_SYSTEM_NAME=Android -DCMAKE_C_FLAGS=\'-march=armv8-a\' -DCMAKE_CXX_FLAGS=\'-march=armv8-a\' " + os.environ.get("CMAKE_ARGS"'
                        )
                        
                        with open(setup_path, 'w') as f:
                            f.write(new_content)
                        count_setup += 1
                except Exception as e:
                    logging.error(f"Trojan Horse failed on {setup_path}: {e}")
        
        logging.info(f"Trojan Horse deployed in {count_setup} setup.py files.") 
        
        # [DISABLED] BUILD 172: CONFIG HIJACK (pyproject.toml)
        # This causes TOML errors and is likely redundant with SKBUILD_CMAKE_ARGS
        # logging.info("Applying CONFIG HIJACK to pyproject.toml...")
        # ...
        
                    
        logging.info(f"Sanitization complete. Patched {count} files.")

    def build_arch(self, arch):
        # BUILD 173: MANUAL COMPILATION
        # We cannot trust pip/scikit-build to pass flags correctly.
        # So we build libllama.so manually first, then tell pip to use it.
        
        build_dir = self.get_build_dir(arch.arch)
        llama_cpp_dir = os.path.join(build_dir, 'vendor', 'llama.cpp')
        
        # 1. Create separate build dir for the C++ lib
        lib_build_dir = os.path.join(build_dir, 'build-lib-arm64')
        os.makedirs(lib_build_dir, exist_ok=True)
        
        env = self.get_recipe_env(arch)
        
        # 2. Configure manually (Full Control)
        cmd_cmake = [
            "cmake",
            "-S", llama_cpp_dir,
            "-B", lib_build_dir,
            f"-DCMAKE_TOOLCHAIN_FILE={self.ctx.ndk_dir}/build/cmake/android.toolchain.cmake",
            "-DANDROID_ABI=arm64-v8a",
            "-DANDROID_PLATFORM=android-21",
            "-DLLAMA_NATIVE=OFF",
            "-DGGML_NATIVE=OFF",
            "-DLLAVA_BUILD=OFF",  # Disable Llava to avoid install errors with prebuilt llama
            "-DBUILD_SHARED_LIBS=ON",
            "-DCMAKE_C_FLAGS=-march=armv8-a",
            "-DCMAKE_CXX_FLAGS=-march=armv8-a"
        ]
        
        logging.info(f"Starting Manual CMake: {cmd_cmake}")
        subprocess.check_call(cmd_cmake, env=env)
        
        # 2b. Patch llama.cpp for Android POSIX constants
        llama_cpp_file = os.path.join(llama_cpp_dir, 'llama.cpp')
        with open(llama_cpp_file, 'r') as f:
            content = f.read()
            
        if '#define posix_madvise' not in content:
            logging.info("Patching llama.cpp for POSIX_MADV definitions...")
            patch_code = """
#if defined(__ANDROID__) || defined(ANDROID)
    #include <sys/mman.h>
    #ifndef POSIX_MADV_WILLNEED
        #ifdef MADV_WILLNEED
            #define POSIX_MADV_WILLNEED MADV_WILLNEED
        #else
            #define POSIX_MADV_WILLNEED 3
        #endif
    #endif
    #ifndef POSIX_MADV_RANDOM
        #ifdef MADV_RANDOM
            #define POSIX_MADV_RANDOM MADV_RANDOM
        #else
            #define POSIX_MADV_RANDOM 1
        #endif
    #endif
    #define posix_madvise madvise
#endif
"""
            # Insert after includes (approx line 43)
            # define LLAMA_API_INTERNAL is at top. We inserts after #include "llama.h"
            content = content.replace('#include "llama.h"', '#include "llama.h"\n' + patch_code)
            with open(llama_cpp_file, 'w') as f:
                f.write(content)

        # 3. Build manually
        logging.info("Starting Manual Make...")
        try:
             # Capture output so we can see why it fails
             subprocess.run(["make", "-j4"], cwd=lib_build_dir, env=env, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
             logging.error("MANUAL MAKE FAILED!")
             logging.error(f"STDOUT:\n{e.stdout}")
             logging.error(f"STDERR:\n{e.stderr}")
             # Write to file for easier retrieval
             err_log = os.path.join(build_dir, "make_failure.log")
             with open(err_log, "w") as f:
                 f.write(f"STDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}")
             raise e
        
        # 4. Locate the built library
        lib_path = os.path.join(lib_build_dir, "libllama.so")
        
        if not os.path.exists(lib_path):
             for root, dirs, files in os.walk(lib_build_dir):
                 if "libllama.so" in files:
                     lib_path = os.path.join(root, "libllama.so")
                     break
        
        if not os.path.exists(lib_path):
            logging.error("MANUAL BUILD FAILED: libllama.so not found")
            raise RuntimeError("Manual build failed")
            
        logging.info(f"MANUAL BUILD SUCCESS. Lib at: {lib_path}")
        
        # 5. BUILD 174: THE SURGEON (CMake Injection)
        # We patch the root CMakeLists.txt to recognize our prebuilt library
        cmake_root = os.path.join(build_dir, "CMakeLists.txt")
        logging.info(f"Applying PREBUILT PATCH to {cmake_root}")
        
        with open(cmake_root, 'r') as f:
            content = f.read()
            
        if "add_subdirectory(vendor/llama.cpp)" in content:
            patch = """
if(DEFINED ENV{LLAMA_CPP_PREBUILT_DIR})
  message(STATUS "ALLMA: Using prebuilt llama from $ENV{LLAMA_CPP_PREBUILT_DIR}")
  add_library(llama SHARED IMPORTED)
  set_target_properties(llama PROPERTIES
    IMPORTED_LOCATION "$ENV{LLAMA_CPP_PREBUILT_DIR}/lib/libllama.so"
    INTERFACE_INCLUDE_DIRECTORIES "$ENV{LLAMA_CPP_PREBUILT_DIR}/include"
  )
else()
  add_subdirectory(vendor/llama.cpp)
endif()
"""
            new_content = content.replace("add_subdirectory(vendor/llama.cpp)", patch)
            
            with open(cmake_root, 'w') as f:
                f.write(new_content)
                
            # PATCH 1: Main Install Block
            install_block_search = """    install(
        TARGETS llama 
        LIBRARY DESTINATION ${SKBUILD_PLATLIB_DIR}/llama_cpp
        RUNTIME DESTINATION ${SKBUILD_PLATLIB_DIR}/llama_cpp
        ARCHIVE DESTINATION ${SKBUILD_PLATLIB_DIR}/llama_cpp
        FRAMEWORK DESTINATION ${SKBUILD_PLATLIB_DIR}/llama_cpp
        RESOURCE DESTINATION ${SKBUILD_PLATLIB_DIR}/llama_cpp
    )"""
            if install_block_search in new_content:
                logging.info("PATCH APPLIED: install(TARGETS llama) [SKBUILD]")
                patch_replace = """    if(DEFINED ENV{LLAMA_CPP_PREBUILT_DIR})
        install(FILES "$ENV{LLAMA_CPP_PREBUILT_DIR}/lib/libllama.so" DESTINATION ${SKBUILD_PLATLIB_DIR}/llama_cpp)
    else()
""" + install_block_search + "\n    endif()"
                new_content = new_content.replace(install_block_search, patch_replace)
            else:
                logging.error("PATCH FAILED: Could not find install(TARGETS llama) [SKBUILD]")

            # PATCH 2: Source Dir Install Block
            install_block_2 = """    install(
        TARGETS llama 
        LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/llama_cpp
        RUNTIME DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/llama_cpp
        ARCHIVE DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/llama_cpp
        FRAMEWORK DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/llama_cpp
        RESOURCE DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/llama_cpp
    )"""
            if install_block_2 in new_content:
                logging.info("PATCH APPLIED: install(TARGETS llama) [SOURCE]")
                new_content = new_content.replace(install_block_2, f"if(NOT DEFINED ENV{{LLAMA_CPP_PREBUILT_DIR}})\n{install_block_2}\nendif()")
            else:
                logging.error("PATCH FAILED: Could not find install(TARGETS llama) [SOURCE]")

            # PATCH 3: DLLs Skbuild
            install_block_3 = """    install(
        FILES $<TARGET_RUNTIME_DLLS:llama>
        DESTINATION ${SKBUILD_PLATLIB_DIR}/llama_cpp
    )"""
            if install_block_3 in new_content:
                logging.info("PATCH APPLIED: install(DLLS) [SKBUILD]")
                new_content = new_content.replace(install_block_3, f"if(NOT DEFINED ENV{{LLAMA_CPP_PREBUILT_DIR}})\n{install_block_3}\nendif()")
            else:
                logging.warning("PATCH WARNING: Could not find install(DLLS) [SKBUILD]")

            # PATCH 4: DLLs Source
            install_block_4 = """    install(
        FILES $<TARGET_RUNTIME_DLLS:llama>
        DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/llama_cpp
    )"""
            if install_block_4 in new_content:
                logging.info("PATCH APPLIED: install(DLLS) [SOURCE]")
                new_content = new_content.replace(install_block_4, f"if(NOT DEFINED ENV{{LLAMA_CPP_PREBUILT_DIR}})\n{install_block_4}\nendif()")
            else:
                logging.warning("PATCH WARNING: Could not find install(DLLS) [SOURCE]")

            with open(cmake_root, 'w') as f:
                f.write(new_content)
                
        else:
            logging.error("Could not find add_subdirectory in CMakeLists.txt! Patch failed.")

        # 6. Organize Prebuilt Dir structure
        prebuilt_dir = os.path.join(build_dir, "prebuilt_llama")
        os.makedirs(os.path.join(prebuilt_dir, "lib"), exist_ok=True)
        os.makedirs(os.path.join(prebuilt_dir, "include"), exist_ok=True)
        
        import shutil
        # Copy lib
        shutil.copy(lib_path, os.path.join(prebuilt_dir, "lib", "libllama.so"))
        # Copy headers
        shutil.copy(os.path.join(llama_cpp_dir, "llama.h"), os.path.join(prebuilt_dir, "include", "llama.h"))
        if os.path.exists(os.path.join(llama_cpp_dir, "ggml.h")):
             shutil.copy(os.path.join(llama_cpp_dir, "ggml.h"), os.path.join(prebuilt_dir, "include", "ggml.h"))
        
        # 7. Set Environment Variable
        env['LLAMA_CPP_PREBUILT_DIR'] = prebuilt_dir
        
        # 8. Install Python Package via Pip with Verified Target
        logging.info("Installing build dependencies (scikit-build-core)...")
        try:
             subprocess.run(
                [sys.executable, "-m", "pip", "install", "scikit-build-core", "cmake"],
                cwd=build_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True
             )
        except subprocess.CalledProcessError as e:
             logging.error("FAILED TO INSTALL BUILD DEPS")
             logging.error(e.stderr)
             raise e

        # FIXED INSTALL LOGIC WITH TARGET AND MANUAL FALLBACK
        logging.info("Installing Python package via pip with PREBUILT linkage...")
        install_target = self.ctx.get_python_install_dir(arch.arch)
        logging.info(f"Target Install Dir: {install_target}")
        
        if not os.path.exists(install_target):
            os.makedirs(install_target)

        try:
            # Run pip with target
            subprocess.run(
                [sys.executable, "-m", "pip", "install", ".", 
                 "--no-build-isolation", 
                 "--target", install_target, 
                 "--ignore-installed", 
                 "--no-deps"],
                cwd=build_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True
            )
            logging.info(f"PIP SUCCESS. Installed to {install_target}")
        except subprocess.CalledProcessError as e:
            logging.error("PIP INSTALL FAILED! Attempting Manual Copy...")
            logging.error(f"STDOUT: {e.stdout}")
            logging.error(f"STDERR: {e.stderr}")
            # Do not raise, fall through to Manual Copy
            pass

        # VERIFICATION / MANUAL COPY FALLBACK
        installed_pkg = os.path.join(install_target, "llama_cpp")
        if not os.path.exists(installed_pkg):
             logging.warning("Pip verification failed. Attempting MANUAL COPY...")
             src_pkg = os.path.join(build_dir, "llama_cpp")
             import shutil
             if os.path.exists(installed_pkg): shutil.rmtree(installed_pkg)
             
             if os.path.exists(src_pkg):
                 shutil.copytree(src_pkg, installed_pkg)
                 logging.info("Manual Copy complete.")
             else:
                 raise RuntimeError(f"Source package {src_pkg} not found for manual copy!")

        # Ensure libllama.so is in the package
        dest_so = os.path.join(installed_pkg, "libllama.so")
        if not os.path.exists(dest_so):
             src_so = os.path.join(prebuilt_dir, "lib", "libllama.so")
             if os.path.exists(src_so):
                  import shutil
                  shutil.copy2(src_so, dest_so)
                  logging.info(f"Copied libllama.so to {dest_so}")
             else:
                  logging.warning("Could not find source libllama.so for copy!")

        logging.info(f"FINAL INSTALL SUCCESS! Package at {installed_pkg}")

recipe = LlamaCppPythonRecipe()
