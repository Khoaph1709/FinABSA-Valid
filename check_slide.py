from pathlib import Path
import re
import sys

root = Path('/home/ubuntu/FinABSA-Valid')
tex_path = root / 'slide.tex'
text = tex_path.read_text(encoding='utf-8')
errors = []
checks = []

for required in [r'\usepackage[utf8]{inputenc}', r'\usepackage[T5]{fontenc}']:
    ok = required in text
    checks.append((f'contains {required}', ok))
    if not ok:
        errors.append(f'Missing {required}')

for banned in ['fontspec', 'polyglossia', 'xelatex', 'lualatex', 'images/']:
    ok = banned not in text.lower()
    checks.append((f'no {banned}', ok))
    if not ok:
        errors.append(f'Unexpected dependency/path: {banned}')

begins = len(re.findall(r'\\begin\{frame\}', text))
ends = len(re.findall(r'\\end\{frame\}', text))
checks.append((f'frame environments balanced ({begins}/{ends})', begins == ends and begins == 12))
if begins != ends or begins != 12:
    errors.append(f'Frame count mismatch: begins={begins}, ends={ends}')

figures = re.findall(r'\{((?:2019|2020|2021|2022)-10/analysis/figures/[^}]+\.png)\}', text)
checks.append((f'found eight period figure references ({len(figures)})', len(figures) == 8))
if len(figures) != 8:
    errors.append(f'Expected 8 figure references, found {len(figures)}')
for fig in figures:
    ok = (root / fig).is_file()
    checks.append((f'figure exists: {fig}', ok))
    if not ok:
        errors.append(f'Missing figure: {fig}')

for label, ok in checks:
    print(('PASS' if ok else 'FAIL') + ' | ' + label)

if errors:
    print('\nERRORS:')
    print('\n'.join(errors))
    sys.exit(1)
print('\nStatic check passed.')
