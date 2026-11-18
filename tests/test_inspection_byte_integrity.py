"""Adversarial Git-index/content controls; all mutations are confined to tmp repos."""
from pathlib import Path
import os
import subprocess

import pytest
from scripts import inspection_provenance as provenance


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    for name in ('src/model.py', 'scripts/runner.py', 'tests/admission_shim.py'):
        path = root / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b'VALUE = 1\n')
    (root / '.gitattributes').write_text('*.py text eol=crlf\n')
    (root / '.gitignore').write_text('ignored.py\n__pycache__/\n')
    git(root, 'init', '-q')
    git(root, 'config', 'user.email', 'test@example.invalid')
    git(root, 'config', 'user.name', 'Provenance test')
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'trusted content')
    try:
        yield root
    finally:
        # Restore only this fixture's disposable repository, including failures
        # and skips. No user checkout's flags or files are ever touched.
        assert root.resolve().parent == tmp_path.resolve()
        for flag in ('--no-assume-unchanged', '--no-skip-worktree'):
            git(root, 'update-index', flag, '--', 'src/model.py',
                'scripts/runner.py', 'tests/admission_shim.py')
        git(root, 'restore', '--source=HEAD', '--staged', '--worktree', '--', '.')


def identity(root, target):
    if target == 'scripts/runner.py':
        return provenance.inspector_identity(root / target, (target,))
    return provenance.model_identity(root, (str(Path(target).parent),))


@pytest.mark.parametrize('target', ['src/model.py', 'scripts/runner.py', 'tests/admission_shim.py'])
@pytest.mark.parametrize('flag', ['--assume-unchanged', '--skip-worktree'])
@pytest.mark.parametrize('modified', [False, True])
def test_reject_index_flags_even_when_status_is_clean(checkout, target, flag, modified):
    git(checkout, 'update-index', flag, target)
    if modified:
        (checkout / target).write_bytes(b'VALUE = 900\n')
    assert git(checkout, 'status', '--porcelain') == ''
    with pytest.raises(provenance.ProvenanceError, match='index flag'):
        identity(checkout, target)


@pytest.mark.parametrize('target', ['src/model.py', 'scripts/runner.py', 'tests/admission_shim.py'])
def test_reject_normal_tracked_mutation(checkout, target):
    (checkout / target).write_bytes(b'VALUE = 900\n')
    with pytest.raises(provenance.ProvenanceError):
        identity(checkout, target)


def test_clean_windows_crlf_checkout(checkout):
    for path in checkout.rglob('*.py'):
        path.write_bytes(b'VALUE = 1\r\n')
    # Refresh cached stat data after Git normalizes the equivalent CRLF bytes.
    git(checkout, 'add', '--renormalize', '.')
    assert git(checkout, 'status', '--porcelain') == ''
    provenance.model_identity(checkout, ('src', 'tests/admission_shim.py'))
    provenance.inspector_identity(checkout / 'scripts/runner.py', ('scripts/runner.py',))


def test_reject_ignored_untracked_executable(checkout):
    (checkout / 'src/ignored.py').write_text('VALUE = 900\n')
    assert git(checkout, 'status', '--porcelain') == ''
    with pytest.raises(provenance.ProvenanceError, match='untracked'):
        provenance.model_identity(checkout, ('src',))


def test_reject_missing_scoped_input(checkout):
    (checkout / 'src/model.py').unlink()
    with pytest.raises(provenance.ProvenanceError):
        provenance.model_identity(checkout, ('src',))


def test_actual_blob_comparison_does_not_depend_on_status(checkout):
    (checkout / 'src/model.py').write_bytes(b'VALUE = 9\n')
    with pytest.raises(provenance.ProvenanceError, match='actual scoped bytes'):
        provenance._verify_scoped_content(checkout, ('src',), git(checkout, 'rev-parse', 'HEAD'))


def test_clean_generated_distribution_metadata(checkout):
    metadata = checkout / 'src/model.egg-info'
    metadata.mkdir()
    (metadata / 'PKG-INFO').write_text('Metadata-Version: 2.1\n')
    (metadata / 'top_level.txt').write_text('model\n')
    # Match the standard install's ignored metadata without hiding executable code.
    with (checkout / '.gitignore').open('a') as handle:
        handle.write('*.egg-info/\n')
    git(checkout, 'add', '.gitignore')
    git(checkout, 'commit', '-qm', 'ignore build metadata')
    provenance.model_identity(checkout, ('src',))
    (metadata / 'evil.py').write_text('VALUE = 900\n')
    with pytest.raises(provenance.ProvenanceError, match='untracked'):
        provenance.model_identity(checkout, ('src',))


def test_reject_scope_without_committed_inputs(checkout):
    with pytest.raises(provenance.ProvenanceError, match='committed'):
        provenance.model_identity(checkout, ('missing.py',))


def test_reject_in_root_hardlink_substitution(checkout):
    target = checkout / 'src/model.py'
    original = checkout / 'original.py'
    target.rename(original)
    os.link(original, target)
    with pytest.raises(provenance.ProvenanceError, match='link'):
        provenance.model_identity(checkout, ('src',))
    with pytest.raises(provenance.ProvenanceError, match='link'):
        provenance.verified_file_identity(target)


def test_reject_in_root_symlink_substitution(checkout):
    target = checkout / 'src/model.py'
    original = checkout / 'original.py'
    target.rename(original)
    try:
        target.symlink_to(original)
    except OSError as error:
        pytest.skip('Host does not permit creation of symlinks: ' + str(error))
    # Public validation can reject the earlier Git type-change before reaching
    # the byte checker; both paths must refuse the actual substitution.
    with pytest.raises(provenance.ProvenanceError):
        provenance.model_identity(checkout, ('src',))
    with pytest.raises(provenance.ProvenanceError, match='link|substitution'):
        provenance._verify_scoped_content(checkout, ('src',), git(checkout, 'rev-parse', 'HEAD'))
