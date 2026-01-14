
from pythonforandroid.recipe import Recipe
from pythonforandroid.logger import shprint
from pythonforandroid.util import current_directory
import sh
import shutil
import os

class LlamaCliRecipe(Recipe):
    version = 'b3564'
    url = 'https://github.com/ggerganov/llama.cpp/archive/refs/tags/{version}.zip'
    depends = ['cmake'] 
    
    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        
        # Build dir
        build_dir = os.path.join(self.get_build_dir(arch.arch), 'build')
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)
            
        with current_directory(build_dir):
            # Configure CMake
            # We target the specific android architecture and disable complex backends
            cmd = [
                "cmake", "..",
                "-DCMAKE_TOOLCHAIN_FILE=" + os.path.join(os.environ['ANDROID_NDK_HOME'], "build/cmake/android.toolchain.cmake"),
                "-DANDROID_ABI=" + arch.arch,
                "-DANDROID_PLATFORM=android-24",
                "-DLLAMA_METAL=OFF",  # CPU only
                "-DLLAMA_BLAS=OFF",   # CPU only
                "-DLLAMA_K_QUANTS=ON"
            ]
            shprint(sh.cmake, *cmd, _env=env)
            
            # Build llama-cli target
            cmd_build = ["cmake", "--build", ".", "--config", "Release", "--target", "llama-cli", "-j4"]
            shprint(sh.cmake, *cmd_build, _env=env)
            
            # Install: Copy binary to a new python package 'llama_bin' in site-packages
            site_pkgs = self.ctx.get_python_install_dir()
            target_dir = os.path.join(site_pkgs, "llama_bin")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            # Create __init__.py so it can be imported
            # This allows app to do: import llama_bin; path = llama_bin.bin_path
            with open(os.path.join(target_dir, "__init__.py"), "w") as f:
                f.write("import os\nbin_path = os.path.join(os.path.dirname(__file__), 'llama-cli')\n")
                
            # Copy the binary
            # Binary usually in bin/ relative to build dir
            bin_source = "bin/llama-cli"
            if not os.path.exists(bin_source):
                # Sometimes it is directly in build dir depending on cmake version
                bin_source = "llama-cli"
                
            shutil.copy(bin_source, os.path.join(target_dir, "llama-cli"))
            
            # Ensure executable perm (though apk install might reset, we try)
            os.chmod(os.path.join(target_dir, "llama-cli"), 0o755)

recipe = LlamaCliRecipe()
