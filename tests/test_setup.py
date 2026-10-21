import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('family_setup',ROOT/'setup.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)

class SetupTests(unittest.TestCase):
    def test_only_explicit_local_tv_addresses_are_accepted(self):
        self.assertEqual(setup.tv_address('192.168.1.25'),'192.168.1.25')
        for value in ['8.8.8.8','127.0.0.1','localhost','192.168.1.1;whoami','::1']:
            with self.assertRaises(ValueError):setup.tv_address(value)

    def test_tool_downloads_cannot_change_to_another_host_or_executable(self):
        setup.check_download_url(setup.DOWNLOADS['Darwin']['url'])
        for url in ['http://download.tizen.org/sdk/a','https://evil.example/setup.exe','https://download.tizen.org.evil.example/setup.exe','https://download.tizen.org/sdk/Installer/other.exe']:
            with self.assertRaises(ValueError):setup.check_download_url(url)

    def test_corrupt_cached_installer_is_rejected_without_overwriting(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'installer.dmg';p.write_bytes(b'broken')
            with self.assertRaises(ValueError):setup.verify_download(p,{'bytes':42,'sha256':None})
            self.assertEqual(p.read_bytes(),b'broken')

    def test_sdk_errors_are_not_treated_as_success_even_with_zero_exit_code(self):
        with self.assertRaises(RuntimeError):setup.check_sdb_connect('error: failed to connect to remote target',0)
        setup.check_sdb_connect('connected to 192.168.1.25:26101',0)

if __name__=='__main__':unittest.main()
