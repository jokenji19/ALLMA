"""Build Khronos' loader for linking only; Android supplies the runtime driver."""
from pathlib import Path
import subprocess

from pythonforandroid.recipe import Recipe


class OpenCLLinkRecipe(Recipe):
    name = 'opencl_link'
    version = '2025.07.22'
    url = 'https://github.com/KhronosGroup/OpenCL-ICD-Loader/archive/refs/tags/v{version}.tar.gz'
    sha512sum = '86e7aa831d3278645cd40c01b7e4262ed9cbfaa2ee8ffb4e9e012dd5bde7b29725508342f05178e09c496dbe3483e5e9b40e46a767d7f5bab504be931eaa95ef'
    depends = ['opencl_headers']

    def should_build(self, arch):
        return not (Path(self.get_build_dir(arch.arch)) / 'allma-link-build/loader/libOpenCL.so').is_file()

    def build_arch(self, arch):
        root = Path(self.get_build_dir(arch.arch))
        headers = Recipe.get_recipe('opencl_headers', self.ctx).get_build_dir(arch.arch)
        wrapper = root / 'allma-link-source'
        wrapper.mkdir(exist_ok=True)
        (wrapper / 'CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.16)\nproject(AllmaOpenCLLink LANGUAGES C)\n'
            'add_subdirectory("' + root.as_posix() + '" loader)\n'
            'set_target_properties(OpenCL PROPERTIES VERSION "" SOVERSION "")\n')
        env = self.get_recipe_env(arch)
        for key in ('CFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CMAKE_ARGS', 'SKBUILD_CMAKE_ARGS'):
            env.pop(key, None)
        build = root / 'allma-link-build'
        subprocess.run(['cmake', '-S', str(wrapper), '-B', str(build),
            '-DCMAKE_TOOLCHAIN_FILE=' + self.ctx.ndk_dir + '/build/cmake/android.toolchain.cmake',
            '-DANDROID_ABI=' + arch.arch, '-DANDROID_PLATFORM=android-24',
            '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON',
            '-DENABLE_OPENCL_LAYERS=OFF', '-DENABLE_OPENCL_LAYERINFO=OFF',
            '-DBUILD_TESTING=OFF', '-DOPENCL_ICD_LOADER_BUILD_TESTING=OFF',
            '-DOPENCL_ICD_LOADER_HEADERS_DIR=' + headers], env=env, check=True)
        subprocess.run(['cmake', '--build', str(build), '--parallel', '4', '--target', 'OpenCL'], env=env, check=True)


recipe = OpenCLLinkRecipe()
