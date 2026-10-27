from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import subprocess
import tempfile
import unittest
import zipfile
import native_export


class NativeExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.game=self.root/'game';self.game.mkdir()
        (self.game/'Skate.exe').write_bytes(b'game');(self.game/'Data').mkdir()
        (self.game/'Data/layout.toc').write_bytes(b'original layout')
        self.cli=self.root/'Studio/reskate_cli.exe';self.cli.parent.mkdir();self.cli.write_bytes(b'cli')
        self.target=self.root/'result.zip'

    def compile(self,args,**options):
        self.assertEqual(args[:3],[str(self.cli),'compile-mod',str(self.game)])
        self.assertNotIn('shell',options)
        stage=Path(args[3]);self.assertFalse(stage.is_relative_to(self.game))
        self.assertEqual(Path(args[4]).read_bytes(),b'content only')
        folder=stage/'Patch';folder.mkdir(parents=True)
        (folder/'layout.toc').write_bytes(b'compiled layout')
        (folder/'Win32').mkdir();(folder/'Win32/items.toc').write_bytes(b'bundles')
        return SimpleNamespace(returncode=0,stdout='resources=14')

    def export(self,compile,folder=False):
        def content(projects,path,progress,**kwargs):
            self.assertTrue(kwargs['shared_runtime']);Path(path).write_bytes(b'content only')
        with patch('creator_engine.export_pack',side_effect=content),patch('native_export.subprocess.run',side_effect=compile):
            exporter = native_export.export_folder if folder else native_export.export_zip
            return exporter([{}],self.target,title='My Deck',game_root=self.game,compiler=self.cli)

    def test_native_zip_has_one_installable_folder_and_no_fbmod(self):
        self.export(self.compile)
        with zipfile.ZipFile(self.target) as z:
            self.assertEqual(z.read('My Deck/layout.toc'),b'compiled layout')
            self.assertEqual(z.read('My Deck/Win32/items.toc'),b'bundles')
            self.assertFalse(any(n.endswith('.fbmod') or n.endswith('.exe') for n in z.namelist()))
        self.assertEqual((self.game/'Data/layout.toc').read_bytes(),b'original layout')
        self.assertFalse((self.game/'Mods').exists())

    def test_compiler_failure_preserves_previous_export(self):
        self.target.write_bytes(b'previous export')
        with self.assertRaisesRegex(ValueError,'compilation failed'):
            self.export(lambda *a,**k:SimpleNamespace(returncode=1,stdout='unsupported resource'))
        self.assertEqual(self.target.read_bytes(),b'previous export')
        self.assertFalse(list(self.root.glob('.deck-package-*')))

    def test_missing_layout_and_timeout_preserve_export(self):
        self.target.write_bytes(b'previous export')
        with self.assertRaisesRegex(ValueError,'native mod layout'):
            self.export(lambda *a,**k:SimpleNamespace(returncode=0,stdout=''))
        with self.assertRaises(subprocess.TimeoutExpired):
            self.export(lambda *a,**k:(_ for _ in ()).throw(subprocess.TimeoutExpired('compiler',900)))
        self.assertEqual(self.target.read_bytes(),b'previous export')

    def test_folder_export_writes_native_layout_and_verified_receipt(self):
        self.target=self.root/'Mods/My Deck'
        self.export(self.compile,folder=True)
        self.assertEqual((self.target/'layout.toc').read_bytes(),b'compiled layout')
        native_export.check_folder(self.target)
        self.assertFalse(any(p.suffix=='.fbmod' for p in self.target.rglob('*')))
        self.assertFalse((self.game/'Mods').exists())

    def test_reexport_backs_up_previous_owned_folder(self):
        self.target=self.root/'Mods/My Deck'
        self.export(self.compile,folder=True)
        self.export(self.compile,folder=True)
        backups=list((self.target.parent/'.deck-tool-backups').glob('*.zip'))
        self.assertEqual(len(backups),1)
        with zipfile.ZipFile(backups[0]) as z:
            self.assertEqual(z.read('My Deck/layout.toc'),b'compiled layout')
        native_export.check_folder(self.target)

    def test_existing_other_mod_and_user_edits_are_never_overwritten(self):
        self.target=self.root/'Other Mod';self.target.mkdir()
        (self.target/'layout.toc').write_bytes(b'other mod')
        with self.assertRaisesRegex(ValueError,'unchanged Deck Tool'):
            self.export(self.compile,folder=True)
        self.assertEqual((self.target/'layout.toc').read_bytes(),b'other mod')
        self.target=self.root/'My Deck';self.export(self.compile,folder=True)
        (self.target/'notes.txt').write_text('my edits')
        with self.assertRaisesRegex(ValueError,'unchanged Deck Tool'):
            self.export(self.compile,folder=True)
        self.assertEqual((self.target/'notes.txt').read_text(),'my edits')

    def test_nested_receipt_named_user_file_is_preserved(self):
        self.target=self.root/'My Deck';self.export(self.compile,folder=True)
        extra=self.target/'notes'/native_export.RECEIPT;extra.parent.mkdir();extra.write_text('user file')
        with self.assertRaisesRegex(ValueError,'unchanged Deck Tool'):
            self.export(self.compile,folder=True)
        self.assertEqual(extra.read_text(),'user file')

    def test_modified_generated_file_is_preserved(self):
        self.target=self.root/'My Deck';self.export(self.compile,folder=True)
        (self.target/'layout.toc').write_bytes(b'edited layout')
        with self.assertRaisesRegex(ValueError,'unchanged Deck Tool'):
            self.export(self.compile,folder=True)
        self.assertEqual((self.target/'layout.toc').read_bytes(),b'edited layout')

    def test_folder_commit_failure_restores_previous_mod(self):
        import os
        self.target=self.root/'My Deck';self.export(self.compile,folder=True)
        replace=os.replace
        def fail_commit(source,target):
            if Path(source).name=='new' and Path(target)==self.target:
                raise OSError('simulated commit failure')
            return replace(source,target)
        with patch('native_export.os.replace',side_effect=fail_commit):
            with self.assertRaisesRegex(OSError,'commit failure'):
                self.export(self.compile,folder=True)
        self.assertEqual((self.target/'layout.toc').read_bytes(),b'compiled layout')
        native_export.check_folder(self.target)

    def test_inputs_and_names(self):
        with self.assertRaises(ValueError):native_export.validate_inputs(self.root,self.cli)
        with self.assertRaises(ValueError):native_export.validate_inputs(self.game,self.root/'missing.exe')
        for title in ['../../evil', 'CON', 'NUL.foo', 'a/b', 'x:y']:
            name=native_export.mod_name(title)
            self.assertNotIn('/',name);self.assertNotIn('\\',name)
            self.assertFalse(name.startswith('.'))
        self.assertEqual(native_export.mod_name('CON'),'Deck Pack')


if __name__=='__main__':unittest.main()
