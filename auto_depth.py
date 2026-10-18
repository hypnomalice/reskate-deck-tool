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

DATA = Path(os.environ.get('LENTICULAR_DATA_DIR', Path(os.environ.get('LOCALAPPDATA', Path.home()))/'Lenticular Deck Creator'))
MODELS = {
    'light': dict(label='Light (Small)', filename='depth-anything-v2-small.onnx', size=99_060_839,
        homepage='https://huggingface.co/depth-anything/Depth-Anything-V2-Small',
        url='https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/4472b7362082ad9968fee890ca0f1e5aca36b93d/onnx/model.onnx',
        sha256='afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c',
        licence='Apache 2.0'),
    'full': dict(label='Full (Base)', filename='depth-anything-v2-base.onnx', size=388_917_010,
        homepage='https://huggingface.co/depth-anything/Depth-Anything-V2-Base',
        url='https://huggingface.co/onnx-community/depth-anything-v2-base/resolve/dd4557d492cd7b563738ac8d9ccff9094620983c/onnx/model.onnx',
        sha256='dab40f67d5ead5e0ed52acfae41a717a708b02bc57f6cb761c5de828f26a7289',
        licence='CC BY-NC 4.0 — non-commercial use only'),
}


def model_path(choice='light'):
    return DATA/'models'/MODELS[choice]['filename']


def valid_model(path=None, *, choice='light'):
    path = Path(path) if path is not None else model_path(choice)
    if not path.is_file():
        return False
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest() == MODELS[choice]['sha256']


def download(progress, cancel, path=None, *, choice='light'):
    path = Path(path) if path is not None else model_path(choice)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.download')
    try:
        if cancel.is_set():
            raise InterruptedError('Download cancelled.')
        with urllib.request.urlopen(MODELS[choice]['url'], timeout=30) as response, temporary.open('wb') as output:
            total = int(response.headers.get('Content-Length', 0))
            received = 0
            while block := response.read(1024*256):
                if cancel.is_set():
                    raise InterruptedError('Download cancelled.')
                output.write(block)
                received += len(block)
                progress(f'Downloading {received/1e6:.1f} MB'+(f' of {total/1e6:.1f} MB' if total else ''))
        if cancel.is_set():
            raise InterruptedError('Download cancelled.')
        if not valid_model(temporary, choice=choice):
            raise ValueError('The downloaded model failed its integrity check. Please try again.')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def estimate(source, destination, model=None, *, choice='light'):
    import numpy as np
    import onnxruntime as ort
    model = Path(model) if model is not None else model_path(choice)
    if not valid_model(model, choice=choice):
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
    dialog = tk.Toplevel(creator.root)
    dialog.title('Generate depth map')
    dialog.transient(creator.root)
    dialog.grab_set()
    frame = ttk.Frame(dialog,padding=24)
    frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Depth model').pack(anchor='w')
    choice = tk.StringVar(value=MODELS['light']['label'])
    selector = ttk.Combobox(frame,textvariable=choice,state='readonly',values=[m['label'] for m in MODELS.values()])
    selector.pack(fill='x',pady=6)
    details = tk.StringVar()
    ttk.Label(frame,textvariable=details,wraplength=460).pack(anchor='w',pady=8)
    link = tk.Label(frame,text='optional component',fg='#bcc7d5',bg='#242629',font=('Segoe UI',10,'underline'))
    link.pack(anchor='w',pady=8)
    link.bind('<Enter>',lambda event:link.configure(fg='#68adff'))
    link.bind('<Leave>',lambda event:link.configure(fg='#bcc7d5'))
    def selected_model():
        return next(key for key, model in MODELS.items() if model['label']==choice.get())
    link.bind('<Button-1>',lambda event:webbrowser.open(MODELS[selected_model()]['homepage']))
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
    def update_model(event=None):
        key = selected_model()
        model = MODELS[key]
        installed = valid_model(choice=key)
        download_text = 'Installed — no download needed.' if installed else f"Additional download: {model['size']/1e6:.1f} MB."
        description = 'Smaller and faster; the default model.' if key=='light' else 'Larger model; uses more memory and may take longer. Better results are not guaranteed for every image.'
        details.set(f"{description}\n{download_text}\nLicence: {model['licence']}.\nDownload once; generate locally and offline.")
        start_button.configure(text='Generate depth map' if installed else 'Download & generate')
    def close():
        if running:
            cancelled.set()
            status.set('Cancelling…')
        else:
            dialog.destroy()
    def start():
        nonlocal running
        key = selected_model()
        cancelled.clear()
        running = True
        creator.busy = True
        start_button.configure(state='disabled')
        selector.configure(state='disabled')
        progress.start()
        source = creator.paths[0]
        destination = DATA/'generated'/('depth-'+os.urandom(8).hex()+'.png')
        def work():
            try:
                if not valid_model(choice=key):
                    download(lambda text:events.put(('status',text)),cancelled,choice=key)
                if cancelled.is_set():
                    raise InterruptedError('Cancelled.')
                events.put(('status',f"Estimating depth locally with {MODELS[key]['label']}…"))
                result = estimate(source,destination,choice=key)
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
                selector.configure(state='readonly')
                update_model()
        if running:
            dialog.after(100,poll)
    ttk.Button(buttons,text='Cancel',command=close).pack(side='right')
    start_button = ttk.Button(buttons,command=start)
    start_button.pack(side='right',padx=8)
    selector.bind('<<ComboboxSelected>>',update_model)
    update_model()
    dialog.protocol('WM_DELETE_WINDOW',close)
