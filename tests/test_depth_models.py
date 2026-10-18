import hashlib
import io
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import auto_depth as depth

assert depth.model_path().name == 'depth-anything-v2-small.onnx'
assert depth.model_path('full') != depth.model_path('light')
assert depth.MODELS['full']['size'] == 388_917_010
with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary)/'model.onnx'
    payload = b'test model'
    model = dict(depth.MODELS['full'],sha256=hashlib.sha256(payload).hexdigest())
    class Response(io.BytesIO):
        headers = {'Content-Length':str(len(payload))}
    with patch.dict(depth.MODELS,full=model):
        with patch.object(depth.urllib.request,'urlopen',return_value=Response(payload)) as opened:
            depth.download(lambda message:None,threading.Event(),path,choice='full')
            assert opened.call_args.args[0] == model['url']
        assert depth.valid_model(path,choice='full')
        assert not depth.valid_model(path,choice='light')
        with patch.object(depth.urllib.request,'urlopen',return_value=Response(b'corrupt')):
            try:
                depth.download(lambda message:None,threading.Event(),path,choice='full')
                raise AssertionError('Corrupt model was accepted')
            except ValueError:
                pass
        assert path.read_bytes() == payload
        assert not path.with_suffix('.download').exists()
        cancel = threading.Event()
        cancel.set()
        with patch.object(depth.urllib.request,'urlopen') as opened:
            try:
                depth.download(lambda message:None,cancel,path,choice='full')
                raise AssertionError('Cancelled download was started')
            except InterruptedError:
                pass
            opened.assert_not_called()

root=tk.Tk()
root.withdraw()
creator=SimpleNamespace(root=root,busy=False,paths=['unused-source.png',None])
with patch.object(depth,'valid_model',return_value=False), patch.object(depth,'download') as download:
    depth.generate_dialog(creator)
    dialog=next(child for child in root.winfo_children() if isinstance(child,tk.Toplevel))
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)
    widgets=list(descendants(dialog))
    selector=next(child for child in widgets if isinstance(child,ttk.Combobox))
    assert selector.get() == 'Light (Small)'
    selector.set('Full (Base)')
    selector.event_generate('<<ComboboxSelected>>')
    root.update()
    labels='\n'.join(str(child.cget('text')) if not child.cget('textvariable') else str(root.getvar(child.cget('textvariable'))) for child in widgets if isinstance(child,ttk.Label))
    assert '388.9 MB' in labels and 'non-commercial' in labels
    download.assert_not_called()
root.destroy()
print('PASS: independent caches, checksums, corruption/cancellation, Light default and Full download/licence popup.')

