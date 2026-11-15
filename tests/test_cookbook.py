"""Run every ```js recipe in docs/QUERY-COOKBOOK.md against the packs in this repo.

A recipe passes when node exits 0 and prints something. Sample output in the doc is
illustrative (counts move with the weekly refresh), so it is not compared.

    python3 tests/test_cookbook.py            run all recipes
    python3 tests/test_cookbook.py --show     also print each recipe's output
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DOC = os.path.join(ROOT, 'docs', 'QUERY-COOKBOOK.md')


def recipes():
    text = open(DOC, encoding='utf-8').read()
    # (heading, code) pairs, in document order
    out = []
    heading = ''
    for part in re.split(r'(?m)^(## .+)$', text):
        if part.startswith('## '):
            heading = part[3:].strip()
            continue
        if heading == 'Setup':
            continue  # the shared preamble; every recipe repeats it
        for code in re.findall(r'```js\n(.*?)```', part, re.S):
            out.append((heading, code))
    return out


def main():
    show = '--show' in sys.argv
    found = recipes()
    failures = []
    if len(found) < 10:
        failures.append(f'expected at least 10 runnable recipes, found {len(found)}')
    with tempfile.TemporaryDirectory() as tmp:
        for n, (heading, code) in enumerate(found, 1):
            path = os.path.join(tmp, f'recipe{n}.mjs')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(code)
            run = subprocess.run(['node', path], cwd=ROOT, capture_output=True,
                                 text=True, timeout=120)
            ok = run.returncode == 0 and run.stdout.strip() != ''
            print(f"{'ok  ' if ok else 'FAIL'} {heading}")
            if show:
                print('\n'.join('     ' + l for l in run.stdout.splitlines()))
            if not ok:
                failures.append(f'{heading}: exit {run.returncode}\n{run.stderr[-600:]}')
    if failures:
        print('\n'.join(failures))
        sys.exit(1)
    print(f'{len(found)} recipes passed')


if __name__ == '__main__':
    main()
