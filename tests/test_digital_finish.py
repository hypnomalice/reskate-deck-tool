import unittest
import numpy as np
from PIL import Image
import digital_finish
from effect_preview import AtlasPreview

class DigitalFinishTests(unittest.TestCase):
    def setUp(self):
        self.a=Image.new('RGB',(512,2048),'red');self.b=Image.new('RGB',(512,2048),'white')
    def test_paper_discards_hue_and_uses_four_pigments(self):
        im=Image.fromarray(np.tile(np.arange(256,dtype=np.uint8),(32,1)))
        x=np.asarray(digital_finish.paper(im));self.assertEqual(len(np.unique(x)),4)
        np.testing.assert_array_equal(x[:,:,0],x[:,:,1])
    def test_effect_markers_differ(self):
        markers=[AtlasPreview(digital_finish.pack(mode,self.a,self.b),mode).sample(.875,27/4096) for mode in ('eink','glitch')]
        self.assertGreater(np.linalg.norm(markers[0]-markers[1]),.4)
    def test_eink_pages_and_span_change_refresh(self):
        out=[]
        for span in (.2,2):
            p=AtlasPreview(digital_finish.pack('eink',self.a,self.b,dict(span=span)),'eink')
            out.append(np.asarray(p.render(.35,(64,256))))
        self.assertGreater(np.abs(out[0].astype(float)-out[1]).mean(),1)
    def test_controls_do_not_rewrite_artwork(self):
        a=digital_finish.pack('glitch',self.a,self.b,dict(strength=0))
        b=digital_finish.pack('glitch',self.a,self.b,dict(strength=1,preset='dropout'))
        np.testing.assert_array_equal(np.asarray(a)[64:],np.asarray(b)[64:])
    def test_all_previews_render(self):
        for mode in ('eink','glitch'):
            p=AtlasPreview(digital_finish.pack(mode,self.a,self.b),mode)
            for angle in (-1,0,1):self.assertEqual(p.render(angle,(64,256)).size,(64,256))

    def test_glitch_animates_without_changing_view_angle(self):
        p=AtlasPreview(digital_finish.pack('glitch',self.b,self.a),'glitch')
        p.clock_seconds=0
        a=np.asarray(p.render(0,(64,256)))
        p.clock_seconds=.4
        b=np.asarray(p.render(0,(64,256)))
        self.assertGreater(np.abs(a.astype(float)-b).mean(),1)

    def test_preview_worker_does_not_shadow_copy_module(self):
        import ast
        from pathlib import Path
        tree=ast.parse((Path(__file__).parents[1]/'qt_ui.py').read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if isinstance(child,ast.Import):
                        self.assertNotIn('copy',[alias.name for alias in child.names])
