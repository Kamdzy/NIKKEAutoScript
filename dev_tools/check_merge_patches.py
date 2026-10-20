# Kamdzy - post-merge audit: for every file changed by BOTH the fork and upstream since their
# merge base, the merge result must differ from upstream only by the fork's own delta.
#   stray   = lines in the merge that are in neither upstream nor the fork's additions
#   lost    = upstream lines missing from the merge that the fork never removed
#   missing = lines the fork added that appear nowhere in the merged file (a dropped patch;
#             a patch upstream absorbed verbatim still passes, since the line is present)
# Marker counts (`git grep -c Kamdzy`) can't catch an auto-merge that kept the Kamdzy comment
# but lost or mangled the code under it; this can. Renames are followed (-M), so a fork patch
# carried into a moved file (rubbish_shop.py -> shop/rubbish.py) is checked at its new path.
#
#   python dev_tools/check_merge_patches.py               # in-progress merge: staged index vs upstream/master
#   python dev_tools/check_merge_patches.py --merge HEAD  # committed merge: REF vs REF^1 (fork) / REF^2 (upstream)
#
# An intentional drop (e.g. a fork patch upstream absorbed with different wording) shows as
# FLAG/missing -- review it, it is the cue to confirm the drop was deliberate. Exits 1 if anything is flagged.
import argparse
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Rebuilt artifacts / restructured-then-translated files are verified by other means.
DEFAULT_SKIP = ('webui/dist/', 'config/notices.yaml')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True, check=True).stdout.decode('utf-8', 'replace')


def changed(a, b):
    """{new_path: old_path} for files changed between a and b, following renames."""
    out = {}
    for line in git('diff', '-M', '--name-status', a, b).splitlines():
        parts = line.split('\t')
        out[parts[-1]] = parts[1] if parts[0].startswith('R') else parts[-1]
    return out


def delta(*args):
    plus, minus = set(), set()
    for line in git('diff', '-M', '-U0', *args).splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            plus.add(line[1:].strip())
        elif line.startswith('-') and not line.startswith('---'):
            minus.add(line[1:].strip())
    return plus - {''}, minus - {''}


def main():
    parser = argparse.ArgumentParser(description='Check fork patches survived an upstream merge.')
    parser.add_argument('--merge', help='committed merge to audit (default: the staged index of an in-progress merge)')
    parser.add_argument('--upstream', default='upstream/master', help='upstream ref when auditing the index')
    parser.add_argument('--skip', nargs='*', default=list(DEFAULT_SKIP), help='path prefixes to skip')
    args = parser.parse_args()

    if args.merge:
        fork, upstream = f'{args.merge}^1', f'{args.merge}^2'
        diff_to_merge = [upstream, args.merge]  # upstream -> committed merge
        blob_prefix = f'{args.merge}:'
        merged_tree = set(git('ls-tree', '-r', '--name-only', args.merge).splitlines())
    else:
        fork, upstream = 'HEAD', args.upstream
        diff_to_merge = ['--cached', upstream]  # upstream -> staged index
        blob_prefix = ':'
        merged_tree = set(git('ls-files').splitlines())
    mb = git('merge-base', fork, upstream).strip()

    fork_files = changed(mb, fork)
    up_files = changed(mb, upstream)
    up_renamed = {old: new for new, old in up_files.items()}
    both = sorted(f for f in fork_files if f in up_files or f in up_renamed)

    flagged = 0
    for f in both:
        if f.startswith(tuple(args.skip)):
            continue
        merged_path = up_renamed.get(f, f)
        f_plus, f_minus = delta(mb, fork, '--', f)
        extra, dropped = delta(*diff_to_merge, '--', merged_path)
        stray, lost = extra - f_plus, dropped - f_minus
        merged_lines = {line.strip() for line in git('show', blob_prefix + (merged_path)).splitlines()}
        missing = f_plus - merged_lines
        # A fork patch upstream absorbed while splitting a module lands in another file: if
        # every missing code line (comments excluded -- upstream never copies ours) shows up
        # in one other upstream-changed file, report MOVED instead of failing.
        relocated = None
        code = {line for line in missing if not line.startswith(('#', '//'))}
        if code and not stray and not lost:
            ext = os.path.splitext(merged_path)[1]
            candidates = [p for p in up_files if p in merged_tree and p != merged_path and p.endswith(ext)]
            for other in candidates:
                if code <= {
                        line.strip() for line in git('show', blob_prefix + (other)).splitlines()}:
                    relocated = other
                    break
        ok = not stray and not lost and not missing
        status = 'OK  ' if ok else 'MOVED' if relocated else 'FLAG'
        flagged += status == 'FLAG'
        moved = f' -> {merged_path}' if merged_path != f else ''
        print(f"{status} {f}{moved}  "
              f"(fork +{len(f_plus)}/-{len(f_minus)}, merge-vs-upstream +{len(extra)}/-{len(dropped)})")
        for line in sorted(stray)[:8]:
            print(f'       stray + {line[:120]}')
        for line in sorted(lost)[:8]:
            print(f'       lost  - {line[:120]}')
        if relocated:
            print(f'       fork patch now lives in {relocated} (upstream absorbed it); '
                  f'{len(missing - code)} fork comment line(s) dropped with it')
        else:
            for line in sorted(missing)[:8]:
                print(f'       missing fork line: {line[:120]}')
    print(f'\n{len(both)} files changed on both sides, {flagged} flagged')
    return 1 if flagged else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
