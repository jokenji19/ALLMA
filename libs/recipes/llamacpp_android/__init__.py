from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pythonforandroid.toolchain import current_directory, shprint
import sh
import os
import logging
import subprocess
import sys
import shutil

class LlamacppAndroidRecipe(CompiledComponentsPythonRecipe):
    name = 'llamacpp_android'
    version = '0.3.16'  # Reverted to valid version, keeping Vulkan disabled logic
    # Use PyPI source because GitHub tarballs often lack submodules (vendor/llama.cpp)
    # causing the patch to miss the files, or the build to fetch fresh (unpatched) code.
    url = 'https://files.pythonhosted.org/packages/source/l/llama_cpp_python/llama_cpp_python-{version}.tar.gz'
    
    depends = ['setuptools', 'numpy']
    site_packages_name = 'llama_cpp_python'
    
    # Non usiamo hostpython per la compilazione C++
    call_hostpython_via_targetpython = False

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        
        # CMAKE ARGS specifici per Android
        env['CMAKE_ARGS'] = (
            f"-DCMAKE_TOOLCHAIN_FILE={self.ctx.ndk_dir}/build/cmake/android.toolchain.cmake "
            f"-DCMAKE_SYSTEM_NAME=Android "
            f"-DANDROID_ABI={arch.arch} "
            f"-DANDROID_PLATFORM=android-32 "
            "-DCMAKE_BUILD_TYPE=Release "
            "-DLLAMA_CUBLAS=OFF " 
            "-DLLAMA_OPENBLAS=OFF "
            "-DLLAMA_BUILD_SERVER=OFF " 
            "-DLLAVA_BUILD=OFF "
            "-DLLAMA_NATIVE=OFF " 
            "-DCMAKE_C_FLAGS='-march=armv8-a' "
            "-DCMAKE_CXX_FLAGS='-march=armv8-a' "
            "-DGGML_NATIVE=OFF " 
            "-DGGML_CPU_ARM_ARCH=8 "
            "-DGGML_OPENMP=OFF " 
            "-DGGML_PERF=OFF "  
        )
        
        env['CMAKE_C_FLAGS'] = "-march=armv8-a"
        env['CMAKE_CXX_FLAGS'] = "-march=armv8-a"
        
        env['CFLAGS'] = f"-target {arch.target} -fPIC -march=armv8-a"
        env['CXXFLAGS'] = f"-target {arch.target} -fPIC -march=armv8-a"
        env['LDFLAGS'] = f"-target {arch.target}"
        
        env['LLAMA_NATIVE'] = 'OFF'
        env['GGML_NATIVE'] = 'OFF'
        env['GGML_OPENMP'] = 'OFF'
        
        env['SKBUILD_CMAKE_ARGS'] = env['CMAKE_ARGS']
        env['LLAMA_CPP_LIB_PRELOAD'] = '1'
        return env

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        build_dir = self.get_build_dir(arch.arch)
        llama_cpp_dir = os.path.join(build_dir, 'vendor', 'llama.cpp')
        llama_cpp_tag = os.environ.get("LLAMA_CPP_TAG", "b5092")
        llama_cpp_repo = os.environ.get("LLAMA_CPP_REPO", "https://github.com/ggml-org/llama.cpp")
        if os.path.exists(llama_cpp_dir):
            try:
                if os.path.exists(os.path.join(llama_cpp_dir, ".git")):
                    subprocess.check_call(["git", "-C", llama_cpp_dir, "fetch", "--tags"])
                    subprocess.check_call(["git", "-C", llama_cpp_dir, "checkout", llama_cpp_tag])
                else:
                    tmp_dir = os.path.join(build_dir, "llama_cpp_b5092")
                    if os.path.exists(tmp_dir):
                        shutil.rmtree(tmp_dir)
                    subprocess.check_call(["git", "clone", "--depth", "1", "--branch", llama_cpp_tag, llama_cpp_repo, tmp_dir])
                    shutil.rmtree(llama_cpp_dir)
                    shutil.move(tmp_dir, llama_cpp_dir)
            except Exception as e:
                logging.error(f"Failed to set llama.cpp to {llama_cpp_tag}: {e}")
        logging.info(f"Scanning {build_dir} for -march=native...")

        # OPENCL MANUAL FIX (Build 163-v7)
        # We manually placed headers in libs/recipes/llamacpp_android/CL
        # No need to download anything here.
        # Just ensure they are found by CMake.
        
        try:
            logging.info("File Structure Check:")
            
            # COMPILE OPENCL STUB (Build 163-v14)
            # We need libOpenCL.so for linking, but the NDK doesn't provide it.
            # We compile our own stub.
            stub_c = os.path.join(self.get_recipe_dir(), "opencl_stub.c")
            stub_so = os.path.join(self.get_recipe_dir(), "libOpenCL.so")
            
            if os.path.exists(stub_so):
                logging.info(f"Removing stale OpenCL stub: {stub_so}")
                os.remove(stub_so)

            if os.path.exists(stub_c):
                logging.info(f"Compiling OpenCL stub: {stub_c} -> {stub_so}")
                
                # Get CC from arch env (provided by p4a)
                env = arch.get_env()
                cc = env.get("CC")
                logging.info(f"CC environment variable: {cc}")
                
                if cc:
                    import subprocess
                    # usage of cc might include arguments, so we should be careful. 
                    # But usually it is just the path to clang with some flags.
                    # We need to construct the command using the environment to ensure flags are respected if needed, 
                    # but check_call with shell=True and the command string should work if cc is "clang ...flags..."
                    
                    cmd = f"{cc} -shared -fPIC -o {stub_so} {stub_c}"
                    try:
                        subprocess.check_call(cmd, shell=True, env=env)
                        logging.info("OpenCL stub compiled successfully.")
                    except Exception as e:
                        logging.error(f"Failed to compile stub: {e}")
                else:
                     logging.warning("CC env var not set in arch.get_env(), cannot compile stub!")
        except Exception:
            pass

        count = 0
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    if file.endswith(('.c', '.h', '.cpp', '.hpp', '.txt', '.cmake', '.make', '.sh')):
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        if "-march=native" in content:
                            logging.info(f"FOUND POISON in {filepath}. REMOVING...")
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
            grep_res = sh.grep("-r", "-march=native", build_dir, _ok_code=[0,1])
            if grep_res.exit_code == 0:
                logging.error("CRITICAL: POISON STILL PRESENT!")
                logging.error(grep_res.stdout.decode('utf-8')[:500])
            else:
                logging.info("VERIFICATION PASSED: No -march=native found in build_dir.")
        except Exception as e:
            logging.error(f"Verification failed: {e}") 
        
        # SETUP.PY PATCH
        logging.info("Applying TROJAN HORSE patch to setup.py...")
        count_setup = 0
        for root, dirs, files in os.walk(build_dir):
            if "setup.py" in files:
                setup_path = os.path.join(root, "setup.py")
                try:
                    with open(setup_path, 'r') as f:
                        content = f.read()
                    
                    if "os.environ.get" in content:
                        logging.info(f"Injecting payload into {setup_path}")
                        new_content = content.replace(
                            'os.environ.get("CMAKE_ARGS"', 
                            '"-DGGML_OPENMP=OFF -DGGML_PERF=OFF -DGGML_NATIVE=OFF -DLLAMA_NATIVE=OFF -DANDROID=1 -DCMAKE_SYSTEM_NAME=Android -DCMAKE_C_FLAGS=\'-march=armv8-a\' -DCMAKE_CXX_FLAGS=\'-march=armv8-a\' " + os.environ.get("CMAKE_ARGS"'
                        )
                        with open(setup_path, 'w') as f:
                            f.write(new_content)
                        count_setup += 1
                except Exception as e:
                    logging.error(f"Trojan Horse failed on {setup_path}: {e}")
        
        logging.info(f"Trojan Horse deployed in {count_setup} setup.py files.") 
        logging.info(f"Sanitization complete. Patched {count} files.")

    def build_arch(self, arch):
        build_dir = self.get_build_dir(arch.arch)
        llama_cpp_dir = os.path.join(build_dir, 'vendor', 'llama.cpp')
        
        # 1. Create separate build dir for the C++ lib
        lib_build_dir = os.path.join(build_dir, 'build-lib-arm64')
        os.makedirs(lib_build_dir, exist_ok=True)
        
        env = self.get_recipe_env(arch)

        # --- BEGIN PATCHING SECTION ---
        # 2b. Patch llama.cpp for POSIX constants
        # Check for llama.cpp location (changed in newer versions to src/llama.cpp)
        possible_paths = [
            os.path.join(llama_cpp_dir, 'llama.cpp'),
            os.path.join(llama_cpp_dir, 'src', 'llama.cpp')
        ]
        
        llama_cpp_file = None
        for p in possible_paths:
            if os.path.exists(p):
                llama_cpp_file = p
                break
        
        if not llama_cpp_file:
             logging.error(f"Could not find llama.cpp source in {llama_cpp_dir}")
             # Only verify if we are sure the source is there. If using PyPI tarball, it should be.
             # If strictly checking:
             # raise FileNotFoundError(f"llama.cpp source not found in {possible_paths}")
             logging.warning("Proceeding without patching llama.cpp source (file not found)")
        else:
            logging.info(f"Patching {llama_cpp_file} for POSIX_MADV definitions...")
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
            #define POSIX_WILLNEED 3
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
                content = content.replace('#include "llama.h"', '#include "llama.h"\n' + patch_code)
                with open(llama_cpp_file, 'w') as f:
                    f.write(content)

        # 2c. PATCH ROOT CMAKE TO DISABLE OPENMP & NATIVE
        cmake_ggml = os.path.join(llama_cpp_dir, 'CMakeLists.txt')
        if os.path.exists(cmake_ggml):
            logging.info(f"Patching {cmake_ggml} to FORCE DISABLE OPENMP")
            with open(cmake_ggml, 'r') as f:
                cm_content = f.read()
            
            # 2c. PATCH ROOT CMAKE TO DISABLE OPENMP & NATIVE
            cm_content = cm_content.replace('option(LLAMA_OPENMP "llama: use OpenMP" ON)', 'option(LLAMA_OPENMP "llama: use OpenMP" OFF)')
            cm_content = cm_content.replace('option(GGML_OPENMP "ggml: use OpenMP" ON)', 'option(GGML_OPENMP "ggml: use OpenMP" OFF)')
            cm_content = cm_content.replace('option(LLAMA_NATIVE "llama: enable -march=native optimizations" ON)', 'option(LLAMA_NATIVE "llama: enable -march=native optimizations" OFF)')
            cm_content = cm_content.replace('option(GGML_NATIVE "ggml: enable -march=native optimizations" ON)', 'option(GGML_NATIVE "ggml: enable -march=native optimizations" OFF)')
            
            # Helper to force cache variables
            force_vars = """
set(LLAMA_OPENMP OFF CACHE BOOL "Force OFF" FORCE)
set(GGML_OPENMP OFF CACHE BOOL "Force OFF" FORCE)
set(LLAMA_NATIVE OFF CACHE BOOL "Force OFF" FORCE)
set(GGML_NATIVE OFF CACHE BOOL "Force OFF" FORCE)
"""
            # Inject after project() to ensure it takes precedence
            if "project(" in cm_content:
                # Find the end of project(...) line roughly or just insert after first project(
                # Simpler: replace project(...) with project(...) \n force_vars
                import re
                cm_content = re.sub(r'(project\s*\(.*?\))', r'\1\n' + force_vars, cm_content, count=1, flags=re.DOTALL)
            else:
                cm_content += force_vars # Fallback

            with open(cmake_ggml, 'w') as f:
                f.write(cm_content)

        # 2d. RECURSIVE PATCH FOR THREADS (The real fix for ALL modules)
        # Scan all CMakeLists.txt and replace find_package(Threads)
        logging.info("Recursive patching of CMakeLists.txt for Android Threads...")
        thread_patch = """
if(ANDROID)
    set(Threads_FOUND TRUE)
    if(NOT TARGET Threads::Threads)
        add_library(Threads::Threads INTERFACE IMPORTED)
    endif()
else()
    find_package(Threads REQUIRED)
endif()
"""
        count_cmake = 0
        for root, dirs, files in os.walk(llama_cpp_dir):
            if "CMakeLists.txt" in files:
                cmake_file = os.path.join(root, "CMakeLists.txt")
                try:
                    with open(cmake_file, 'r') as f:
                        content = f.read()
                    
                    if "find_package(Threads" in content:
                        logging.info(f"Patching Threads in {cmake_file}")
                        # Coverage for both REQUIRED and not, though usually REQUIRED
                        new_content = content.replace("find_package(Threads REQUIRED)", thread_patch)
                        new_content = new_content.replace("find_package(Threads)", thread_patch) # Fallback
                        
                        # Also fix CheckLibraryExists which might look for pthread explicitly
                        # This handles the "ld: error: unable to find library -lpthread" in check stages
                        if "check_library_exists(pthread" in new_content or "CHECK_LIBRARY_EXISTS(pthread" in new_content:
                             new_content = new_content.replace("check_library_exists(pthread", "# check_library_exists(pthread")
                             new_content = new_content.replace("CHECK_LIBRARY_EXISTS(pthread", "# CHECK_LIBRARY_EXISTS(pthread")

                        with open(cmake_file, 'w') as f:
                            f.write(new_content)
                        count_cmake += 1
                except Exception as e:
                    logging.error(f"Failed to patch {cmake_file}: {e}")

        logging.info(f"Patched Threads in {count_cmake} CMakeLists.txt files.")

        # --- PLATFORM PATCH (Fixes "Unsupported platform") ---
        # llama-cpp-python checks sys.platform and raises error if not linux/darwin/win32
        # On some p4a builds, sys.platform might be 'android' or similar
        
        # Search strategy for _ctypes_extensions.py
        # 1. In llama_cpp_dir/llama_cpp (vendor/llama.cpp/llama_cpp) - unlikely for p4a
        # 2. In build_dir/llama_cpp (root of package) - most likely for p4a
        extensions_paths_to_check = [
            os.path.join(build_dir, "llama_cpp", "_ctypes_extensions.py"),
            os.path.join(llama_cpp_dir, "llama_cpp", "_ctypes_extensions.py"),
            os.path.join(llama_cpp_dir, "..", "llama_cpp", "_ctypes_extensions.py")
        ]
        
        extensions_path = None
        for p in extensions_paths_to_check:
            if os.path.exists(p):
                extensions_path = p
                break
        
        if extensions_path:
             with open(extensions_path, 'r') as f:
                 ext_content = f.read()
             
             # Patch: if sys.platform.startswith("linux") or sys.platform.startswith("freebsd") OR ...("android")
             if 'sys.platform.startswith("linux")' in ext_content:
                 logging.info(f"Patching platform check in {extensions_path}")
                 ext_content = ext_content.replace(
                     'if sys.platform.startswith("linux") or sys.platform.startswith("freebsd"):',
                     'if sys.platform.startswith("linux") or sys.platform.startswith("freebsd") or sys.platform.startswith("android"):'
                 )
                 with open(extensions_path, 'w') as f:
                     f.write(ext_content)
        else:
             logging.warning(f"Could not find _ctypes_extensions.py in {extensions_paths_to_check}")
        
        # --- VULKAN LINKING PATCH ---
        # The Vulkan::Vulkan imported target doesn't properly link libvulkan.so for Android cross-compilation
        # We need to patch ggml-vulkan/CMakeLists.txt to add explicit vulkan library linking
        vulkan_cmake_path = os.path.join(llama_cpp_dir, "ggml", "src", "ggml-vulkan", "CMakeLists.txt")
        if os.path.exists(vulkan_cmake_path):
            try:
                with open(vulkan_cmake_path, 'r') as f:
                    vulkan_content = f.read()
                
                # Add full absolute path to libvulkan.so in target_link_libraries
                old_link = "target_link_libraries(ggml-vulkan PRIVATE Vulkan::Vulkan)"
                ndk_libvulkan_path = f"{self.ctx.ndk_dir}/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/lib/aarch64-linux-android/34/libvulkan.so"
                # REMOVE Vulkan::Vulkan completely - it uses wrong API level library
                new_link = f'target_link_libraries(ggml-vulkan PRIVATE "{ndk_libvulkan_path}")'
                
                if old_link in vulkan_content:
                    vulkan_content = vulkan_content.replace(old_link, new_link)
                    with open(vulkan_cmake_path, 'w') as f:
                        f.write(vulkan_content)
                    logging.info(f"Patched Vulkan linking with absolute libvulkan.so path in {vulkan_cmake_path}")
                else:
                    logging.warning(f"Vulkan link line not found in {vulkan_cmake_path}")
            except Exception as e:
                logging.error(f"Failed to patch Vulkan CMakeLists: {e}")
        # --- END VULKAN PATCH ---
        # --- END VULKAN PATCH ---
        # --- VULKAN HOST TOOLCHAIN PATCH (Build 163-v19) ---
        # Fix for 'vulkan-shaders-gen' using Android CFLAGS on Host
        host_toolchain_in = os.path.join(llama_cpp_dir, "ggml", "src", "ggml-vulkan", "cmake", "host-toolchain.cmake.in")
        if os.path.exists(host_toolchain_in):
             logging.info(f"Patching {host_toolchain_in} to UNSET cross-compile env vars")
             with open(host_toolchain_in, 'r') as f:
                 ht_content = f.read()
             
             # Prepend unsets
             unset_code = """
# ALLMA PATCH: Unset cross-compile flags for host build
set(ENV{CFLAGS} "")
set(ENV{CXXFLAGS} "")
set(ENV{LDFLAGS} "")
"""
             if "ALLMA PATCH" not in ht_content:
                 new_content = unset_code + ht_content
                 with open(host_toolchain_in, 'w') as f:
                     f.write(new_content)
        else:
             logging.warning(f"Could not find host-toolchain.cmake.in at {host_toolchain_in}")
        # --- END VULKAN HOST TOOLCHAIN PATCH ---
        
        # --- END PATCHING SECTION ---
        
        # 2. Configure manually (Full Control)
        cmd_cmake = [
            "cmake",
            "-S", llama_cpp_dir,
            "-B", lib_build_dir,
            f"-DCMAKE_TOOLCHAIN_FILE={self.ctx.ndk_dir}/build/cmake/android.toolchain.cmake",
            "-DANDROID_ABI=arm64-v8a",
            "-DANDROID_PLATFORM=android-32",
            "-DLLAMA_NATIVE=OFF",
            "-DGGML_NATIVE=OFF",
            "-DGGML_OPENMP=OFF",
            "-DGGML_PERF=OFF",
            "-DLLAVA_BUILD=OFF",
            "-DLLAMA_CURL=OFF", # Fix for missing libcurl on Android
            # VULKAN PIVOT (Build 163-v18)
            "-DGGML_VULKAN=ON", 
            "-DGGML_OPENCL=OFF",
            # GLSL COMPILER FIX (Build 163-v19)
            f"-DVulkan_GLSLC_EXECUTABLE={self.ctx.ndk_dir}/shader-tools/darwin-x86_64/glslc",
            
            # CORRECT CMAKE VARIABLES FOR FindOpenCL.cmake
            f"-DOpenCL_INCLUDE_DIR={self.get_recipe_dir()}", # Parent of CL/
            f"-DOpenCL_LIBRARY={self.get_recipe_dir()}/libOpenCL.so",
            # Redundant but helpful flags
            f"-DCL_IncludeDir={self.get_recipe_dir()}", 
            f"-DCL_Library={self.get_recipe_dir()}/libOpenCL.so",
            # Force include path for the compiler
            f"-DCMAKE_C_FLAGS='-march=armv8-a -I{self.get_recipe_dir()}'",
            f"-DCMAKE_CXX_FLAGS='-march=armv8-a -I{self.get_recipe_dir()}'",
            "-DBUILD_SHARED_LIBS=ON",
            f"-DCMAKE_C_FLAGS=-march=armv8-a -I{self.ctx.ndk_dir}/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include",
            f"-DCMAKE_CXX_FLAGS=-march=armv8-a -I{self.ctx.ndk_dir}/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include",
            # FORCE PTHREAD VARIABLES TO BYPASS CHECKS
            "-DCMAKE_HAVE_LIBC_PTHREAD=1",
            "-DCMAKE_HAVE_PTHREAD_CREATE=1",
            "-DCMAKE_THREAD_LIBS_INIT=",
            "-DTHREADS_HAVE_PTHREAD_ARG=1",
            "-DThreads_FOUND=TRUE"
        ]
        
        logging.info(f"Starting Manual CMake: {cmd_cmake}")
        try:
            result = subprocess.run(cmd_cmake, env=env, capture_output=True, text=True, check=True)
            logging.info(f"CMake SUCCESS:\\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            logging.error(f"CMake FAILED!\\nSTDOUT:\\n{e.stdout}\\nSTDERR:\\n{e.stderr}")
            # SAVE LOG TO FILE FOR DEBUGGING
            crash_log = os.path.join(build_dir, "cmake_crash_log.txt")
            with open(crash_log, "w") as f:
                f.write(f"STDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}")
            logging.info(f"Saved crash log to {crash_log}")
            raise
        
        # 3. Build manually
        logging.info("Starting Manual Make...")
        try:
             subprocess.run(["make", "-j4"], cwd=lib_build_dir, env=env, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
             logging.error("MANUAL MAKE FAILED!")
             logging.error(f"STDOUT:\n{e.stdout}")
             logging.error(f"STDERR:\n{e.stderr}")
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

            # PATCH 3: DLLs Skbuild
            install_block_3 = """    install(
        FILES $<TARGET_RUNTIME_DLLS:llama>
        DESTINATION ${SKBUILD_PLATLIB_DIR}/llama_cpp
    )"""
            if install_block_3 in new_content:
                logging.info("PATCH APPLIED: install(DLLS) [SKBUILD]")
                new_content = new_content.replace(install_block_3, f"if(NOT DEFINED ENV{{LLAMA_CPP_PREBUILT_DIR}})\n{install_block_3}\nendif()")

            # PATCH 4: DLLs Source
            install_block_4 = """    install(
        FILES $<TARGET_RUNTIME_DLLS:llama>
        DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/llama_cpp
    )"""
            if install_block_4 in new_content:
                logging.info("PATCH APPLIED: install(DLLS) [SOURCE]")
                new_content = new_content.replace(install_block_4, f"if(NOT DEFINED ENV{{LLAMA_CPP_PREBUILT_DIR}})\n{install_block_4}\nendif()")

            with open(cmake_root, 'w') as f:
                f.write(new_content)
                
        else:
            logging.error("Could not find add_subdirectory in CMakeLists.txt! Patch failed.")

        # 6. Organize Prebuilt Dir structure
        prebuilt_dir = os.path.join(build_dir, "prebuilt_llama")
        os.makedirs(os.path.join(prebuilt_dir, "lib"), exist_ok=True)
        os.makedirs(os.path.join(prebuilt_dir, "include"), exist_ok=True)
        
        import shutil
        
        def find_and_copy(filename, dest_dir):
            search_paths = [
                os.path.join(llama_cpp_dir, filename),
                os.path.join(llama_cpp_dir, 'include', filename),
                os.path.join(llama_cpp_dir, 'src', filename),
                os.path.join(llama_cpp_dir, 'ggml', 'include', filename),
                os.path.join(llama_cpp_dir, 'ggml', 'src', filename),
            ]
            found = False
            for p in search_paths:
                if os.path.exists(p):
                    shutil.copy(p, os.path.join(dest_dir, filename))
                    logging.info(f"Copied {filename} from {p}")
                    found = True
                    break
            if not found:
                 logging.warning(f"Header {filename} not found in expected paths.")

        find_and_copy("llama.h", os.path.join(prebuilt_dir, "include"))
        find_and_copy("ggml.h", os.path.join(prebuilt_dir, "include"))
        find_and_copy("ggml-alloc.h", os.path.join(prebuilt_dir, "include"))
        find_and_copy("ggml-backend.h", os.path.join(prebuilt_dir, "include"))

        # CRITICAL FIX: explicit copy of libllama.so to prebuilt lib dir
        # This was missing, causing empty lib dir during packaging
        if lib_path and os.path.exists(lib_path):
             import shutil
             shutil.copy2(lib_path, os.path.join(prebuilt_dir, "lib", "libllama.so"))
             logging.info(f"Copied libllama.so from {lib_path} to prebuilt lib dir")
             
             # ALSO COPY all libggml*.so (cpu, vulkan, etc.)
             import glob
             # Search for all libggml*.so files in the lib build dir
             ggml_libs = []
             for root, dirs, files in os.walk(lib_build_dir):
                 for f in files:
                     if f.startswith("libggml") and f.endswith(".so"):
                         ggml_libs.append(os.path.join(root, f))
             
             if ggml_libs:
                 for lib in ggml_libs:
                     shutil.copy2(lib, os.path.join(prebuilt_dir, "lib", os.path.basename(lib)))
                     logging.info(f"Copied {os.path.basename(lib)} to prebuilt lib dir")
             else:
                 logging.warning("No libggml*.so found in build dir!")

        else:
             logging.error("Source libllama.so missing for prebuilt copy!")
             raise RuntimeError("Source libllama.so missing")
        
        # 7. Set Environment Variable
        env['LLAMA_CPP_PREBUILT_DIR'] = prebuilt_dir
        
        # 8. Install Python Package
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

        logging.info("Installing Python package via pip with PREBUILT linkage...")
        install_target = self.ctx.get_python_install_dir(arch.arch)
        if not os.path.exists(install_target):
            os.makedirs(install_target)

        try:
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

        # Ensure all libggml*.so are in the package (CRITICAL FIX)
        # Scan prebuilt dir for all ggml libs
        prebuilt_lib_dir = os.path.join(prebuilt_dir, "lib")
        if os.path.exists(prebuilt_lib_dir):
            for f in os.listdir(prebuilt_lib_dir):
                if f.startswith("libggml") and f.endswith(".so"):
                    src_lib = os.path.join(prebuilt_lib_dir, f)
                    dest_lib = os.path.join(installed_pkg, f)
                    if not os.path.exists(dest_lib):
                        import shutil
                        shutil.copy2(src_lib, dest_lib)
                        logging.info(f"Copied {f} to {dest_lib}")
        else:
            logging.warning(f"Prebuilt lib dir {prebuilt_lib_dir} missing during package install!")

        # --- PLATFORM PATCH (POST-INSTALL) ---
        # This MUST be applied AFTER pip install since pip downloads fresh source
        # llama-cpp-python checks sys.platform and raises error if not linux/darwin/win32
        # On Android, sys.platform might be 'android' - we need to support that
        installed_ext = os.path.join(installed_pkg, "_ctypes_extensions.py")
        if os.path.exists(installed_ext):
             with open(installed_ext, 'r') as f:
                 ext_content = f.read()
             
             if 'sys.platform.startswith("linux")' in ext_content and 'startswith("android")' not in ext_content:
                 logging.info(f"Patching platform check in {installed_ext} (POST-INSTALL)")
                 ext_content = ext_content.replace(
                     'if sys.platform.startswith("linux") or sys.platform.startswith("freebsd"):',
                     'if sys.platform.startswith("linux") or sys.platform.startswith("freebsd") or sys.platform.startswith("android"):'
                 )
                 with open(installed_ext, 'w') as f:
                     f.write(ext_content)
                 logging.info("Platform patch applied successfully!")
             
             # Re-read for second patch
             with open(installed_ext, 'r') as f:
                 ext_content = f.read()
             
             # LIBRARY PATH PATCH: Add LLAMA_CPP_LIB env var support to load_shared_library
             # This allows the library to be found from custom paths (Android app files)
             if 'LLAMA_CPP_LIB' not in ext_content:
                 logging.info(f"Patching library search in {installed_ext}")
                 old_func_start = 'def load_shared_library(lib_base_name: str, base_path: pathlib.Path):'
                 new_func_with_env = '''def load_shared_library(lib_base_name: str, base_path: pathlib.Path):
    """Platform independent shared library loader"""
    # ANDROID PATCH: Check LLAMA_CPP_LIB environment variable first
    env_lib = os.environ.get("LLAMA_CPP_LIB")
    if env_lib and os.path.exists(env_lib):
        try:
            return ctypes.CDLL(env_lib)
        except Exception as e:
            pass  # Fall through to standard search
    
    # Original:'''
                 if old_func_start in ext_content:
                     ext_content = ext_content.replace(old_func_start, new_func_with_env)
                     with open(installed_ext, 'w') as f:
                         f.write(ext_content)
                     logging.info("Library path patch applied successfully!")
        else:
             logging.warning(f"Could not find _ctypes_extensions.py at {installed_ext}")

        logging.info(f"FINAL INSTALL SUCCESS! Package at {installed_pkg}")

recipe = LlamacppAndroidRecipe()
