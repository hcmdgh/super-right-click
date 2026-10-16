"""Verify that installing cannot overwrite unrelated files or applications."""

import importlib.util
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "scripts/install.py"
SPEC = importlib.util.spec_from_file_location("installer", MODULE)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallDestinationTests(unittest.TestCase):
    identifier = "local.genghao.itermfindermenu"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.destination = self.root / "iTerm Finder Menu.app"

    def write_bundle(self, identifier):
        contents = self.destination / "Contents"
        contents.mkdir(parents=True)
        (contents / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": identifier}))

    def test_new_install_and_matching_update_are_allowed(self):
        installer.validate_destination(self.destination, self.identifier)
        self.write_bundle(self.identifier)
        installer.validate_destination(self.destination, self.identifier)

    def test_unrelated_application_is_preserved(self):
        self.write_bundle("com.example.unrelated")
        original = (self.destination / "Contents/Info.plist").read_bytes()
        with self.assertRaises(ValueError):
            installer.validate_destination(self.destination, self.identifier)
        self.assertEqual((self.destination / "Contents/Info.plist").read_bytes(), original)

    def test_regular_file_is_preserved(self):
        self.destination.write_text("keep this file")
        with self.assertRaises(ValueError):
            installer.validate_destination(self.destination, self.identifier)
        self.assertEqual(self.destination.read_text(), "keep this file")

    def test_symlinks_are_rejected_including_broken_links(self):
        for target in (self.root, self.root / "missing"):
            with self.subTest(target=target):
                self.destination.symlink_to(target)
                with self.assertRaises(ValueError):
                    installer.validate_destination(self.destination, self.identifier)
                self.assertTrue(self.destination.is_symlink())
                self.destination.unlink()

    def prepare_build(self):
        project = self.root / "source"
        resources = project / "resources"
        resources.mkdir(parents=True)
        info = {"CFBundleIdentifier": self.identifier, "CFBundleName": "iTerm Finder Menu"}
        (resources / "App-Info.plist").write_bytes(plistlib.dumps(info))
        source = project / "build" / self.destination.name
        (source / "Contents").mkdir(parents=True)
        (source / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
        (source / "version.txt").write_text("new")
        extension_contents = source / installer.EXTENSION_RELATIVE / "Contents"
        extension_contents.mkdir(parents=True)
        (extension_contents / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": self.identifier + ".findersync",
        }))
        self.write_bundle(self.identifier)
        (self.destination / "version.txt").write_text("previous")
        return project

    def test_failed_registration_restores_previous_app(self):
        project = self.prepare_build()
        with patch.object(installer, "ROOT", project), \
             patch.object(installer, "run"), \
             patch.object(installer, "stop_bundle_processes"), \
             patch.object(installer, "register", side_effect=[RuntimeError("registration failed"), None]) as register:
            with self.assertRaisesRegex(RuntimeError, "registration failed"):
                installer.install(self.root)
        self.assertEqual((self.destination / "version.txt").read_text(), "previous")
        self.assertEqual(register.call_count, 2)
        self.assertFalse(list(self.root.glob(".iterm-menu-install-*")))

    def test_failure_before_replacement_does_not_delete_old_app(self):
        project = self.prepare_build()
        with patch.object(installer, "ROOT", project), \
             patch.object(installer, "run"), \
             patch.object(installer, "stop_bundle_processes", side_effect=RuntimeError("stop failed")), \
             patch.object(installer, "register") as register:
            with self.assertRaisesRegex(RuntimeError, "stop failed"):
                installer.install(self.root)
        self.assertEqual((self.destination / "version.txt").read_text(), "previous")
        register.assert_called_once_with(self.destination, self.identifier + ".findersync")


if __name__ == "__main__":
    unittest.main()
