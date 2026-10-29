"""Build a matched Python/native runtime from the same pinned source archive.

The CPU stays available independently of the optional OpenCL plugin.
No unrelated llama.cpp checkout or host-built wheel may replace its ABI.
"""
from pythonforandroid.recipe import CompiledComponentsPythonRecipe, Recipe
from pathlib import Path
import json
import hashlib
import shutil
import subprocess


class LlamacppAndroidRecipe(CompiledComponentsPythonRecipe):
    name = 'llamacpp_android'
    version = '0.3.36'
    sha512sum = '97b00ab7eed4192e38c7e6da2a1fad493a338492d1f91c9787fa5e37e5e290ac7bca1584fea9a00c331655dcb0a40c8a988baf6a2586b962f13904115b0c6632'
    url = 'https://files.pythonhosted.org/packages/ec/e9/e7de2b0463ea3ffbf0ede6cb21b58c1258a8f6521aae45ca773a59fe7cf3/llama_cpp_python-0.3.36.tar.gz'
    depends = ['setuptools', 'numpy', 'opencl_link']
    site_packages_name = 'llama_cpp'
    call_hostpython_via_targetpython = False
    patches = ['patches/opencl-interactive.patch', 'patches/explicit-devices.patch']

    def patch_digest(self):
        return hashlib.sha256(b''.join((Path(__file__).parent/name).read_bytes()
                                      for name in self.patches)).hexdigest()

    def apply_patches(self, arch, build_dir=None):
        super().apply_patches(arch, build_dir)
        root=Path(build_dir or self.get_build_dir(arch.arch))
        # p4a's old .patched marker predates the additive Python API patch.
        if '_allma_explicit_devices' not in (root/'llama_cpp/llama.py').read_text():
            self.apply_patch(self.patches[1],arch.arch,build_dir=str(root))

    def should_build(self, arch):
        target = Path(self.ctx.get_python_install_dir(arch.arch)) / 'llama_cpp'
        try:
            metadata = json.loads((target / 'allma_runtime.json').read_text())
            manifest=json.loads((Path(__file__).parents[2]/'native_backend/hexagon/manifest.json').read_text())
            return (metadata.get('runtime_id') != 'allma-cpu-opencl-hexagon-v3'
                    or metadata.get('patch_set_sha256') != self.patch_digest()
                    or metadata.get('hexagon') != manifest
                    or not (target / 'libggml-opencl.so').is_file()
                    or any(hashlib.sha256((target/name).read_bytes()).hexdigest()!=digest
                           for name,digest in manifest['files'].items()))
        except (OSError, ValueError):
            return True

    def build_arch(self, arch):
        root = Path(self.get_build_dir(arch.arch))
        source = root/'vendor'/'llama.cpp'
        # Fail early rather than shipping an engine which cannot load the model.
        if 'qwen35' not in (source/'src'/'llama-arch.cpp').read_text():
            raise RuntimeError('Pinned runtime does not support Qwen 3.5')
        output = root/'build-allma-accelerated'
        headers = Recipe.get_recipe('opencl_headers', self.ctx).get_build_dir(arch.arch)
        link_root = Recipe.get_recipe('opencl_link', self.ctx).get_build_dir(arch.arch)
        link_library = Path(link_root) / 'allma-link-build/loader/libOpenCL.so'
        env = self.get_recipe_env(arch)
        # Cross flags from PythonRecipe are for Python extensions, not this C ABI.
        for variable in ('CFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CMAKE_ARGS', 'SKBUILD_CMAKE_ARGS'):
            env.pop(variable, None)
        subprocess.run(['cmake', '-S', str(source), '-B', str(output),
            '-DCMAKE_TOOLCHAIN_FILE='+self.ctx.ndk_dir+'/build/cmake/android.toolchain.cmake',
            '-DANDROID_ABI='+arch.arch, '-DANDROID_PLATFORM=android-24',
            '-DANDROID_STL=c++_shared',
            '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON',
            '-DGGML_NATIVE=OFF', '-DGGML_OPENMP=OFF', '-DGGML_CPU_ARM_ARCH=armv8-a',
            '-DGGML_CPU_KLEIDIAI=OFF', '-DGGML_VULKAN=OFF', '-DGGML_HEXAGON=OFF',
            '-DGGML_OPENCL=ON', '-DGGML_BACKEND_DL=ON',
            '-DOpenCL_INCLUDE_DIR='+headers, '-DOpenCL_LIBRARY='+str(link_library),
            '-DLLAMA_BUILD_COMMON=OFF', '-DLLAMA_BUILD_TESTS=OFF',
            '-DLLAMA_BUILD_EXAMPLES=OFF', '-DLLAMA_BUILD_TOOLS=OFF',
            '-DLLAMA_BUILD_APP=OFF', '-DLLAMA_BUILD_SERVER=OFF',
            '-DLLAMA_CURL=OFF', '-DLLAMA_HTTPLIB=OFF'], env=env, check=True)
        subprocess.run(['cmake', '--build', str(output), '--parallel', '4',
                        '--target', 'llama'], env=env, check=True)
        target = Path(self.ctx.get_python_install_dir(arch.arch))/'llama_cpp'
        if target.exists():
            shutil.rmtree(target)  # Generated package only; avoid stale backend ABI.
        shutil.copytree(root/'llama_cpp', target, ignore=shutil.ignore_patterns('__pycache__'))
        libraries = {p.name:p for p in output.rglob('*.so') if p.name.startswith(('libllama', 'libggml'))}
        required = {'libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libggml-opencl.so'}
        if not required.issubset(libraries):
            raise RuntimeError('Incomplete native runtime: '+str(required-libraries.keys()))
        for name, path in libraries.items():
            shutil.copy2(path, target/name)
        optional=Path(__file__).parents[2]/'native_backend/hexagon'
        hexagon=json.loads((optional/'manifest.json').read_text())
        if hexagon['source_commit'] != '0c1e57098bba43ac29e6e3b677cdceebdd22334f':
            raise RuntimeError('Hexagon must match the pinned llama.cpp source')
        for name,digest in hexagon['files'].items():
            payload=(optional/name).read_bytes()
            if hashlib.sha256(payload).hexdigest()!=digest:
                raise RuntimeError('Hexagon component checksum mismatch: '+name)
            (target/name).write_bytes(payload)
        shutil.copy2(optional/'LICENSE.txt',target/'HEXAGON-LICENSE.txt')
        # Both the legacy wrapper and newer Python package resolve this directory.
        extension = target/'_ctypes_extensions.py'
        text = extension.read_text().replace(
            'sys.platform.startswith("freebsd")',
            '(sys.platform.startswith("freebsd") or sys.platform.startswith("android"))')
        extension.write_text(text)
        binding = target/'llama_cpp.py'
        text = binding.read_text().replace(
            'pathlib.Path(os.path.abspath(os.path.dirname(__file__))) / "lib"',
            'pathlib.Path(os.path.abspath(os.path.dirname(__file__)))')
        binding.write_text(text)
        (target/'allma_runtime.json').write_text(json.dumps({
            'python_version':self.version, 'architecture':arch.arch,
            'source_sha256':'832db0699007f1be95a7e41ef12e88926b02ba836461e36a36372db2760c1a2e',
            'runtime_id':'allma-cpu-opencl-hexagon-v3', 'dynamic_backends':True,
            'explicit_devices':True, 'hexagon':hexagon,
            'patch_set_sha256':self.patch_digest(),
            'interactive_scheduling':True,
            'patch_sha256':hashlib.sha256((Path(__file__).parent / self.patches[0]).read_bytes()).hexdigest(),
            'opencl_link_version':'2025.07.22',
            'backends':['CPU', 'OpenCL', 'Hexagon'], 'qwen35':True}))


recipe = LlamacppAndroidRecipe()
