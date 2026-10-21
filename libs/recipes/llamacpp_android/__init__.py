"""Build a matched Python/native runtime from the same pinned source archive.

CPU-only intentionally matches the app's stable Android execution policy.
No unrelated llama.cpp checkout or host-built wheel may replace its ABI.
"""
from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from pathlib import Path
import json
import shutil
import subprocess


class LlamacppAndroidRecipe(CompiledComponentsPythonRecipe):
    name = 'llamacpp_android'
    version = '0.3.36'
    sha512sum = '97b00ab7eed4192e38c7e6da2a1fad493a338492d1f91c9787fa5e37e5e290ac7bca1584fea9a00c331655dcb0a40c8a988baf6a2586b962f13904115b0c6632'
    url = 'https://files.pythonhosted.org/packages/ec/e9/e7de2b0463ea3ffbf0ede6cb21b58c1258a8f6521aae45ca773a59fe7cf3/llama_cpp_python-0.3.36.tar.gz'
    depends = ['setuptools', 'numpy']
    site_packages_name = 'llama_cpp'
    call_hostpython_via_targetpython = False

    def build_arch(self, arch):
        root = Path(self.get_build_dir(arch.arch))
        source = root/'vendor'/'llama.cpp'
        # Fail early rather than shipping an engine which cannot load the model.
        if 'qwen35' not in (source/'src'/'llama-arch.cpp').read_text():
            raise RuntimeError('Pinned runtime does not support Qwen 3.5')
        output = root/'build-allma-cpu'
        env = self.get_recipe_env(arch)
        # Cross flags from PythonRecipe are for Python extensions, not this C ABI.
        for variable in ('CFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CMAKE_ARGS', 'SKBUILD_CMAKE_ARGS'):
            env.pop(variable, None)
        subprocess.run(['cmake', '-S', str(source), '-B', str(output),
            '-DCMAKE_TOOLCHAIN_FILE='+self.ctx.ndk_dir+'/build/cmake/android.toolchain.cmake',
            '-DANDROID_ABI='+arch.arch, '-DANDROID_PLATFORM=android-24',
            '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON',
            '-DGGML_NATIVE=OFF', '-DGGML_OPENMP=OFF', '-DGGML_CPU_ARM_ARCH=armv8-a',
            '-DGGML_CPU_KLEIDIAI=OFF', '-DGGML_VULKAN=OFF', '-DGGML_OPENCL=OFF',
            '-DLLAMA_BUILD_COMMON=OFF', '-DLLAMA_BUILD_TESTS=OFF',
            '-DLLAMA_BUILD_EXAMPLES=OFF', '-DLLAMA_BUILD_TOOLS=OFF',
            '-DLLAMA_CURL=OFF', '-DLLAMA_HTTPLIB=OFF'], env=env, check=True)
        subprocess.run(['cmake', '--build', str(output), '--parallel', '4',
                        '--target', 'llama'], env=env, check=True)
        target = Path(self.ctx.get_python_install_dir(arch.arch))/'llama_cpp'
        if target.exists():
            shutil.rmtree(target)  # Generated package only; avoid stale backend ABI.
        shutil.copytree(root/'llama_cpp', target, ignore=shutil.ignore_patterns('__pycache__'))
        libraries = {p.name:p for p in output.rglob('*.so') if p.name.startswith(('libllama', 'libggml'))}
        required = {'libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so'}
        if not required.issubset(libraries):
            raise RuntimeError('Incomplete native runtime: '+str(required-libraries.keys()))
        for name, path in libraries.items():
            shutil.copy2(path, target/name)
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
            'backends':['CPU'], 'qwen35':True}))


recipe = LlamacppAndroidRecipe()
