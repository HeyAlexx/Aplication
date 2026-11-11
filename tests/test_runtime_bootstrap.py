"""Archive safety checks use synthetic ZIPs and never download or execute a runtime."""
import hashlib
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from bootstrap_php import extract_verified


class RuntimeArchiveTests(unittest.TestCase):
    def archive(self, names):
        temporary = tempfile.TemporaryDirectory(prefix='altoids-runtime-archive-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        archive = root / 'runtime.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            for item in names:
                if isinstance(item, str) and '\\' in item:
                    raw = zipfile.ZipInfo('raw-name')
                    raw.filename = raw.orig_filename = item
                    item = raw
                output.writestr(item, b'fictitious payload, never executable')
        destination = root / 'destination'
        destination.mkdir()
        return archive, destination, hashlib.sha256(archive.read_bytes()).hexdigest()

    def test_valid_archive_extracts_only_under_destination(self):
        archive, destination, digest = self.archive(['php.exe','ext/fixture.dll'])
        extract_verified(archive, destination, digest)
        self.assertEqual(len(list(destination.rglob('*.*'))), 2)

    def test_hash_mismatch_prevents_all_extraction(self):
        archive, destination, _ = self.archive(['php.exe'])
        with self.assertRaises(ValueError):
            extract_verified(archive, destination, '0' * 64)
        self.assertEqual(list(destination.iterdir()), [])

    def test_traversal_and_windows_streams_rejected_before_writes(self):
        for name in ['../outside.txt','/absolute.txt','C:/absolute.txt','ext/../../outside.txt',
                     'php.exe:stream','ext\\outside.dll','php.ini','NUL','ext/CON.txt','alias./payload']:
            with self.subTest(name=name):
                archive, destination, digest = self.archive(['safe.txt', name])
                with self.assertRaises(ValueError):
                    extract_verified(archive, destination, digest)
                self.assertEqual(list(destination.iterdir()), [])

    def test_case_collisions_rejected_before_writes(self):
        archive, destination, digest = self.archive(['php.exe','PHP.EXE'])
        with self.assertRaises(ValueError):
            extract_verified(archive, destination, digest)
        self.assertEqual(list(destination.iterdir()), [])

    def test_symlink_member_rejected_before_writes(self):
        entry = zipfile.ZipInfo('external-link')
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive, destination, digest = self.archive([entry])
        with self.assertRaises(ValueError):
            extract_verified(archive, destination, digest)
        self.assertEqual(list(destination.iterdir()), [])

    def test_existing_file_is_never_overwritten(self):
        archive, destination, digest = self.archive(['safe.txt','php.exe'])
        (destination / 'php.exe').write_bytes(b'existing sentinel')
        with self.assertRaises(ValueError):
            extract_verified(archive, destination, digest)
        self.assertEqual((destination / 'php.exe').read_bytes(), b'existing sentinel')
        self.assertFalse((destination / 'safe.txt').exists())


if __name__ == '__main__':
    unittest.main()
