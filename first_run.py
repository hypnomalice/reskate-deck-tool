import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

WARNING = '''Warning: You NEED a version of ReSkate Studio that supports shaders.
This warning will only appear once.

By clicking "Got it, chief", you confirm that you have a shader-supported ReSkate Studio build
and won't come crying in chat because it won't let you import.'''


def show_shader_warning(root):
    settings_dir = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Lenticular Deck Creator'
    marker = settings_dir / 'shader-support-acknowledged.json'
    try:
        if json.loads(marker.read_text(encoding='utf8')).get('acknowledged') is True:
            return True
    except (OSError, ValueError, AttributeError):
        pass

    accepted = False
    dialog = tk.Toplevel(root)
    dialog.title('Shader support required')
    dialog.resizable(False, False)
    dialog.transient(root)
    frame = ttk.Frame(dialog, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text=WARNING, justify='center', anchor='center', wraplength=590).pack(fill='x')

    def acknowledge():
        nonlocal accepted
        try:
            settings_dir.mkdir(parents=True, exist_ok=True)
            temporary = marker.with_suffix('.tmp')
            temporary.write_text(json.dumps({'acknowledged': True}), encoding='utf8')
            temporary.replace(marker)
        except OSError as error:
            messagebox.showerror('Cannot save acknowledgement',
                                 'The acknowledgement could not be saved.\n\n' + str(error), parent=dialog)
            return
        accepted = True
        dialog.destroy()

    button = ttk.Button(frame, text='Got it, chief', command=acknowledge)
    button.pack(pady=(22, 0))
    dialog.update_idletasks()
    x = root.winfo_rootx() + max(0, (root.winfo_width()-dialog.winfo_reqwidth())//2)
    y = root.winfo_rooty() + max(0, (root.winfo_height()-dialog.winfo_reqheight())//2)
    dialog.geometry(f'+{x}+{y}')
    dialog.grab_set()
    button.focus_set()
    root.wait_window(dialog)
    return accepted
