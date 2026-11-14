import json
import tempfile
import unittest
from pathlib import Path
import transparency_native as native


class NativeTransparencySettingsTests(unittest.TestCase):
    def test_runtime_rejects_the_missing_shared_data_from_second_crash(self):
        import effects_runtime
        updates=effects_runtime._runtime_updates()
        native.validate_runtime_dependencies(updates)
        missing='expressionshader/permutationshareddata/8239482023658057188'
        self.assertTrue(any(row['name']==missing for row,_ in updates))
        with self.assertRaisesRegex(ValueError,'8239482023658057188'):
            native.validate_runtime_dependencies([(row,payload) for row,payload in updates
                                                  if row['name']!=missing])

    def test_native_colour_type_is_preserved_in_every_optical_identity(self):
        native.validate_parameter_ids()
        # This exact arbitrary UUID was in the failed startup package. Its
        # embedded type becomes 0xa1228c92, which the game cannot resolve.
        with self.assertRaisesRegex(ValueError,'ColorRgb'):
            native.validate_parameter_ids(['5fbdb69cae8bb35b928c22a1da938240'])

    def test_corrupted_binding_is_rejected_before_runtime_export(self):
        raw=b''.join(bytes.fromhex(x) for x in native.COLOUR_GUIDS)
        native.validate_optical_binding(raw)
        damaged=raw.replace(bytes.fromhex(native.COLOUR_GUIDS[0]),
                            bytes.fromhex('5fbdb69cae8bb35b928c22a1da938240'))
        with self.assertRaises(ValueError):native.validate_optical_binding(damaged)

    def test_parameters_keep_full_rgb_precision_and_explicit_zero(self):
        values=native.parameter_values('glass',dict(tint='#123456',haze=0,tint_strength=0,reflection_strength=2))
        self.assertEqual(values[0],[18/255,52/255,86/255])
        self.assertEqual(values[1][:2],[0,0])
        self.assertEqual(values[2][0],1)
        self.assertEqual(values[3][2],native.AUTHORING_MARKER)
        self.assertTrue(all(0<=x<=1 for row in values for x in row))

    def test_mixed_pack_retains_spring_declaration_and_isolates_each_deck(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'reskate-materials.json'
            existing=dict(part='deck',items=['Own_Spring'],parameters=[dict(guid='previous',type='colour',default=[.1,.2,.3])])
            path.write_text(json.dumps(dict(schema=1,materials=[existing])))
            native.write_materials([
                dict(name='Glass A',mode='glass',glass=dict(tint='#ff0000')),
                dict(name='Glass B',mode='glass',glass=dict(tint='#0000ff',haze=.8)),
                dict(name='Spring',mode='jiggle')],folder)
            rows=json.loads(path.read_text())['materials']
            self.assertEqual(rows[0],existing)
            self.assertEqual(len(rows),3)
            self.assertEqual(rows[1]['parameters'][0]['default'],[1,0,0])
            self.assertEqual(rows[2]['parameters'][0]['default'],[0,0,1])
            self.assertEqual(rows[2]['parameters'][1]['default'][1],.8)

    def test_existing_item_cannot_be_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            project=dict(name='Glass',mode='glass')
            native.write_materials([project],folder)
            path=Path(folder)/'reskate-materials.json';before=path.read_bytes()
            with self.assertRaises(ValueError):native.write_materials([project],folder)
            self.assertEqual(path.read_bytes(),before)

if __name__=='__main__':unittest.main()
