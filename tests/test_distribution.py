"""Distribution/build checks that require neither game assets nor a GPU."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class DistributionTests(unittest.TestCase):
    def test_settings_preserve_player_paths_and_preferences(self):
        install = module('install', 'scripts/configure_install.py')
        with tempfile.TemporaryDirectory() as folder:
            build = Path(folder)
            install.configure(build)
            self.assertIn('mcla_aspect_ratio = "auto"', (build / 'mcla.toml').read_text())
            custom = 'user_data_root = "my-save"\nframe_generation = "fsr"\n'
            (build / 'mcla.toml').write_text(custom)
            install.configure(build)
            self.assertEqual((build / 'mcla.toml').read_text(), custom)

    def test_bad_amd_download_cannot_replace_existing_provider(self):
        amd = module('amd', 'scripts/prepare_amd_fsr.py')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'scripts').mkdir()
            manifest = dict(repository='official/example', revision='pinned', files=[dict(
                path='test.dll', destination='runtime', sha256=hashlib.sha256(b'expected').hexdigest())])
            (root / 'scripts/amd-fsr-manifest.json').write_text(json.dumps(manifest))
            runtime = root / 'runtime'
            runtime.mkdir()
            (runtime / 'test.dll').write_bytes(b'previous good provider')
            with patch.object(amd, 'ROOT', root), patch.object(amd.urllib.request, 'urlopen', return_value=io.BytesIO(b'corrupt')):
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    amd.prepare(root / 'sdk', runtime)
            self.assertEqual((runtime / 'test.dll').read_bytes(), b'previous good provider')
            self.assertEqual(len(list(runtime.iterdir())), 1)

    def test_native_translation_preserves_other_languages_and_control_tags(self):
        ptbr = module('ptbr', 'localization/build_ptbr.py')
        original = 'Example <D>42</D>'
        text = (original + '\0').encode('utf-16le')
        english = struct.pack('<I', 1) + struct.pack('<IHI', 0x12345678, 0, 0) + struct.pack('<I', len(text)//2) + text + bytes(10)
        start = 4 + 11 * 4
        tail = b'unchanged other languages'
        blob = struct.pack('<I11I', 11, start, *([start + len(english)] * 10)) + english + tail
        expected = hashlib.sha256(original.encode()).hexdigest()
        changes = {'12345678': (expected, 'Exemplo <D>42</D>')}
        translated, selected = ptbr.translate_bundle(blob, changes)
        self.assertEqual(selected, ['12345678'])
        self.assertTrue(translated.endswith(tail))
        self.assertIn('Exemplo <D>42</D>'.encode('utf-16le'), translated)
        with self.assertRaises(AssertionError):
            ptbr.translate_bundle(blob, {'12345678': (expected, 'Exemplo 42')})
        with self.assertRaises(AssertionError):
            ptbr.translate_bundle(blob, {'12345678': ('incorrect-source-hash', 'Exemplo <D>42</D>')})

    def test_translation_sources_and_provider_manifest_are_complete(self):
        native = json.loads((ROOT / 'localization/pt-BR/native-texts.json').read_text(encoding='utf8'))
        subtitles = json.loads((ROOT / 'localization/pt-BR/subtitle-files.json').read_text())
        self.assertEqual(len(native['bundles']), 4)
        self.assertEqual(len({r['entry'] for r in subtitles}), 76)
        self.assertEqual(len(native["records"]), 2815)
        for record in native['records'].values():
            self.assertEqual(len(record['source_sha256']), 64)
            self.assertIsInstance(record['translation'], str)
        manifest = json.loads((ROOT / 'scripts/amd-fsr-manifest.json').read_text())
        self.assertEqual(len(manifest['revision']), 40)
        self.assertEqual(sum(r['destination'] == 'runtime' for r in manifest['files']), 3)
        for item in manifest['files']:
            self.assertEqual(len(item['sha256']), 64)
            self.assertNotIn('..', Path(item['path']).parts)

    @staticmethod
    def _bundle(records):
        """A resource table with only an English block, the way the game keeps its texts."""
        def record(ident, text):
            data = (text + '\0').encode('utf-16le')
            return struct.pack('<IHI', ident, 0, 0) + struct.pack('<I', len(data) // 2) + data + bytes(10)
        english = struct.pack('<I', len(records)) + b''.join(record(i, t) for i, t in records)
        start = 4 + 11 * 4
        tail = b'other languages'
        return struct.pack('<I11I', 11, start, *([start + len(english)] * 10)) + english + tail, tail

    def test_update_rewrites_only_untranslated_records(self):
        ptbr = module('ptbr', 'localization/build_ptbr.py')
        sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
        # 1: still English (a new translation); 2: already the current translation;
        # 3: the translation an earlier release made; 4: text this tool never wrote.
        blob, tail = self._bundle([(1, 'New <D>1</D>'), (2, 'Ja traduzido'), (3, 'Antiga'), (4, 'Editado a mao')])
        changes = {'00000001': (sha('New <D>1</D>'), 'Novo <D>1</D>'),
                   '00000002': (sha('Already'), 'Ja traduzido'),
                   '00000003': (sha('Old'), 'Nova'),
                   '00000004': (sha('Mine'), 'Outra')}
        earlier = {'00000003': sha('Antiga')}
        def replaceable(key, text):
            expected, translated = changes[key]
            current = sha(text)
            return False if current == sha(translated) else current == expected or earlier.get(key) == current
        result, updated = ptbr.translate_bundle(blob, changes, replaceable)
        self.assertEqual(sorted(updated), ['00000001', '00000003'])
        self.assertTrue(result.endswith(tail))
        for text in ('Novo <D>1</D>', 'Nova', 'Ja traduzido', 'Editado a mao'):
            self.assertIn(text.encode('utf-16le'), result)
        self.assertNotIn('Antiga'.encode('utf-16le'), result)
        # Without a policy the original behaviour stays: every record must be the English one.
        with self.assertRaises(AssertionError):
            ptbr.translate_bundle(blob, changes)

    def test_installer_version_is_one_release_everywhere(self):
        core = re.search(r'Version = "([0-9.]+)"', (ROOT / 'installer/source/Core.cs').read_text(encoding='utf8')).group(1)
        packaged = re.search(r"--version',default='([0-9.]+)'", (ROOT / 'installer/package.py').read_text(encoding='utf8')).group(1)
        self.assertEqual(core, packaged)

    def test_update_mode_never_writes_player_data(self):
        source = (ROOT / 'installer/source/compact_prepare.py').read_text(encoding='utf8')
        update = source[source.index('def update_install'):source.index('def main')]
        # The update copies the saves out (backup) but never replaces settings or game data wholesale.
        for forbidden in ("write_text(existing", "rmtree", "output_game", "extract_game", "settings.with_suffix"):
            self.assertNotIn(forbidden, update)
        self.assertIn("backup_saves(", update)
        self.assertIn("update_ptbr.py", update)

    def test_translation_can_be_turned_off_and_defaults_on(self):
        source = (ROOT / 'installer/source/compact_prepare.py').read_text(encoding='utf8')
        self.assertIn("'--translate', choices=('1', '0'), default='1'", source)
        self.assertIn("mcla_ptbr=translate", source)
        xaml = (ROOT / 'installer/source/Launcher.xaml').read_text(encoding='utf8')
        self.assertRegex(xaml, r'x:Name="TranslateGame"[^>]*IsChecked="True"')
        script = (ROOT / 'installer/source/offline_bootstrap.ps1').read_text(encoding='utf8')
        self.assertIn("[string]$Translate = '1'", script)


if __name__ == '__main__':
    unittest.main()
