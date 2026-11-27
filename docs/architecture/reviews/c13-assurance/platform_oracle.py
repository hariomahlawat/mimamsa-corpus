"""Cross-host baseline checks for the R1 path, parse and exact-byte interfaces."""
import argparse
import importlib
import json
import platform
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath

FIXTURES = json.loads(Path(__file__).with_name('platform-fixtures.json').read_text(encoding='utf-8'))
CANONICAL_BYTES = (
    '{"copy":"SYNTH-001","issued_at":"2031-01-02T03:04:05Z",'
    '"pages":[1,3],"title":"नमूना"}\n'
).encode('utf-8')
SYNTHETIC_HASH = '01b06fa6493cfd8127eea645cfb8077e370e80254df81ee01e5785106cc4725a'


def load_contract(path):
    sys.path.insert(0, str(path.resolve()))
    return (
        importlib.import_module('mimamsa_contract.paths'),
        importlib.import_module('mimamsa_contract.bundle'),
    )


def tests(contract_dir):
    paths, bundle = load_contract(contract_dir)

    class PortabilityChecks(unittest.TestCase):
        def test_POR01_relative_paths_share_components(self):
            for value in FIXTURES['allowed_paths']:
                with self.subTest(value=value):
                    self.assertIsNone(paths.path_hazard(value))
                    parts = tuple(value.split('/'))
                    self.assertEqual(PurePosixPath(value).parts, parts)
                    self.assertEqual(PureWindowsPath(value).parts, parts)

        def test_POR02_case_alias_policy_independent_of_filesystem(self):
            for pair in FIXTURES['alias_pairs']:
                with self.subTest(pair=pair):
                    self.assertEqual(paths.case_collisions(pair), [tuple(pair)])
                    self.assertEqual(paths.case_collisions([pair[0], pair[0]]), [])

        def test_POR03_exact_utf8_identity_and_platform_neutral_parse(self):
            expected = FIXTURES['synthetic_record']
            encoded = (json.dumps(expected, sort_keys=True, separators=(',', ':'),
                                  ensure_ascii=False) + '\n').encode('utf-8')
            self.assertEqual(encoded, CANONICAL_BYTES)
            with tempfile.TemporaryDirectory() as directory:
                file = Path(directory) / 'synthetic.json'
                file.write_bytes(encoded)
                self.assertEqual(bundle.sha256_file(file), SYNTHETIC_HASH)
                self.assertEqual(bundle.strict_loads(file.read_text(encoding='utf-8')), expected)
                file.write_bytes(encoded.replace(b'\n', b'\r\n'))
                self.assertNotEqual(bundle.sha256_file(file), SYNTHETIC_HASH)

    return unittest.defaultTestLoader.loadTestsFromTestCase(PortabilityChecks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract-dir', required=True, type=Path,
                        help='app/contract from the pinned application snapshot')
    args = parser.parse_args()
    print(f'{platform.platform()} / Python {platform.python_version()}', flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(tests(args.contract_dir))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
