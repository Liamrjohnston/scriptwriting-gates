#!/usr/bin/env python3
"""Read-only portable package checks; no customer inputs or network required."""
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'scriptwriting-gates'


def check(root=ROOT):
    root = Path(root).resolve()
    skill = root / 'skills' / 'scriptwriting-gates'
    errors = []
    required = ['SKILL.md', 'LICENSE', 'NOTICE.md', 'agents/openai.yaml',
                'references/workflow.md', 'references/gates.md',
                'references/humanizer.md', 'references/packet-contract.md',
                'references/packet-template.json', 'scripts/validate.py']
    for name in required:
        file = skill / name
        if not file.is_file() or not file.read_text().strip():
            errors.append('Missing/empty skill resource: ' + name)
    if errors:
        return errors
    entry = (skill / 'SKILL.md').read_text()
    if not entry.startswith('---\n') or not re.search(r'^name: scriptwriting-gates$', entry, re.M):
        errors.append('Skill discovery metadata is missing')
    if not re.search(r'^description: .+', entry, re.M):
        errors.append('Skill description is empty')
    gates = (skill / 'references/gates.md').read_text()
    for prefix, count in [('G', 30), ('H', 4), ('D', 7)]:
        actual = re.findall(r'^\| (' + prefix + r'\d+) \|', gates, re.M)
        if actual != [f'{prefix}{i}' for i in range(1, count + 1)]:
            errors.append(prefix + ' register is missing/duplicate/out of order')
    humanizer = (skill / 'references/humanizer.md').read_text()
    if re.findall(r'^### (\d+)\.', humanizer, re.M) != [str(i) for i in range(1, 34)]:
        errors.append('Humanizer roster is not exactly 1–33')
    try:
        packet = json.loads((skill / 'references/packet-template.json').read_text())
        for key, expected in [('gates', [f'G{i}' for i in range(1, 31)]),
                              ('hook_checks', [f'H{i}' for i in range(1, 5)]),
                              ('desire_checks', [f'D{i}' for i in range(1, 8)]),
                              ('humanizer', list(range(1, 34)))]:
            if [row['id'] for row in packet[key]] != expected:
                errors.append('Template register mismatch: ' + key)
        if packet['spoken_script'] or any(row['status'] != 'BLOCKED' for row in packet['gates']):
            errors.append('Template must remain visibly unfinished, not a passing campaign')
    except (ValueError, KeyError, TypeError):
        errors.append('Invalid packet template')
    forbidden = [r'/(?:Users|home)/[^/\s]+/', r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
                 r'\b(?:ghp_|sk_live_|xoxb-)[A-Za-z0-9-]{12,}',
                 r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----']
    for file in sorted(root.rglob('*')):
        if not file.is_file() or any(p.startswith('.') and p not in {'.github'} for p in file.relative_to(root).parts[:-1]):
            continue
        if '__pycache__' in file.parts or file.suffix not in {'.md', '.py', '.json', '.yaml', '.yml'}:
            continue
        contents = file.read_text()
        for pattern in forbidden:
            if re.search(pattern, contents, re.I):
                errors.append('Potential private material: ' + str(file.relative_to(root)))
        if file.suffix == '.md':
            # Remove fenced examples before resolving executable/documentation links.
            prose = re.sub(r'```.*?```', '', contents, flags=re.S)
            for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', prose):
                if urlsplit(target).scheme or target.startswith('#'):
                    continue
                destination = (file.parent / unquote(target.split('#')[0])).resolve()
                if not destination.is_relative_to(root) or not destination.exists():
                    errors.append('Broken/outside package link: ' + str(file.relative_to(root)) + ' → ' + target)
    return sorted(set(errors))


if __name__ == '__main__':
    problems = check()
    print(json.dumps({'package_valid': not problems, 'findings': problems}, indent=2))
    sys.exit(1 if problems else 0)
