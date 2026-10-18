import hashlib
import os
from pathlib import Path
import queue
import threading
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageOps

HOMEPAGE = 'https://huggingface.co/depth-anything/Depth-Anything-V2-Small'
REVISION = '4472b7362082ad9968fee890ca0f1e5aca36b93d'
URL = f'https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/{REVISION}/onnx/model.onnx'
SHA256 = 'afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c'
DATA = Path(os.environ.get('LENTICULAR_DATA_DIR', Path(os.environ.get('LOCALAPPDATA', Path.home()))/'Lenticular Deck Creator'))
MODEL = DATA/'models'/'depth-anything-v2-small.onnx'


def valid_model(path=MODEL):
    if not path.is_file():
        return False
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest() == SHA256


def download(progress, cancel, path=MODEL):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.download')
    try:
        with urllib.request.urlopen(URL, timeout=30) as response, temporary.open('wb') as output:
            total = int(response.headers.get('Content-Length', 0))
            received = 0
            while block := response.read(1024*256):
                if cancel.is_set():
                    raise InterruptedError('Download cancelled.')
                output.write(block)
                received += len(block)
                progress(f'Downloading {received/1e6:.1f} MB'+(f' of {total/1e6:.1f} MB' if total else ''))
        if not valid_model(temporary):
            raise ValueError('The downloaded model failed its integrity check. Please try again.')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def estimate(source, destination, model=MODEL):
    import numpy as np
    import onnxruntime as ort
    if not valid_model(model):
        raise ValueError('The depth model is missing or damaged.')
    with Image.open(source) as opened:
        original = ImageOps.exif_transpose(opened).convert('RGB')
    scale = min(1, 700/max(original.size))
    width, height = [max(14, round(side*scale/14)*14) for side in original.size]
    image = original.resize((width,height), Image.Resampling.BICUBIC)
    pixels = np.asarray(image, dtype=np.float32)/255
    pixels = (pixels-np.array([.485,.456,.406],dtype=np.float32))/np.array([.229,.224,.225],dtype=np.float32)
    inputs = np.transpose(pixels,(2,0,1))[None].copy()
    options = ort.SessionOptions()
    options.intra_op_num_threads = max(1,min(4,os.cpu_count() or 1))
    session = ort.InferenceSession(str(model), sess_options=options, providers=['CPUExecutionProvider'])
    output = session.run(None,{session.get_inputs()[0].name:inputs})[0].squeeze()
    if output.ndim != 2 or not np.isfinite(output).all():
        raise ValueError('The model returned an invalid depth map.')
    low, high = np.percentile(output,[1,99])
    output = np.clip((output-low)/max(float(high-low),1e-6),0,1)
    result = Image.fromarray((output*255).astype('uint8')).resize(original.size,Image.Resampling.BILINEAR)
    destination = Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    result.save(destination)
    return destination


def generate_dialog(creator):
    if creator.busy:
        return
    if not creator.paths[0]:
        messagebox.showinfo('Choose a colour image', 'Choose your colour image first.')
        return
    installed = valid_model()
    dialog = tk.Toplevel(creator.root)
    dialog.title('Generate depth map' if installed else 'Download depth estimation component?')
    dialog.transient(creator.root)
    dialog.grab_set()
    frame = ttk.Frame(dialog,padding=24)
    frame.pack(fill='both',expand=True)
    if not installed:
        ttk.Label(frame,text='Generate an estimated depth map from your colour image.',wraplength=460).pack(anchor='w')
        link = tk.Label(frame,text='optional component',fg='#bcc7d5',bg='#242629',font=('Segoe UI',10,'underline'))
        link.pack(anchor='w',pady=8)
        link.bind('<Enter>',lambda event:link.configure(fg='#68adff'))
        link.bind('<Leave>',lambda event:link.configure(fg='#bcc7d5'))
        link.bind('<Button-1>',lambda event:webbrowser.open(HOMEPAGE))
        ttk.Label(frame,text='Additional download: 99.1 MB (model).\nThe runtime is already included. Download once; generate locally and offline.',wraplength=460).pack(anchor='w',pady=8)
    ttk.Label(frame,text='This feature uses an AI model to estimate depth. Results may be inaccurate, especially around lettering, transparency, fine details and unusual poses.\n\nA carefully made depth map can give more accurate results. You can also load your own map without this component.',wraplength=460).pack(anchor='w',pady=8)
    status = tk.StringVar(value='Your artwork stays on your computer.')
    ttk.Label(frame,textvariable=status,wraplength=460).pack(anchor='w',pady=8)
    progress = ttk.Progressbar(frame,mode='indeterminate')
    progress.pack(fill='x',pady=6)
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x',pady=(12,0))
    cancelled = threading.Event()
    events = queue.Queue()
    running = False
    def close():
        if running:
            cancelled.set()
            status.set('Cancelling…')
        else:
            dialog.destroy()
    def start():
        nonlocal running
        running = True
        creator.busy = True
        start_button.configure(state='disabled')
        progress.start()
        source = creator.paths[0]
        destination = DATA/'generated'/('depth-'+os.urandom(8).hex()+'.png')
        def work():
            try:
                if not installed:
                    download(lambda text:events.put(('status',text)),cancelled)
                if cancelled.is_set():
                    raise InterruptedError('Cancelled.')
                events.put(('status','Estimating depth locally…'))
                result = estimate(source,destination)
                if cancelled.is_set():
                    result.unlink(missing_ok=True)
                    raise InterruptedError('Cancelled.')
                events.put(('done',result))
            except Exception as exc:
                events.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()
        poll()
    def poll():
        nonlocal running
        while not events.empty():
            kind,value = events.get()
            if kind == 'status':
                status.set(value)
            else:
                running = False
                creator.busy = False
                progress.stop()
                if kind == 'done':
                    creator.paths[1] = str(value)
                    creator.placements[1] = dict(creator.placements[0])
                    creator.refresh_images()
                    creator.status.set('Estimated depth map ready. Review the result before exporting.')
                    dialog.destroy()
                    return
                status.set(value)
                start_button.configure(state='normal')
        if running:
            dialog.after(100,poll)
    ttk.Button(buttons,text='Cancel',command=close).pack(side='right')
    start_button = ttk.Button(buttons,text='Generate depth map' if installed else 'Download component',command=start)
    start_button.pack(side='right',padx=8)
    dialog.protocol('WM_DELETE_WINDOW',close)
