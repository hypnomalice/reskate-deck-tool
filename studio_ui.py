import copy
import json
import queue
import threading
import traceback
import random
import time
import animation
import animation_texture
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageOps, ImageChops
import creator_engine as engine
import image_placement
import effect_preview
import preview_depth
from app_version import APP_VERSION
from tutorials import open_guide

BG, FIELD, TEXT, MUTED = '#242629', '#33373d', '#e3e5e8', '#aeb4be'
MODES = {'gif': 'Animated / GIF', 'classic': 'Lenticular', 'depth': 'Depth Map', 'layers': 'Foreground / Background', 'ghost': 'Ghost Rare'}
APP_NAME = 'ReSkate Deck Tool'
QUOTES = [
    'shoutouts shwang',
    '@everyone',
    'shoutouts No, Noble and c00lshapes',
    'PM died for this.',
    "You don't even skate bro",
    'Sofi was here <3',
    'Definitely not a virus',
    'GLITCH FIX STUDIO PLEASE',
    'ReSkate 2.07 is our endgame',
    'Blows up pancakes with mind',
    'This tool is so fucking ugly',
    'Shoutouts azzie',
    'Shoutouts strumzino',
    'Shoutouts kori',
    'Shoutouts Michael Fourth',
    'You should try mesh recompiler!',
]


class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.popup, self.timer = widget, text, None, None
        widget.bind('<Enter>', self.show, add='+')
        widget.bind('<FocusIn>', self.show, add='+')
        for event in ('<Leave>', '<FocusOut>', '<Escape>', '<Destroy>'):
            widget.bind(event, self.hide, add='+')

    def show(self, event=None):
        if self.popup:
            return
        popup = self.popup = tk.Toplevel(self.widget)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes('-topmost', True)
        popup.attributes('-alpha', 0)
        text = self.text() if callable(self.text) else self.text
        tk.Label(popup, text=text, bg=FIELD, fg=TEXT, padx=14, pady=12,
                 justify='left', wraplength=310, font=('Segoe UI', 10)).pack()
        popup.update_idletasks()
        x = min(self.widget.winfo_rootx(), popup.winfo_screenwidth()-popup.winfo_reqwidth()-12)
        y = self.widget.winfo_rooty()+self.widget.winfo_height()+8
        if y+popup.winfo_reqheight() > popup.winfo_screenheight()-45:
            y = self.widget.winfo_rooty()-popup.winfo_reqheight()-8
        popup.geometry(f'+{max(0,x)}+{max(0,y)}')
        popup.deiconify()
        self.fade(0)

    def fade(self, step):
        if self.popup:
            self.popup.attributes('-alpha', min(1, step/6))
            if step < 6:
                self.timer = self.widget.after(25, lambda: self.fade(step+1))

    def hide(self, event=None):
        if self.timer:
            self.widget.after_cancel(self.timer)
            self.timer = None
        if self.popup:
            self.popup.destroy()
            self.popup = None


