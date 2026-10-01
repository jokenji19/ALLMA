import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('host_support', ROOT / 'libs/recipes/host_build_support.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


@pytest.mark.parametrize('selected,obsolete', [('84.0', '65.5'), ('65.5', '84.0')])
def test_pip_receipt_selects_metadata_for_upgrade_and_downgrade(tmp_path, selected, obsolete):
    site = tmp_path / 'site-packages'
    for version in [selected, obsolete]:
        metadata = site / f'setuptools-{version}.dist-info/METADATA'
        metadata.parent.mkdir(parents=True)
        metadata.write_text(f'Name: setuptools\nVersion: {version}\n')
    other = site / 'other-1.dist-info/METADATA'
    other.parent.mkdir()
    other.write_text('Name: other\nVersion: 1\n')
    support.archive_stale_metadata(site, {'setuptools': selected})
    assert (site / f'setuptools-{selected}.dist-info/METADATA').exists()
    assert not (site / f'setuptools-{obsolete}.dist-info').exists()
    assert other.exists()
    assert len(list(tmp_path.glob(f'allma-old-metadata-*/setuptools-{obsolete}.dist-info/METADATA'))) == 1
