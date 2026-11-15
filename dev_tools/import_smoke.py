# Kamdzy - post-merge import smoke check. Upstream removed its whole tests/ suite (9e27c6c8),
# so after a merge this is the remaining behavioural gate: import every Python module the
# merge changed plus every task module main.py dispatches to, which catches missing names,
# broken or circular imports, and module-level errors from upstream refactors.
# Must run under the NKAS runtime interpreter against this checkout, i.e. via run_tests.py:
#
#   python dev_tools/run_tests.py --run dev_tools/import_smoke.py                # staged merge
#   python dev_tools/run_tests.py --run dev_tools/import_smoke.py --merge <sha>  # committed merge
#
# Exits 1 if any import fails.
import argparse
import importlib
import os
import re
import subprocess
import sys
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description='Import every module a merge changed plus main.py task modules.')
    parser.add_argument('--merge', help='committed merge to check (default: staged index vs HEAD)')
    args = parser.parse_args()

    diff = [f'{args.merge}^1', args.merge] if args.merge else ['--cached', 'HEAD']
    changed = subprocess.run(['git', '-C', REPO, 'diff', '--name-only', '--diff-filter=AMR', *diff, '--', '*.py'],
                             capture_output=True, text=True, check=True).stdout.split()
    mods = {p[:-3].replace('/', '.') for p in changed
            if p.startswith(('module/', 'deploy/')) and not p.endswith('__init__.py')}
    main_src = open(os.path.join(REPO, 'main.py'), encoding='utf-8').read()
    mods |= set(re.findall(r'^\s+from (module\.[\w.]+) import', main_src, re.M))

    failed = []
    for name in sorted(mods):
        try:
            importlib.import_module(name)
        except Exception:
            failed.append((name, traceback.format_exc().strip().splitlines()[-1]))
    print(f'imported {len(mods) - len(failed)}/{len(mods)} modules '
          f'({len(changed)} changed .py files + main.py task imports)')
    for name, error in failed:
        print(f'  FAIL {name}: {error}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
