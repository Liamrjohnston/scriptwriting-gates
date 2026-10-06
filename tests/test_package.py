"""Package regressions use only disposable synthetic copies."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('package_check', HERE / 'check_package.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'package'
        shutil.copytree(HERE.parent, self.root, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        self.skill = self.root / 'skills/scriptwriting-gates'

    def tearDown(self):
        self.temp.cleanup()

    def test_real_package_is_self_contained(self):
        self.assertEqual(checker.check(self.root), [])

    def test_missing_reference_cannot_pass(self):
        (self.skill / 'references/workflow.md').unlink()
        self.assertTrue(checker.check(self.root))

    def test_duplicate_gate_cannot_pass(self):
        path = self.skill / 'references/gates.md'
        path.write_text(path.read_text() + '\n| G1 | fake | fake |\n')
        self.assertTrue(any('register' in x for x in checker.check(self.root)))

    def test_outside_link_cannot_pass(self):
        path = self.skill / 'SKILL.md'
        path.write_text(path.read_text() + '\n[External local file](../../../../../outside.md)\n')
        self.assertTrue(any('package link' in x for x in checker.check(self.root)))

    def test_accidental_email_shaped_data_is_flagged(self):
        (self.root / 'example.md').write_text('example' + '@' + 'example.invalid')
        self.assertTrue(any('private material' in x for x in checker.check(self.root)))

    def test_template_must_not_fake_completion(self):
        path = self.skill / 'references/packet-template.json'
        packet = json.loads(path.read_text())
        packet['spoken_script'] = 'Pretend this is a finished script.'
        path.write_text(json.dumps(packet))
        self.assertTrue(any('unfinished' in x for x in checker.check(self.root)))


if __name__ == '__main__':
    unittest.main()
