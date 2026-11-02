# Kamdzy - rebuild config/notices.yaml in English during an upstream merge. Upstream notices
# always arrive in zh-CN and upstream reshapes the file freely (e.g. nesting older notices
# under a pinned "notice_history" entry's items), so hunk-merging it is error-prone. This
# takes the STRUCTURE (ids, dates, pinned/type, nesting, order) verbatim from upstream --
# ReadNoticeIds in config/deploy.yaml keys off the ids -- and the TEXT from the fork:
#   - an id whose upstream zh-CN title/content is unchanged since the merge base reuses the
#     fork's English as-is;
#   - a new id, or one upstream edited (a stale translation otherwise), must come from
#     --translations (YAML: {id: {title: ..., content: ...}}, plus optional `header: [lines]`).
# Without a translation for every such id nothing is written: it prints the zh-CN source
# and the current English for each and exits 1. On success it validates the written file
# (structure == upstream, no zh-CN left outside --allow) and exits 0.
#
#   python dev_tools/merge_notices.py                          # list what needs translating
#   python dev_tools/merge_notices.py --translations new.yaml  # write + validate
import argparse
import os
import re
import subprocess
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = 'config/notices.yaml'
HAN = re.compile(r'[一-鿿]')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args], capture_output=True, check=True).stdout.decode('utf-8')


def load(ref):
    return yaml.safe_load(git('show', f'{ref}:{PATH}'))


def header(ref):
    """Comment lines above the first entry."""
    lines = []
    for line in git('show', f'{ref}:{PATH}').replace('\r\n', '\n').split('\n'):
        if line.startswith('- '):
            break
        lines.append(line)
    return [line for line in lines if line.strip()]


def flat(entries):
    for e in entries:
        yield e
        yield from flat(e.get('items', []))


def text(entries):
    return {e['id']: (e['title'], e.get('content')) for e in flat(entries)}


def skeleton(entries):
    return [{k: (skeleton(v) if k == 'items' else v) for k, v in e.items() if k not in ('title', 'content')}
            for e in entries]


def block(value):
    return '\n'.join('    ' + line for line in (value or '').rstrip('\n').split('\n'))


def scalar(value):
    if any(c in value for c in ':#"\'') or value[:1] in '[]{}&*!|>%@`-?,':
        return "'" + value.replace("'", "''") + "'"
    return value


def emit(entry, indent, english):
    pad = ' ' * indent
    title, content = english[entry['id']]
    out = []
    for i, (key, value) in enumerate(entry.items()):
        lead = pad + ('- ' if i == 0 else '  ')
        if key == 'title':
            out.append(f'{lead}title: {scalar(title)}')
        elif key == 'content':
            out.append(f'{lead}content: |')
            out += [(pad + '    ' + line) if line else '' for line in content.rstrip('\n').split('\n')]
        elif key == 'items':
            out.append(f'{lead}items:')
            for item in value:
                out += emit(item, indent + 4, english)
        elif isinstance(value, bool):
            out.append(f'{lead}{key}: {str(value).lower()}')
        else:
            out.append(f'{lead}{key}: {value}')
    return out


def main():
    parser = argparse.ArgumentParser(description='Rebuild config/notices.yaml in English on upstream structure.')
    parser.add_argument('--upstream', default='upstream/master')
    parser.add_argument('--fork', default='HEAD')
    parser.add_argument('--translations', help='YAML {id: {title, content}} (+ optional header: [lines])')
    parser.add_argument('--allow', nargs='*', default=['不会起名字'], help='zh-CN strings allowed to remain (names)')
    args = parser.parse_args()

    base = git('merge-base', args.fork, args.upstream).strip()
    up, up_base, fork = load(args.upstream), load(base), load(args.fork)
    up_text, base_text, fork_text = text(up), text(up_base), text(fork)
    given = yaml.safe_load(open(args.translations, encoding='utf-8')) if args.translations else {}
    given = given or {}

    english, todo = {}, []
    for entry_id, zh in up_text.items():
        if entry_id in given:
            english[entry_id] = (given[entry_id]['title'], given[entry_id].get('content'))
        elif entry_id in fork_text and base_text.get(entry_id) == zh:
            english[entry_id] = fork_text[entry_id]
        else:
            todo.append((entry_id, 'edited upstream' if entry_id in fork_text else 'new', zh, fork_text.get(entry_id)))

    head_changed = header(base) != header(args.upstream)
    head = given.get('header') or (None if head_changed else header(args.fork))

    if todo or head is None:
        if head is None:
            print('NEEDS header (upstream changed it):\n  ' + '\n  '.join(header(args.upstream)))
            print('  current English:\n  ' + '\n  '.join(header(args.fork)))
        for entry_id, why, zh, en in todo:
            print(f'\nNEEDS {entry_id} ({why})\n  zh title: {zh[0]}')
            print('  zh content:\n' + block(zh[1]))
            if en:
                print(f'  current English title: {en[0]}')
                print('  current English content:\n' + block(en[1]))
        print(f'\n{len(todo)} entr{"y" if len(todo) == 1 else "ies"} need translation; nothing written.')
        return 1

    lines = list(head)
    for entry in up:
        lines += emit(entry, 0, english)
    target = os.path.join(REPO, PATH)
    raw = open(target, encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in raw else '\n'
    open(target, 'w', encoding='utf-8', newline='').write(eol.join(lines) + eol)

    written = yaml.safe_load(open(target, encoding='utf-8'))
    same = skeleton(written) == skeleton(up)
    allowed = re.compile('|'.join(map(re.escape, args.allow))) if args.allow else None

    def has_zh(entry):
        value = entry['title'] + (entry.get('content') or '')
        return HAN.search(allowed.sub('', value) if allowed else value)

    left = [e['id'] for e in flat(written) if has_zh(e)]
    print(f'wrote {PATH}: {len(lines)} lines; structure identical to upstream: {same}; '
          f'reused {sum(1 for i in up_text if i not in given)}, translated {len(given) - ("header" in given)}; '
          f'zh-CN left in: {left or "none"}')
    return 0 if same and not left else 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
