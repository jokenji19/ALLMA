"""Keep metadata consistent with wheels installed into p4a's host Python."""
import json
import tempfile
from email.parser import Parser
from pathlib import Path
from packaging.utils import canonicalize_name


def archive_stale_metadata(site_dir, installed):
    """Archive superseded metadata, using pip's receipt rather than version order."""
    site = Path(site_dir)
    archive = None
    for metadata in site.glob('*.dist-info/METADATA'):
        fields = Parser().parsestr(metadata.read_text(encoding='utf-8'))
        name = canonicalize_name(fields.get('Name', ''))
        if name in installed and fields.get('Version') != installed[name]:
            if archive is None:
                archive = Path(tempfile.mkdtemp(prefix='allma-old-metadata-', dir=site.parent))
            metadata.parent.rename(archive / metadata.parent.name)


class HostBuildPrerequisites:
    def install_hostpython_prerequisites(self, packages=None, force_upgrade=True):
        from pythonforandroid.logger import shprint
        packages = packages or self.hostpython_prerequisites
        if not packages:
            return
        # pip --target --upgrade replaces package code but can retain dist-info
        # from earlier versions, causing PEP 517 to see the wrong dependency.
        with tempfile.TemporaryDirectory(prefix='allma-pip-report-') as temporary:
            report = Path(temporary) / 'installed.json'
            options = ['install', *packages, '--target', self._host_recipe.site_dir,
                       '--python-version', self.ctx.python_recipe.version,
                       '--only-binary=:all:', '--report', str(report)]
            if force_upgrade:
                options.append('--upgrade')
            shprint(self._host_recipe.pip, *options, _env=self.get_hostrecipe_env())
            installed = {canonicalize_name(item['metadata']['name']): item['metadata']['version']
                         for item in json.loads(report.read_text())['install']}
            archive_stale_metadata(self._host_recipe.site_dir, installed)