class Creator:
    def __init__(self, root):
        self.root, self.paths, self.images = root, [None, None], [None, None]
        self.animation_clip, self.animation_path, self.animation_job = None, None, None
        self.animation_start = time.monotonic()
        self.events, self.busy = queue.Queue(), False
        self.thumbnail_path, self.depth_preview, self.preview_job = None, None, None
        self.background, self.wood_colour = '#ffffff', '#b98a56'
        self.deck_name, self.author = tk.StringVar(value='My Lenticular Deck'), tk.StringVar()
        self.mode, self.fit = tk.StringVar(value=MODES['classic']), tk.StringVar(value='Stretch')
        self.background_fit = tk.StringVar(value='Crop to fill')
        self.gif_quality = tk.StringVar(value='High (1024 × 8192)')
        self.strength, self.convergence, self.bands = tk.DoubleVar(value=.04), tk.DoubleVar(value=.5), tk.DoubleVar(value=1)
        self.invert, self.angle = tk.BooleanVar(value=False), tk.DoubleVar(value=0)
        self.wood_mode = tk.StringVar(value='Original wood')
        self.wood_intensity = tk.DoubleVar(value=1)
        self.show_trucks = tk.BooleanVar(value=True)
        self.large_preview = None
        self.render_job, self.last_frame, self.last_frame_key, self.last_draw_key = None, None, None, None
        self.preview_revision, self.preview_worker, self.preview_pending = 0, False, None
        self.atlas_preview, self.update_release = None, None
        self.gif_frames = {}
        self.status = tk.StringVar(value='Choose two graphics to begin.')
        self.selected, self.decks, self.loading = 0, [], False
        self.placements = [dict(zoom=1, x=0, y=0), dict(zoom=1, x=0, y=0)]
        self.quote = None
        self.rotate_quote()
        icon = Path(__file__).resolve().parent/'assets'/'sofi-deck-tool.ico'
        if icon.is_file():
            root.iconbitmap(default=str(icon))
            self.app_icons = [ImageTk.PhotoImage(Image.open(icon).convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)) for size in [16,32,64,128]]
            root.iconphoto(True,*self.app_icons)
        root.geometry('1180x870')
        root.minsize(1080, 850)
        root.configure(bg=BG)
        self.style()
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        header = ttk.Frame(root, padding=(18, 12))
        header.grid(row=0, column=0, sticky='ew')
        ttk.Label(header, text=APP_NAME, font=('Segoe UI', 12, 'bold')).pack(side='left')
        self.update_button = ttk.Button(header, text='Update available', command=self.open_update)
        Tooltip(self.update_button, lambda: f'Open {self.update_release.version} on GitHub. Current version: {APP_VERSION}.' if self.update_release else '')
        for text, action in [('Guide', lambda: open_guide(root)), ('Save', self.save_project), ('Open', self.load_project)]:
            ttk.Button(header, text=text, command=action).pack(side='right', padx=4)
        body = ttk.Frame(root, padding=(18, 0))
        body.grid(row=1, column=0, sticky='nsew')
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        left = ttk.Frame(body, width=245, padding=(0, 8, 14, 0))
        left.grid(row=0, column=0, sticky='ns')
        ttk.Label(left, text='Decks').pack(anchor='w')
        self.deck_list = tk.Listbox(left, width=25, height=5, bg=FIELD, fg=TEXT, borderwidth=0,
                                   selectbackground='#536479', selectforeground=TEXT, exportselection=False,
                                   activestyle='none', font=('Segoe UI', 10))
        self.deck_list.pack(fill='x', pady=8)
        self.deck_list.bind('<<ListboxSelect>>', self.select_deck)
        buttons = ttk.Frame(left)
        buttons.pack(fill='x', pady=(0, 12))
        ttk.Button(buttons, text='Add deck', command=self.add_deck).pack(side='left')
        ttk.Button(buttons, text='Remove', command=self.remove_deck).pack(side='right')
        self.labels, self.canvases, self.image_frames, self.image_contents = [], [], [], []
        for index in range(2):
            panel = ttk.LabelFrame(left, text=['Image A', 'Image B'][index], padding=8)
            panel.pack(fill='x', pady=(0, 10))
            self.image_frames.append(panel)
            canvas = tk.Canvas(panel, width=34, height=136, bg=BG, highlightthickness=0)
            canvas.pack(side='right', padx=(8, 0))
            self.canvases.append(canvas)
            content = ttk.Frame(panel)
            self.image_contents.append(content)
            content.pack(side='left', fill='x', expand=True)
            label = ttk.Label(content, text='No image selected', wraplength=135)
            label.pack(anchor='w', pady=(0, 8))
            self.labels.append(label)
            ttk.Button(content, text='Choose image…', command=lambda i=index: self.choose(i)).pack(fill='x')
            ttk.Button(content, text='Adjust placement…', command=lambda i=index: self.adjust_placement(i)).pack(fill='x', pady=5)
        self.auto_row = ttk.Frame(left)
        ttk.Button(self.auto_row, text='Generate auto depthmap', command=self.generate_depth).pack(side='left')
        self.help(self.auto_row, 'Uses an AI model to estimate depth. Results may be inaccurate around lettering, transparency, fine details and unusual poses. A carefully made depth map can give more accurate results.')
        self.swap_button = ttk.Button(left, text='Swap A / B', command=self.swap)
        self.swap_button.pack(fill='x', pady=5)
        ttk.Button(left, text='Load depth test scene', command=self.load_study).pack(fill='x', pady=5)
        centre = ttk.Frame(body, padding=(16, 8))
        self.centre = centre
        centre.grid(row=0, column=1, sticky='nsew')
        preview_header=ttk.Frame(centre)
        preview_header.pack(fill='x')
        ttk.Label(preview_header, text='Deck preview').pack(side='left')
        ttk.Button(preview_header,text='Enlarge',command=self.enlarge_preview).pack(side='right')
        ttk.Button(preview_header,text='Lens detail',command=self.lens_detail).pack(side='right',padx=6)
        self.preview = tk.Canvas(centre, width=270, height=480, bg='#1d1f22', highlightthickness=0)
        self.preview.pack(fill='both', expand=True, pady=12)
        self.preview.bind('<Configure>', lambda event: self.render())
        self.preview.bind('<Double-Button-1>', lambda event:self.enlarge_preview())
        ttk.Checkbutton(centre,text='Approximate truck positions',variable=self.show_trucks,command=self.render).pack(anchor='w')
        self.angle_control = ttk.Scale(centre, from_=-1, to=1, variable=self.angle, command=self.render)
        self.angle_control.pack(fill='x', pady=8)
        self.placement_controls = ttk.Frame(centre)
        self.placement_title = tk.StringVar()
        ttk.Label(self.placement_controls,textvariable=self.placement_title).pack(anchor='w')
        self.placement_vars = {key:tk.DoubleVar(value=value) for key,value in dict(zoom=1,x=0,y=0).items()}
        self.placement_outputs = {}
        self.placement_index = None
        for key,title,low,high in [('zoom','Zoom',.1,5),('x','Horizontal',-1,1),('y','Vertical',-1,1)]:
            row = ttk.Frame(self.placement_controls)
            row.pack(fill='x',pady=2)
            output = tk.StringVar()
            self.placement_outputs[key] = (title,output)
            ttk.Label(row,textvariable=output,width=18).pack(side='left')
            ttk.Scale(row,from_=low,to=high,variable=self.placement_vars[key],command=self.move_image).pack(side='left',fill='x',expand=True)
        row = ttk.Frame(self.placement_controls)
        row.pack(fill='x',pady=5)
        ttk.Button(row,text='Reset placement',command=self.reset_placement).pack(side='left')
        ttk.Button(row,text='Done',command=self.placement_controls.pack_forget).pack(side='right')
        ttk.Label(centre, text='Left                  Viewing angle                  Right', anchor='center').pack(fill='x')
        ttk.Label(centre, text='Note: may not reflect 1:1 in game', anchor='center').pack(fill='x', pady=(8, 10))
        right = ttk.Frame(body, padding=(14, 8, 0, 0))
        right.grid(row=0, column=2, sticky='ns')
        ttk.Label(right, text='Deck name').pack(anchor='w', pady=(8, 5))
        ttk.Entry(right, textvariable=self.deck_name).pack(fill='x')
        ttk.Label(right, text='Author (optional)').pack(anchor='w', pady=(8, 5))
        ttk.Entry(right, textvariable=self.author).pack(fill='x')
        row = ttk.Frame(right)
        row.pack(fill='x', pady=(12, 5))
        ttk.Label(row, text='Effect').pack(side='left')
        self.help(row, 'Lenticular: two images flip with viewing angle.\n\n3D (depth map): a colour image and matching grayscale depth map create depth. White is near; black is far.\n\n3D (foreground/background): a transparent foreground moves over a complete background.\n\nAnimated GIF: a GIF, animated PNG or WebP loops on the underside, centred without stretching. Up to 512 frames and 40.95 seconds. Frames may be reduced in resolution to fit. Older lenticular mods need a renderer compatibility update.')
        modes = ttk.Combobox(right, textvariable=self.mode, values=list(MODES.values()), state='readonly', width=29)
        modes.pack(fill='x')
        modes.bind('<<ComboboxSelected>>', self.change_mode)
        self.depth_anchor = modes
        self.gif_controls = ttk.Frame(right)
        quality_row = ttk.Frame(self.gif_controls)
        quality_row.pack(fill='x',pady=(8,4))
        ttk.Label(quality_row,text='Animation quality').pack(side='left')
        self.help(quality_row,'Larger atlases retain more detail per frame but use more memory and take longer to export. High uses about 8 MB of compressed texture data per deck; Ultra about 32 MB. Animation data stays at full resolution so lower mip levels cannot corrupt its timing. The preview shows the source, not the final texture compression. Up to 512 source frames are retained; extra frames are not invented.')
        ttk.Combobox(self.gif_controls,textvariable=self.gif_quality,values=['Standard (512 × 4096)','High (1024 × 8192)','Ultra (2048 × 16384)'],state='readonly').pack(fill='x')
        self.depth_controls = ttk.Frame(right)
        self.strength_label, self.convergence_label, self.bands_label = [tk.StringVar() for _ in range(3)]
        self.slider(self.depth_controls, self.strength_label, self.strength, self.schedule_depth,
                    'How far parts move. 0% removes depth. High values may stretch edges or expose missing background.')
        self.slider(self.depth_controls, self.bands_label, self.bands, self.render,
                    'Strength of the fine lens-band texture. This does not increase 3D depth.')
        self.slider(self.depth_controls, self.convergence_label, self.convergence, self.schedule_depth,
                    lambda: '0% moves the foreground; 50% shares motion; 100% moves the background.' if self.is_layers() else 'The depth-map shade that stays still. Nearer and farther parts move in opposite directions.')
        ttk.Checkbutton(self.depth_controls, text='Reverse depth', variable=self.invert, command=self.refresh_images).pack(anchor='w', pady=6)
        for variable in (self.strength, self.convergence, self.bands, self.mode):
            variable.trace_add('write', self.update_labels)
        self.fit_title = ttk.Label(right, text='Image sizing')
        self.fit_title.pack(anchor='w', pady=(12, 5))
        fit = ttk.Combobox(right, textvariable=self.fit, values=['Stretch', 'Crop to fill', 'Fit entire image'], state='readonly')
        fit.pack(fill='x')
        self.fit_box = fit
        fit.bind('<<ComboboxSelected>>', self.refresh_images)
        self.background_fit_row = ttk.Frame(self.image_contents[1])
        background_box = ttk.Combobox(self.background_fit_row,textvariable=self.background_fit,values=['Crop to fill','Fit entire image'],state='readonly',width=16)
        background_box.pack(fill='x')
        background_box.bind('<<ComboboxSelected>>',self.refresh_images)
        Tooltip(background_box,'Background framing preserves the source aspect ratio. Adjust placement pans and zooms the original image before cropping it to the board.')
        ttk.Button(right, text='Padding colour…', command=self.choose_background).pack(fill='x', pady=6)
        row = ttk.Frame(right)
        row.pack(fill='x', pady=(10, 5))
        ttk.Label(row, text='Base colour (wood)').pack(side='left')
        self.help(row, 'Changes the exposed wood using a separate base colour texture for this deck. Intensity controls brightness. Artwork is separate. The preview is approximate; lighting in game affects the result.')
        row = ttk.Frame(right)
        row.pack(fill='x')
        wood = ttk.Combobox(row, textvariable=self.wood_mode, values=['Original wood', 'Custom tint'], state='readonly', width=20)
        wood.pack(side='left', fill='x', expand=True)
        wood.bind('<<ComboboxSelected>>', self.render)
        ttk.Button(row, text='Colour…', command=self.choose_wood).pack(side='left', padx=(5, 0))
        self.wood_intensity_label=tk.StringVar(value='Wood intensity 100%')
        ttk.Label(right,textvariable=self.wood_intensity_label).pack(anchor='w',pady=(8,3))
        ttk.Scale(right,from_=0,to=2,variable=self.wood_intensity,command=self.render).pack(fill='x')
        ttk.Label(right, text='In-game thumbnail').pack(anchor='w', pady=(10, 5))
        row = ttk.Frame(right)
        row.pack(fill='x')
        self.thumb_preview = tk.Canvas(row, width=64, height=64, bg=FIELD, highlightthickness=0)
        self.thumb_preview.pack(side='left', padx=(0, 8))
        buttons = ttk.Frame(row)
        buttons.pack(side='left', fill='x', expand=True)
        ttk.Button(buttons, text='Custom image…', command=self.choose_thumbnail).pack(fill='x')
        ttk.Button(buttons, text='Use automatic', command=self.reset_thumbnail).pack(fill='x', pady=5)
        self.thumb_label = ttk.Label(right, text='Automatic: animation + ANIMATED' if self.is_gif() else 'Automatic: both images + LENTICULAR', wraplength=290)
        self.thumb_label.pack(anchor='w', pady=5)
        footer = ttk.Frame(root, padding=(18, 12))
        footer.grid(row=2, column=0, sticky='ew')
        footer.columnconfigure(0, weight=1, uniform='ends')
        footer.columnconfigure(1, weight=1)
        footer.columnconfigure(2, weight=1, uniform='ends')
        disclaimer = tk.Label(footer, text='DISCLAIMER', bg=BG, fg=MUTED, font=('Segoe UI', 9, 'underline'))
        disclaimer.grid(row=0, column=0, sticky='w')
        Tooltip(disclaimer, "This tool is in beta, like genuinely.\nIf something breaks, we're sorry, make\na note of it and report it")
        ttk.Label(footer, textvariable=self.deck_name, anchor='center').grid(row=0, column=1, sticky='ew')
        buttons = ttk.Frame(footer)
        buttons.grid(row=0, column=2, sticky='e')
        self.help(buttons, 'Export .fbmod saves the selected deck. Export all puts every deck in this workspace into one .fbmod. Neither button installs anything.')
        self.pack_button = ttk.Button(buttons, text='Export all (1)', command=self.export_pack)
        self.pack_button.pack(side='left', padx=5)
        self.export_button = ttk.Button(buttons, text='Export .fbmod', command=self.export)
        self.export_button.pack(side='left')
        ttk.Label(footer, textvariable=self.status, wraplength=1080).grid(row=1, column=0, columnspan=3, sticky='w', pady=(8, 0))
        self.deck_name.trace_add('write', self.rename_deck)
        self.decks = [self.project_data()]
        self.draw_list()
        self.update_mode()
        self.update_labels()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.dirty = False
        self.baseline = self.workspace_data()
        root.after(150, self.poll)
        root.after(1000, self.check_updates)

    def check_updates(self):
        def run():
            from updates import check_for_update
            release = check_for_update()
            if release:
                self.events.put(('update_available', release))
        threading.Thread(target=run, daemon=True).start()

    def open_update(self):
        if self.update_release:
            import webbrowser
            webbrowser.open(self.update_release.url)

    def rotate_quote(self):
        self.quote = random.choice([quote for quote in QUOTES if quote!=self.quote])
        self.root.title(APP_NAME+' v'+APP_VERSION+' — '+self.quote)

    def style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', background=BG, foreground=TEXT, font=('Segoe UI', 10))
        style.configure('TButton', background=FIELD, padding=(8, 5), borderwidth=0)
        style.map('TButton', background=[('active', '#49515c'), ('disabled', BG)])
        style.configure('TEntry', fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT, padding=5)
        style.configure('TCombobox', fieldbackground=FIELD, background=FIELD, padding=4)
        style.map('TCombobox', fieldbackground=[('readonly', FIELD)], foreground=[('readonly', TEXT)])
        style.configure('TScale', troughcolor=FIELD, background='#8090a5')
        self.root.option_add('*TCombobox*Listbox.background', FIELD)
        self.root.option_add('*TCombobox*Listbox.foreground', TEXT)

    def help(self, parent, text):
        button = ttk.Button(parent, text='?', width=2)
        button.pack(side='left', padx=6)
        Tooltip(button, text)

    def slider(self, parent, title, variable, action, explanation):
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=(8, 3))
        ttk.Label(row, textvariable=title).pack(side='left')
        self.help(row, explanation)
        ttk.Scale(parent, from_=0, to=1, variable=variable, command=action).pack(fill='x')

    def is_layers(self):
        return self.mode.get() == MODES['layers']

    def is_depth(self):
        return self.mode.get() in (MODES['depth'], MODES['layers'])

    def update_labels(self, *args):
        self.strength_label.set(f'Depth strength {self.strength.get()*100:.0f}%')
        self.bands_label.set(f'Lens texture {self.bands.get()*100:.0f}%')
        self.convergence_label.set(f'{"Background motion" if self.is_layers() else "Stationary depth"} {self.convergence.get()*100:.0f}%')

    def is_gif(self):
        return self.mode.get() == MODES["gif"]

    def animate(self):
        self.animation_job = None
        if self.busy:
            self.animation_job=self.root.after(150,self.animate)
            return
        if self.is_gif() and self.animation_clip:
            self.render()
            self.animation_job = self.root.after(16, self.animate)

    def update_mode(self):
        if self.is_gif():
            self.gif_controls.pack(fill='x',after=self.depth_anchor)
        else:
            self.gif_controls.pack_forget()
        self.fit_box.configure(state='disabled' if self.is_gif() else 'readonly')
        self.angle_control.configure(state='disabled' if self.is_gif() else 'normal')
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None
        if self.is_gif():
            self.image_frames[1].pack_forget()
            self.swap_button.pack_forget()
            self.animation_job = self.root.after(15, self.animate)
        else:
            self.image_frames[1].pack(fill="x", pady=(0,10), after=self.image_frames[0])
            self.swap_button.pack(fill="x", after=self.image_frames[1])
        self.swap_button.configure(text='Reverse depth' if self.is_depth() else 'Swap A / B')
        if self.is_depth():
            self.depth_controls.pack(fill='x', after=self.depth_anchor)
        else:
            self.depth_controls.pack_forget()
        if self.mode.get() == MODES['depth']:
            self.auto_row.pack(fill='x', before=self.swap_button, pady=6)
        else:
            self.auto_row.pack_forget()
        if self.is_layers():
            self.background_fit_row.pack(fill='x',pady=4)
        else:
            self.background_fit_row.pack_forget()
        self.fit_title.configure(text='Foreground sizing' if self.is_layers() else 'Image sizing')
        titles = ['Animation (GIF / APNG / WebP)', 'Unused'] if self.is_gif() else ['Foreground', 'Background'] if self.is_layers() else ['Colour image', 'Depth map'] if self.is_depth() else ['Image A', 'Image B']
        for panel, title in zip(self.image_frames, titles):
            panel.configure(text=title)

    def change_mode(self, *args):
        if self.busy:
            return
        self.update_mode()
        self.bands.set(.25 if self.is_layers() else 1)
        self.images = [None, None]
        self.refresh_images()

    def project_data(self):
        data = dict(version=4, mode='gif' if self.is_gif() else 'layers' if self.is_layers() else 'depth' if self.is_depth() else 'classic', name=self.deck_name.get(), author=self.author.get(), images=list(self.paths), fit=self.fit.get(), background=self.background, thumbnail=self.thumbnail_path, depth=dict(strength=self.strength.get(), convergence=self.convergence.get(), invert=self.invert.get(), bands=self.bands.get()))
        data['placement'] = copy.deepcopy(self.placements)
        data['animation'] = dict(quality={'Standard (512 × 4096)':1,'High (1024 × 8192)':2,'Ultra (2048 × 16384)':4}[self.gif_quality.get()])
        data['background_fit'] = self.background_fit.get()
        data['wood_tint'] = self.wood_colour if self.wood_mode.get() != 'Original wood' else None
        data['wood_intensity'] = self.wood_intensity.get()
        return data

    def read_image(self, path, index):
        if self.is_gif():
            if self.animation_path != path:
                self.animation_clip = animation.load(path)
                self.animation_path = path
                self.animation_start = time.monotonic()
            return animation_texture.preview_frame(self.animation_clip,0,self.background,self.placements[0])
        fit = self.background_fit.get() if self.is_layers() and index==1 else self.fit.get()
        image = image_placement.frame(path, fit, self.background, self.placements[index],
                                      alpha=self.is_layers() and index == 0,
                                      depth=self.is_depth() and not self.is_layers() and index == 1)
        if self.is_depth() and not self.is_layers() and index == 1:
            return (ImageOps.invert(image) if self.invert.get() else image).convert('RGB')
        return image

    def remember(self):
        self.decks[self.selected] = self.project_data()

    def workspace_data(self):
        self.remember()
        return copy.deepcopy(dict(version=5, selected=self.selected, decks=self.decks))

    def draw_list(self):
        self.deck_list.delete(0, 'end')
        for deck in self.decks:
            self.deck_list.insert('end', deck['name'] or 'Untitled deck')
        self.deck_list.selection_set(self.selected)
        self.pack_button.configure(text=f'Export all ({len(self.decks)})')

    def rename_deck(self, *args):
        if self.decks and not self.loading:
            self.decks[self.selected]['name'] = self.deck_name.get()
            self.draw_list()

    def select_deck(self, event=None):
        choice = self.deck_list.curselection()
        if not choice or self.busy or choice[0] == self.selected:
            return
        self.remember()
        self.selected = choice[0]
        self.apply_project(self.decks[self.selected])

    def add_deck(self):
        if self.busy:
            return
        self.remember()
        data = copy.deepcopy(self.decks[self.selected])
        used = {deck['name'] for deck in self.decks}
        number = len(self.decks)+1
        while f'My deck {number}' in used:
            number += 1
        data.update(name=f'My deck {number}', images=[None, None], thumbnail=None,
                    placement=[dict(zoom=1, x=0, y=0), dict(zoom=1, x=0, y=0)])
        self.decks.append(data)
        self.selected = len(self.decks)-1
        self.apply_project(data)

    def remove_deck(self):
        if self.busy or len(self.decks) == 1:
            return
        if messagebox.askyesno('Remove deck', 'Remove this deck from the workspace? Source images will be kept.'):
            del self.decks[self.selected]
            self.selected = min(self.selected, len(self.decks)-1)
            self.apply_project(self.decks[self.selected])

    def apply_project(self, data):
        self.loading = True
        if self.preview_job:
            self.root.after_cancel(self.preview_job)
            self.preview_job = None
        try:
            self.mode.set(MODES[data['mode']])
            self.deck_name.set(data['name'])
            self.author.set(data.get('author', ''))
            self.fit.set(data.get('fit', 'Stretch'))
            self.background_fit.set(data.get('background_fit','Crop to fill'))
            self.gif_quality.set({1:'Standard (512 × 4096)',2:'High (1024 × 8192)',4:'Ultra (2048 × 16384)'}.get(data.get('animation',{}).get('quality',2),'High (1024 × 8192)'))
            self.placement_index = None
            self.placement_controls.pack_forget()
            self.background = data.get('background', '#ffffff')
            settings = data.get('depth', {})
            for key, default in [('strength', .04), ('convergence', .5), ('bands', 1), ('invert', False)]:
                getattr(self, key).set(settings.get(key, default))
            self.paths = list(data['images'])
            self.images, self.depth_preview = [None, None], None
            self.thumbnail_path = data.get('thumbnail')
            self.placements = copy.deepcopy(data.get('placement', [dict(zoom=1, x=0, y=0)]*2))
            self.wood_colour = data.get('wood_tint') or '#b98a56'
            self.wood_mode.set('Custom tint' if data.get('wood_tint') else 'Original wood')
            self.wood_intensity.set(data.get('wood_intensity',1))
            for label, canvas in zip(self.labels, self.canvases):
                label.configure(text='No image selected')
                canvas.delete('all')
            self.preview.delete('all')
            self.thumb_preview.delete('all')
            self.update_mode()
            self.refresh_images()
            self.draw_list()
        finally:
            self.loading = False

    def load_study(self):
        if self.busy:
            return
        self.mode.set(MODES['depth'])
        self.update_mode()
        self.deck_name.set('3D Lens Study')
        from auto_depth import DATA
        self.paths = list(map(str, engine.depth_views.depth_study(DATA/'demo')))
        self.strength.set(.16)
        self.convergence.set(.5)
        self.invert.set(False)
        self.refresh_images()

    def choose(self, index):
        if self.busy:
            return
        path = filedialog.askopenfilename(title='Choose image', filetypes=[('Images', '*.gif *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff')])
        if path:
            self.paths[index] = path
            self.refresh_images()

    def refresh_images(self, *args):
        if self.busy:
            return
        self.preview_job = None
        self.gif_frames.clear()
        self.last_frame_key = None
        for index, path in enumerate(self.paths):
            if self.is_gif() and index == 1:
                self.images[index] = None
                continue
            if path:
                try:
                    image = self.read_image(path, index)
                    self.images[index] = image
                    self.labels[index].configure(text=Path(path).name)
                    self.paint(self.canvases[index], image, (34, 136))
                except Exception as exc:
                    self.images[index] = None
                    self.status.set(str(exc))
        self.rebuild_depth()
        self.render()
        self.render_thumbnail()
        if self.is_gif() and self.animation_clip and self.animation_job is None:
            self.animation_job = self.root.after(15, self.animate)

    def swap(self):
        if self.busy:
            return
        if self.is_depth():
            self.invert.set(not self.invert.get())
        else:
            self.paths.reverse()
            self.placements.reverse()
        self.refresh_images()

    def paint(self, canvas, image, size):
        photo = ImageTk.PhotoImage(image.resize(size, Image.Resampling.LANCZOS))
        canvas.image = photo
        canvas.delete('all')
        canvas.create_image(0, 0, anchor='nw', image=photo)

    def render(self, *args):
        if self.render_job is None:
            self.render_job = self.root.after(16, self.render_now)

    def render_now(self):
        if self.render_job is not None:
            self.root.after_cancel(self.render_job)
            self.render_job = None
        self.wood_intensity_label.set(f'Wood intensity {self.wood_intensity.get()*100:.0f}%')
        if all(image is None for image in self.images):
            self.preview.delete('all')
            if self.large_preview is not None and self.large_preview.winfo_exists():
                self.large_preview.delete('all')
            return
        width = max(40, min(256, (self.preview.winfo_height()-28)//4, self.preview.winfo_width()-32, 140))
        if self.large_preview is not None and self.large_preview.winfo_exists():
            width = max(width, min(360, (self.large_preview.winfo_height()-28)//4, self.large_preview.winfo_width()-32))
        size = (width, width*4)
        key = (self.preview_revision, self.mode.get(), round(self.angle.get(), 5), self.bands.get(), size)
        if self.is_gif() and self.animation_clip and self.images[0] is not None:
            elapsed=(time.monotonic()-self.animation_start)*1000
            index=self.animation_clip.frame_index(elapsed % self.animation_clip.duration_ms)
            key = (self.preview_revision, 'gif', index, size)
            frame_key = (index, size)
            if frame_key not in self.gif_frames:
                self.gif_frames[frame_key] = animation_texture.preview_frame(self.animation_clip,index,self.background,self.placements[0]).resize(size,Image.Resampling.LANCZOS)
                while len(self.gif_frames)>4:
                    self.gif_frames.pop(next(iter(self.gif_frames)))
            out = self.gif_frames[frame_key]
        elif any(image is None for image in self.images):
            out = next(image for image in self.images if image is not None)
        elif self.atlas_preview is not None:
            if key != self.last_frame_key:
                self.atlas_preview.set_lens_strength(self.bands.get())
                self.last_frame = self.atlas_preview.render(self.angle.get(), size)
            out = self.last_frame
        else:
            return
        self.last_frame_key = key
        self.update_lens_detail()
        draw_key = (key, self.wood_colour, self.wood_mode.get(), self.wood_intensity.get(), self.show_trucks.get(),
                    self.preview.winfo_width(), self.preview.winfo_height(),
                    (self.large_preview.winfo_width(),self.large_preview.winfo_height()) if self.large_preview is not None and self.large_preview.winfo_exists() else None)
        if draw_key == self.last_draw_key:
            return
        self.last_draw_key = draw_key
        self.draw_deck_preview(self.preview,out,560)
        if self.large_preview is not None and self.large_preview.winfo_exists():
            self.draw_deck_preview(self.large_preview,out)

    def draw_deck_preview(self,canvas,out,limit=None):
        height = max(80,min(canvas.winfo_height()-28,(canvas.winfo_width()-32)*4))
        if limit is not None:
            height=min(limit,height)
        width = height//4
        out = out.resize((width, height), Image.Resampling.LANCZOS).convert('RGBA')
        mask = Image.new('L', out.size)
        ImageDraw.Draw(mask).rounded_rectangle((0,0,width-1,height-1), radius=width//2, fill=255)
        out.putalpha(ImageChops.multiply(out.getchannel('A'),mask))
        photo = ImageTk.PhotoImage(out)
        canvas.image = photo
        canvas.delete('all')
        x, y = (canvas.winfo_width()-width)//2, (canvas.winfo_height()-height)//2
        colour = self.wood_colour if self.wood_mode.get() != 'Original wood' else '#8c704e'
        if self.wood_mode.get()!='Original wood':
            colour='#'+''.join(f'{min(255,round(int(colour[i:i+2],16)*self.wood_intensity.get())):02x}' for i in (1,3,5))
        canvas.create_rectangle(x-3, y+width//2, x+width+3, y+height-width//2, fill=colour, outline=colour)
        canvas.create_image(x, y, anchor='nw', image=photo)
        if self.show_trucks.get():
            for centre in (.225,.775):
                cy=y+height*centre
                canvas.create_rectangle(x+width*.29,cy-height*.025,x+width*.71,cy+height*.025,outline='#b7bec5',dash=(4,3),width=1)
                canvas.create_line(x-width*.08,cy,x+width*1.08,cy,fill='#b7bec5',dash=(4,3),width=2)
                for bx in (.36,.64):
                    for by in (-.017,.017):
                        px,py=x+width*bx,cy+height*by
                        canvas.create_oval(px-2,py-2,px+2,py+2,fill='#b7bec5',outline='')

    def enlarge_preview(self):
        if self.large_preview is not None and self.large_preview.winfo_exists():
            self.large_preview.winfo_toplevel().lift()
            return
        window=tk.Toplevel(self.root)
        window.title('Deck preview')
        window.geometry('650x900')
        window.minsize(360,480)
        window.columnconfigure(0,weight=1)
        window.rowconfigure(0,weight=1)
        self.large_preview=tk.Canvas(window,bg='#1d1f22',highlightthickness=0)
        self.large_preview.grid(row=0,column=0,sticky='nsew',padx=12,pady=12)
        self.large_preview.bind('<Configure>',self.render)
        ttk.Scale(window,from_=-1,to=1,variable=self.angle,command=self.render).grid(row=1,column=0,sticky='ew',padx=20)
        ttk.Checkbutton(window,text='Approximate truck positions',variable=self.show_trucks,command=self.render).grid(row=2,column=0,pady=8)
        ttk.Label(window,text='Note: may not reflect 1:1 in game').grid(row=3,column=0,pady=(0,12))
        window.bind('<Escape>',lambda event:window.destroy())
        self.render()

    def lens_detail(self):
        if self.atlas_preview is None or self.is_gif():
            messagebox.showinfo('Lens detail', 'Choose both images and wait for the effect preview first.')
            return
        window = tk.Toplevel(self.root)
        self.detail_window = window
        window.title('Lens detail — enlarged centre crop')
        ttk.Label(window, text='Same viewing angle, enlarged centre crop. Before game lighting.').pack(padx=16,pady=12)
        row = ttk.Frame(window)
        row.pack(padx=16)
        sample = copy.copy(self.atlas_preview)
        sample.settings = sample.settings.copy()
        sample.cached_size, sample.cached_samples = None, None
        self.detail_sample = sample
        self.detail_revision = self.preview_revision
        self.detail_key = None
        self.detail_canvases = []
        self.detail_labels = []
        for label in ('Lens texture 0%', 'Current lens texture'):
            column = ttk.Frame(row)
            column.pack(side='left',padx=8)
            title = ttk.Label(column,text=label)
            title.pack(pady=6)
            self.detail_labels.append(title)
            canvas = tk.Canvas(column,width=280,height=280,highlightthickness=0)
            canvas.pack()
            self.detail_canvases.append(canvas)
        ttk.Label(window,text='Move the viewing angle or lens slider to compare.').pack(pady=12)
        window.bind('<Escape>',lambda event:window.destroy())
        self.update_lens_detail()

    def update_lens_detail(self):
        window = getattr(self,'detail_window',None)
        if window is None or not window.winfo_exists() or self.atlas_preview is None:
            return
        if self.detail_revision != self.preview_revision:
            self.detail_sample = copy.copy(self.atlas_preview)
            self.detail_sample.settings = self.detail_sample.settings.copy()
            self.detail_sample.cached_size, self.detail_sample.cached_samples = None, None
            self.detail_revision = self.preview_revision
        key = (self.preview_revision,self.angle.get(),self.bands.get())
        if key == self.detail_key:
            return
        self.detail_key = key
        self.detail_labels[1].configure(text=f'Lens texture {self.bands.get()*100:.0f}%')
        for canvas,strength in zip(self.detail_canvases,(0,self.bands.get())):
            self.detail_sample.set_lens_strength(strength)
            image = self.detail_sample.render(self.angle.get(),(280,280),(.375,.46875,.625,.53125))
            self.paint(canvas,image,(280,280))

    def render_thumbnail(self):
        self.thumb_label.configure(text=Path(self.thumbnail_path).name if self.thumbnail_path else 'Automatic: animation + ANIMATED' if self.is_gif() else 'Automatic: both images + LENTICULAR')
        try:
            if self.thumbnail_path or (self.is_gif() and self.images[0] is not None) or all(image is not None for image in self.images):
                sources = [self.depth_preview[0], self.depth_preview[-1]] if self.is_depth() and self.depth_preview else self.images
                if self.is_gif():
                    sources = [self.images[0], self.images[0]]
                thumbnail = engine.thumbnail(*sources, self.thumbnail_path, size=64, label="ANIMATED" if self.is_gif() else "LENTICULAR")
                self.paint(self.thumb_preview, thumbnail, (64,64))
        except Exception as exc:
            self.status.set('Thumbnail: '+str(exc))

    def choose_wood(self):
        colour = colorchooser.askcolor(self.wood_colour, title='Base wood colour')[1]
        if colour:
            self.wood_colour = colour
            self.wood_mode.set('Custom tint')
            self.render()

    def adjust_placement(self, index):
        if self.busy or not self.paths[index]:
            return
        self.placement_index = index
        if not self.is_depth():
            self.angle.set(-1 if index==0 else 1)
        self.placement_title.set('Adjust '+self.image_frames[index].cget('text')+' — live preview')
        for key,variable in self.placement_vars.items():
            variable.set(self.placements[index].get(key,1 if key=='zoom' else 0))
        self.update_placement_labels()
        self.placement_controls.pack(fill='x',before=self.angle_control,pady=8)
        self.render()

    def update_placement_labels(self):
        for key,(title,output) in self.placement_outputs.items():
            output.set(f'{title}: {self.placement_vars[key].get()*100:.0f}%')

    def move_image(self, *args):
        if self.placement_index is None or self.busy:
            return
        index = self.placement_index
        setting = {key:variable.get() for key,variable in self.placement_vars.items()}
        self.placements[index] = setting
        if self.is_depth() and not self.is_layers():
            self.placements[1-index] = copy.deepcopy(setting)
        self.update_placement_labels()
        if self.preview_job is None:
            self.preview_job = self.root.after(60,self.refresh_images)

    def reset_placement(self):
        for key,variable in self.placement_vars.items():
            variable.set(1 if key=='zoom' else 0)
        self.move_image()

    def save_project(self):
        if self.busy:
            return False
        path = filedialog.asksaveasfilename(title='Save workspace', defaultextension='.lenticular.json', initialfile='Deck workspace.lenticular.json', filetypes=[('Lenticular project','*.lenticular.json')])
        if not path:
            return False
        try:
            data = self.workspace_data()
            Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf8')
            self.baseline = copy.deepcopy(data)
            self.status.set('Workspace saved. Source images remain in their original locations.')
            return True
        except Exception as exc:
            messagebox.showerror('Cannot save workspace', str(exc))
            return False

    def load_project(self):
        if self.busy or not self.confirm_discard():
            return
        path = filedialog.askopenfilename(title='Open project or workspace', filetypes=[('Lenticular project','*.lenticular.json'),('JSON','*.json')])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding='utf8'))
            decks = data['decks'] if data.get('version') == 5 else [data]
            if not decks:
                raise ValueError('No decks found in this workspace.')
            for deck in decks:
                if deck['mode'] not in MODES or len(deck['images']) != 2:
                    raise ValueError('Invalid deck settings.')
                deck['images'] = [str((Path(path).parent/p).resolve()) if p else None for p in deck['images']]
                if deck.get('thumbnail'):
                    deck['thumbnail'] = str((Path(path).parent/deck['thumbnail']).resolve())
            self.decks = decks
            self.selected = max(0,min(data.get('selected',0),len(decks)-1))
            self.apply_project(decks[self.selected])
            self.baseline = self.workspace_data()
        except Exception as exc:
            messagebox.showerror('Cannot open project', str(exc))

    def confirm_discard(self):
        if self.workspace_data() == self.baseline:
            return True
        result = messagebox.askyesnocancel('Save changes?', 'Save this workspace before continuing?')
        return self.save_project() if result else result is False

    def close(self):
        if self.busy:
            messagebox.showinfo('Export in progress', 'Wait for the export to finish before closing.')
        elif self.confirm_discard():
            self.root.destroy()

    def export(self):
        self.start_export(False)

    def export_pack(self):
        self.start_export(True)

    def start_export(self, all_decks):
        if self.busy:
            return
        self.remember()
        projects = copy.deepcopy(self.decks if all_decks else [self.decks[self.selected]])
        try:
            for project in projects:
                engine.validate_name(project['name'])
                if not (project['images'][0] if project.get('mode') == 'gif' else all(project['images'])):
                    raise ValueError('Choose both images for '+project['name']+'.')
            if len({engine.validate_name(p['name']).casefold() for p in projects}) != len(projects):
                raise ValueError('Give each deck a different name.')
        except ValueError as exc:
            messagebox.showerror('Check the decks', str(exc))
            return
        title = 'Lenticular Deck Pack' if all_decks else projects[0]['name']
        path = filedialog.asksaveasfilename(title='Export mod', defaultextension='.fbmod', initialfile=title+'.fbmod', filetypes=[('ReSkate mod','*.fbmod')])
        if not path:
            return
        self.busy = True
        self.export_button.configure(state='disabled')
        self.pack_button.configure(state='disabled')
        self.status.set('Preparing export…')
        author = self.author.get()
        def run():
            try:
                result = engine.export_pack(projects, path, lambda msg:self.events.put(('status',msg)), title=title, author=author)
                self.events.put(('done',str(result)))
            except Exception as exc:
                from auto_depth import DATA
                DATA.mkdir(parents=True,exist_ok=True)
                (DATA/'last-error.txt').write_text(traceback.format_exc())
                self.events.put(('error',str(exc)))
        threading.Thread(target=run,daemon=True).start()

    def poll(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'update_available':
                self.update_release = value
                self.update_button.pack(side='right', padx=8)
                continue
            if kind in ('preview_ready', 'preview_failed'):
                self.preview_worker = False
                revision, result, thumbnails = value
                if revision == self.preview_revision:
                    if kind == 'preview_ready' and result is not None:
                        self.atlas_preview, self.depth_preview = result, thumbnails
                        self.last_frame_key = None
                        self.render()
                        self.render_thumbnail()
                    elif kind == 'preview_failed' and not self.busy:
                        self.status.set('Preview: '+result)
                self.start_preview_build()
                continue
            if kind == 'status':
                self.status.set(value)
                continue
            self.busy = False
            self.export_button.configure(state='normal')
            self.pack_button.configure(state='normal')
            if kind == 'done':
                self.status.set('Saved: ' + value)
                messagebox.showinfo('Export complete',
                    'Saved your .fbmod.\n\nImport it in Studio to install it. '
                    'Find each deck by its chosen name in the board menu.\n\n'
                    'The export has not installed or enabled anything.')
            else:
                self.status.set('Export failed.')
                messagebox.showerror('Export failed', value)
        self.root.after(150, self.poll)

    def choose_background(self):
        if self.busy:
            return
        color = colorchooser.askcolor(self.background, title='Transparency and padding colour')[1]
        if color:
            self.background = color
            self.refresh_images()

    def choose_thumbnail(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(title='Choose custom thumbnail', filetypes=[('Images', '*.gif *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff'), ('All files', '*.*')])
        if not path:
            return
        try:
            with Image.open(path) as im:
                im.verify()
        except Exception as e:
            messagebox.showerror('Cannot open thumbnail', str(e))
            return
        self.thumbnail_path = path
        self.render_thumbnail()

    def rebuild_depth(self):
        self.preview_revision += 1
        self.atlas_preview = None
        self.depth_preview = None
        self.last_frame_key = self.last_draw_key = None
        self.preview_pending = None
        if self.is_gif() or not all(image is not None for image in self.images):
            return
        for canvas in (self.preview, self.large_preview):
            if canvas is not None and canvas.winfo_exists():
                canvas.delete('all')
                canvas.create_text(canvas.winfo_width()//2,canvas.winfo_height()//2,text='Preparing effect preview…',fill=MUTED)
        mode = 'layers' if self.is_layers() else 'depth' if self.is_depth() else 'classic'
        self.preview_pending = (self.preview_revision, mode, tuple(image.copy() for image in self.images),
                                self.strength.get(), self.convergence.get(), self.bands.get(), self.invert.get())
        self.start_preview_build()

    def start_preview_build(self):
        if self.preview_worker or self.preview_pending is None:
            return
        revision, mode, images, strength, convergence, bands, reverse = self.preview_pending
        self.preview_pending = None
        self.preview_worker = True
        def run():
            thumbnails = None
            try:
                def progress(message):
                    if revision != self.preview_revision:
                        raise InterruptedError()
                if mode == 'classic':
                    atlas = engine.atlas(*images)
                elif mode == 'layers':
                    atlas = engine.layer_atlas.pack(*images, strength, convergence, bands, reverse)
                else:
                    views = preview_depth.views(*images, strength, convergence, progress)
                    atlas = engine.depth_views.pack(views, bands, balanced=True)
                    thumbnails = [views[0], views[-1]]
                progress('')
                preview = effect_preview.AtlasPreview(atlas, mode)
                self.events.put(('preview_ready',(revision, preview, thumbnails)))
            except InterruptedError:
                self.events.put(('preview_ready',(revision, None, None)))
            except Exception as exc:
                self.events.put(('preview_failed',(revision, str(exc), None)))
        threading.Thread(target=run, daemon=True).start()

    def reset_thumbnail(self):
        if self.busy:
            return
        self.thumbnail_path = None
        self.render_thumbnail()

    def schedule_depth(self, *args):
        if self.preview_job:
            self.root.after_cancel(self.preview_job)
        self.preview_job = self.root.after(200, self.refresh_images)

    def generate_depth(self):
        from auto_depth import generate_dialog
        generate_dialog(self)


def main():
    from first_run import show_shader_warning
    import sys
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ReSkate.DeckTool.Beta')
    root = tk.Tk()
    Creator(root)
    root.update_idletasks()
    if show_shader_warning(root):
        root.mainloop()
    else:
        root.destroy()
