# Kamdzy - run the repo's tests (or a Python snippet) under the NKAS runtime interpreter
# without touching the install. The toolkit Python is embedded and runs in ._pth mode with
# the install dir hardcoded, so it would import C:\Tools\NKAS\module (stale) instead of this
# checkout, including in child processes the tests spawn. This copies the interpreter
# binaries into a temp dir next to a ._pth that points at the repo, reuses the toolkit's
# site-packages read-only, and installs pytest beside it. Rebuilt per run on purpose: a
# cached copy in %TEMP% gets half-deleted by cleanup and then imports as empty packages.
#
#   python dev_tools/run_tests.py tests/ -q                     -> python -m pytest tests/ -q
#   python dev_tools/run_tests.py --run -c "import module.shop"  -> python -c "import module.shop"
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(toolkit, root):
    pth_files = glob.glob(os.path.join(toolkit, 'python*._pth'))
    if len(pth_files) != 1:
        sys.exit(f'expected one python*._pth in {toolkit}, found {pth_files}')
    pth_name = os.path.basename(pth_files[0])
    py = os.path.join(root, 'py')
    os.makedirs(os.path.join(py, 'Lib', 'site-packages'))
    for entry in os.scandir(toolkit):
        if entry.is_file() and entry.name != pth_name:
            shutil.copy2(entry.path, py)
    with open(os.path.join(py, pth_name), 'w') as f:
        f.write('\n'.join([pth_name.replace('._pth', '.zip'), '.', REPO, 'import site']) + '\n')

    pytest_dir = os.path.join(root, 'pytest')
    # --no-deps + explicit deps: pytest would otherwise pull a newer `packaging` into the
    # target dir (shadowed at runtime anyway) and pip warns it breaks the toolkit's langchain.
    subprocess.run([os.path.join(toolkit, 'python.exe'), '-m', 'pip', 'install', '--quiet',
                    '--disable-pip-version-check', '--no-deps', '--target', pytest_dir,
                    'pytest', 'pluggy', 'iniconfig', 'exceptiongroup', 'tomli'], check=True)
    # addsitedir (not a plain path entry) so pywin32.pth etc. in the toolkit are processed;
    # pytest's dir comes after, so the toolkit's pinned packages (e.g. packaging) win.
    site_packages = os.path.join(toolkit, 'Lib', 'site-packages')
    with open(os.path.join(py, 'Lib', 'site-packages', 'toolkit.pth'), 'w') as f:
        f.write(f'import site; site.addsitedir(r"{site_packages}")\n{pytest_dir}\n')
    return os.path.join(py, 'python.exe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolkit', default=r'C:\Tools\NKAS\toolkit', help='NKAS toolkit dir (embedded Python)')
    parser.add_argument('--run', action='store_true', help='pass remaining args to python instead of pytest')
    args, rest = parser.parse_known_args()
    with tempfile.TemporaryDirectory(prefix='nkas-test-') as root:
        python = build(args.toolkit, root)
        cmd = [python, *rest] if args.run else [python, '-m', 'pytest', '-p', 'no:cacheprovider', *rest]
        env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
        return subprocess.run(cmd, cwd=REPO, env=env).returncode


if __name__ == '__main__':
    sys.exit(main())
