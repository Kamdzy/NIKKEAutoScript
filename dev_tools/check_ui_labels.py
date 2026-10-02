# Kamdzy - audit run after every upstream merge: upstream adds zh-CN t('...') keys freely,
# and any key without a label for the target language renders as raw Chinese on the en-US
# client. Labels are collected from every `'key': { 'en-US': ... }` map under webui/src,
# not just i18n.ts, because some components keep their own local label tables.
import argparse
import pathlib
import re
import sys

HAN = re.compile(r'[一-鿿]')
LABEL = re.compile(r"'((?:[^'\\]|\\.)*)'\s*:\s*\{([^{}]*)\}")
CALL = re.compile(r"""\bt\(\s*(['"])((?:(?!\1)[^\\]|\\.)*)\1""")


def main():
    parser = argparse.ArgumentParser(description='List Chinese t() keys in the SPA that lack a label for a language.')
    parser.add_argument('--src', default=str(pathlib.Path(__file__).resolve().parent.parent / 'webui' / 'src'))
    parser.add_argument('--lang', default='en-US')
    args = parser.parse_args()
    src = pathlib.Path(args.src)
    files = [p for p in sorted(src.rglob('*')) if p.suffix in ('.vue', '.ts')]

    labelled = set()
    used = {}
    for path in files:
        text = path.read_text(encoding='utf-8')
        for m in LABEL.finditer(text):
            if f"'{args.lang}'" in m.group(2):
                labelled.add(m.group(1))
        for m in CALL.finditer(text):
            if HAN.search(m.group(2)):
                used.setdefault(m.group(2), set()).add(path.relative_to(src).as_posix())

    missing = {k: v for k, v in used.items() if k not in labelled}
    print(f'{len(used)} Chinese t() keys, {len(missing)} without a {args.lang} label')
    for key, where in sorted(missing.items()):
        print(f'  {key}  ({", ".join(sorted(where))})')
    return 1 if missing else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
