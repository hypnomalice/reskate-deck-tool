import copy
import json
import os
import queue
import random
import sys
import threading
import time
import uuid
import numpy as np
from pathlib import Path

from PIL import Image, ImageOps
from PySide6.QtCore import Qt, QTimer, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPalette, QImage
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QPushButton, QToolButton, QLineEdit, QComboBox, QSlider,
    QDoubleSpinBox, QAbstractSpinBox, QCheckBox, QGroupBox, QScrollArea, QSplitter,
    QTabBar, QFileDialog, QColorDialog, QMessageBox, QDialog, QTextBrowser, QTabWidget)

import creator_engine as engine
import animation
import animation_texture
import image_placement
import preview_depth
import live_placement
from effect_preview import AtlasPreview
from app_version import APP_VERSION
from studio_ui import MODES, QUOTES, APP_NAME

ROOT = Path(__file__).resolve().parent
THEME = '''
QWidget { color:#e4e7eb; font-size:12px; }
QMainWindow,QDialog { background:#24272b; }
QScrollArea { border:0; }
QGroupBox { border:1px solid #41474e; border-radius:4px; margin-top:9px; padding:12px 9px 9px; }
QGroupBox::title { subcontrol-origin:margin; left:9px; padding:0 4px; }
QLineEdit,QComboBox { background:#1d2024; border:1px solid #505860; border-radius:3px; padding:5px; min-height:17px; }
QDoubleSpinBox QLineEdit { padding:0; border:0; min-height:0; background:transparent; }
QDoubleSpinBox { background:#1d2024; color:#e4e7eb; }
QPushButton,QToolButton { background:#30353b; border:1px solid #505860; border-radius:3px; padding:5px 9px; min-height:18px; }
QToolButton { padding:1px; }
QPushButton:hover,QToolButton:hover { border-color:#8cb5ca; }
QPushButton#primary { background:#356b86; border-color:#6e9db6; }
QSlider::groove:horizontal { height:4px; background:#50575f; border-radius:2px; }
QSlider::sub-page:horizontal { background:#8bbbd3; border-radius:2px; }
QSlider::handle:horizontal { width:14px; margin:-5px 0; background:#b8d6e5; border:1px solid #24272b; border-radius:7px; }
QTabBar::tab { padding:8px 18px; background:#2b3036; border:1px solid #41474e; }
QTabBar::tab:selected { background:#3b444e; border-bottom:2px solid #8bbbd3; }
QMenuBar,QMenu { background:#24272b; }
QMenu::item:selected { background:#356b86; }
QLabel#muted { color:#aeb7c1; }
QToolTip { background:#30353b; color:#e4e7eb; border:1px solid #71808e; padding:8px; }
'''


def qt_image(image):
    image = image.convert('RGBA')
    return QImage(image.tobytes(),image.width,image.height,image.width*4,QImage.Format_RGBA8888).copy()


def button(text, action, layout):
    widget = QPushButton(text)
    widget.clicked.connect(action)
    layout.addWidget(widget)
    return widget


def help_button(text, layout):
    widget = QToolButton()
    widget.setText('?')
    widget.setToolTip(text)
    widget.setFixedSize(24,24)
    layout.addWidget(widget)
    return widget


class Adjustment(QWidget):
    changed = Signal(float)

    def __init__(self, title, value=0, low=0, high=100, tip=''):
        super().__init__()
        box = QVBoxLayout(self)
        box.setContentsMargins(0,0,0,0)
        box.setSpacing(4)
        top = QHBoxLayout()
        self.title = QLabel(title)
        top.addWidget(self.title)
        top.addStretch()
        if tip:
            help_button(tip,top)
        self.spin = QDoubleSpinBox()
        self.spin.setRange(low,high)
        self.spin.setDecimals(0)
        self.spin.setSuffix(' %')
        self.spin.setFixedWidth(78)
        self.spin.setKeyboardTracking(False)
        self.spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        top.addWidget(self.spin)
        for label, delta in [('−',-1),('+',1)]:
            tool = QToolButton()
            tool.setText(label)
            tool.setFixedSize(24,25)
            tool.clicked.connect(lambda checked=False,d=delta:self.spin.setValue(self.spin.value()+d))
            top.addWidget(tool)
        box.addLayout(top)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(low,high)
        self.slider.setPageStep(5)
        self.slider.setMinimumHeight(24)
        box.addWidget(self.slider)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self._changed)
        self.set_value(value)

    def _changed(self,value):
        self.slider.setValue(round(value))
        self.changed.emit(value)

    def set_value(self,value):
        self.spin.blockSignals(True)
        self.slider.blockSignals(True)
        self.spin.setValue(value)
        self.slider.setValue(round(value))
        self.spin.blockSignals(False)
        self.slider.blockSignals(False)

    def value(self):
        return self.spin.value()


class Board(QWidget):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.wood = '#9a7855'
        self.guides = True
        self.setMinimumSize(250,180)

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(),QColor('#191c20'))
        h = min(self.height()-30,(self.width()-45)*4)
        w = h/4
        area = QRectF((self.width()-w)/2,(self.height()-h)/2,w,h)
        path = QPainterPath()
        path.addRoundedRect(area,w/2,w/2)
        painter.setPen(QPen(QColor(self.wood),5))
        painter.setBrush(QColor('#30353b'))
        painter.drawPath(path)
        if self.frame is not None:
            painter.save()
            painter.setClipPath(path)
            painter.drawPixmap(area,self.frame,QRectF(self.frame.rect()))
            painter.restore()
        else:
            painter.setPen(QColor('#aeb7c1'))
            painter.drawText(self.rect(),Qt.AlignCenter,'Choose artwork to preview')
        if self.guides:
            painter.setPen(QPen(QColor('#bec8d1'),1,Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            for centre in (.225,.775):
                y = area.top()+h*centre
                painter.drawRoundedRect(QRectF(area.left()+w*.28,y-h*.025,w*.44,h*.05),3,3)
                painter.drawLine(round(area.left()-8),round(y),round(area.right()+8),round(y))
                for x in (.36,.64):
                    for offset in (-.017,.017):
                        painter.drawEllipse(QRectF(area.left()+w*x-2,y+h*offset-2,4,4))


class DetailImage(QWidget):
    def __init__(self):
        super().__init__()
        self.image = None
        self.setFixedHeight(96)
        self.setMinimumWidth(0)

    def setPixmap(self,image):
        self.image = image
        self.update()

    def pixmap(self):
        return self.image

    def paintEvent(self,event):
        if self.image is not None:
            image = self.image.scaled(self.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation)
            painter = QPainter(self)
            painter.drawPixmap((self.width()-image.width())//2,(self.height()-image.height())//2,image)


def default_deck(name='My Lenticular Deck'):
    return dict(version=4,name=name,mode='classic',author='',images=[None,None],fit='Stretch',
        background_fit='Crop to fill',background='#ffffff',thumbnail=None,
        placement=[dict(zoom=1,x=0,y=0),dict(zoom=1,x=0,y=0)],
        depth=dict(strength=.04,convergence=.5,bands=1,invert=False),
        animation=dict(quality=2),wood_tint=None,wood_intensity=1)


class Creator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.quote = random.choice(QUOTES)
        self.setWindowTitle(f'{APP_NAME} v{APP_VERSION} — {self.quote}')
        self.setWindowIcon(QIcon(str(ROOT/'assets/app-icon.ico')))
        self.resize(1180,920)
        self.setMinimumSize(960,720)
        self.setStyleSheet(THEME)
        self.decks = [default_deck()]
        self.selected = 0
        self.loading = self.busy = self.worker = False
        self.events = queue.Queue()
        self.revision = 0
        self.display_revision = -1
        self.lens_source_key = self.clip_path = None
        self.placement_sources = None
        self.placement_source_key = None
        self.live_placement = False
        self.last_detail_key = None
        self.pending = None
        self.renderer = self.detail_renderer = self.clip = None
        self.gif_cache = {}
        self.started = time.monotonic()
        self.last_key = self.large = self.path = self.release = self.placement_index = None
        self.placement_open = False
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(150)
        self.preview_timer.timeout.connect(self.prepare)
        self.build_ui()
        self.apply_deck()
        self.baseline = self.workspace()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(30)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.render)
        self.animation_timer.start(16)
        QTimer.singleShot(1000,self.check_updates)

    def save_project(self):
        if self.busy:
            return False
        path,_ = QFileDialog.getSaveFileName(self,'Save project',str(self.path or 'Deck project.json'),'Deck project (*.json)')
        if not path:
            return False
        try:
            data = self.workspace()
            target = Path(path)
            temporary = target.with_suffix(target.suffix+'.tmp')
            temporary.write_text(json.dumps(data,indent=2),encoding='utf8')
            temporary.replace(target)
            self.path = target
            self.project_title.setText(target.stem)
            self.baseline = data
            return True
        except Exception as exc:
            QMessageBox.critical(self,'Cannot save',str(exc))
            return False

    def discard(self):
        if self.workspace()==self.baseline:
            return True
        result = QMessageBox.question(self,'Save changes?','Save this workspace before continuing?',QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
        return self.save_project() if result==QMessageBox.Save else result==QMessageBox.Discard

    def open_project(self):
        if self.busy or not self.discard():
            return
        path,_ = QFileDialog.getOpenFileName(self,'Open project','','Deck project (*.json)')
        if path:
            try:
                self.load_project(path)
            except Exception as exc:
                QMessageBox.critical(self,'Cannot open',str(exc))

    def load_project(self,path):
        data = json.loads(Path(path).read_text(encoding='utf8'))
        decks = data.get('decks',[data])
        if not decks:
            raise ValueError('The project contains no decks.')
        normalized = []
        for source in decks:
            deck = default_deck()
            deck.update(source)
            if deck['mode'] not in MODES or len(deck['images'])!=2:
                raise ValueError('Invalid deck settings.')
            deck['images'] = [str((Path(path).parent/p).resolve()) if p else None for p in deck['images']]
            if deck.get('thumbnail'):
                deck['thumbnail'] = str((Path(path).parent/deck['thumbnail']).resolve())
            normalized.append(deck)
        self.decks = normalized
        self.selected = max(0,min(data.get('selected',0),len(decks)-1))
        self.path = Path(path)
        self.project_title.setText(self.path.stem)
        self.apply_deck()
        self.baseline = self.workspace()

    def set_busy(self,busy):
        self.busy = busy
        for widget in (self.settings,self.tabs,self.add_button,self.export_button,self.pack_button,self.strength,self.bands,self.convergence,self.invert,self.placement):
            widget.setEnabled(not busy)
        if not busy:
            self.update_mode()

    def export(self,all_decks):
        if self.busy:
            return
        self.remember()
        projects = copy.deepcopy(self.decks if all_decks else [self.current()])
        try:
            for d in projects:
                engine.validate_name(d['name'])
                if not d['images'][0] or (d['mode']!='gif' and not all(d['images'])):
                    raise ValueError('Choose the images for '+d['name']+'.')
            if len({engine.validate_name(d['name']).casefold() for d in projects})!=len(projects):
                raise ValueError('Give each deck a different name.')
        except ValueError as exc:
            QMessageBox.warning(self,'Check the decks',str(exc))
            return
        title = 'Lenticular Deck Pack' if all_decks else projects[0]['name']
        path,_ = QFileDialog.getSaveFileName(self,'Export mod',title+'.fbmod','ReSkate mod (*.fbmod)')
        if not path:
            return
        self.set_busy(True)
        self.status.setText('Preparing export…')
        def run():
            try:
                result = engine.export_pack(projects,path,lambda message:self.events.put(('status',0,message)),title=title,author=projects[0].get('author',''))
                self.events.put(('export',0,str(result)))
            except Exception as exc:
                self.events.put(('error',0,str(exc)))
        threading.Thread(target=run,daemon=True).start()

    def guide(self):
        from tutorials import GUIDES
        dialog = QDialog(self)
        dialog.setWindowTitle('Deck Tool guide')
        dialog.resize(720,600)
        layout = QVBoxLayout(dialog)
        tabs = QTabWidget()
        for title,text in GUIDES.items():
            browser = QTextBrowser()
            browser.setPlainText(text)
            tabs.addTab(browser,title)
        layout.addWidget(tabs)
        button('Close',dialog.accept,layout)
        dialog.exec()

    def auto_depth(self):
        import auto_depth
        source = self.current()['images'][0]
        if not source:
            QMessageBox.information(self,'Choose artwork','Choose the colour image first.')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('Generate auto depthmap')
        dialog.setMinimumWidth(480)
        layout = QVBoxLayout(dialog)
        model = QComboBox()
        model.addItems(['Light (Small)','Full (Base)'])
        layout.addWidget(model)
        info = QLabel()
        info.setWordWrap(True)
        layout.addWidget(info)
        link = QLabel('<a href="model" style="color:#9db9c9">Optional component</a>')
        link.setToolTip('Open the selected AI model’s homepage')
        link.linkActivated.connect(lambda _:__import__('webbrowser').open(auto_depth.MODELS['full' if model.currentIndex() else 'light']['homepage']))
        layout.addWidget(link)
        def describe():
            data = auto_depth.MODELS['full' if model.currentIndex() else 'light']
            info.setText(f"Uses the Depth Anything V2 AI model locally. Optional download: {data['size']/1e6:.0f} MB.\n\nLicence: {data['licence']}.\n\nThis is an estimate. Fine details, text, transparency and layered artwork may be wrong. A carefully made depth map is more accurate. Your image stays on this PC.")
        model.currentIndexChanged.connect(describe)
        describe()
        button('Download if needed & generate',dialog.accept,layout)
        button('Cancel',dialog.reject,layout)
        if dialog.exec()!=QDialog.Accepted:
            return
        choice = 'full' if model.currentIndex() else 'light'
        selected = self.selected
        self.set_busy(True)
        self.status.setText('Checking optional component…')
        def run():
            try:
                if not auto_depth.valid_model(choice=choice):
                    auto_depth.download(lambda message:self.events.put(('status',0,message)),threading.Event(),choice=choice)
                self.events.put(('status',0,'Estimating depth locally…'))
                output = auto_depth.DATA/'generated'/f'depth-{uuid.uuid4().hex}.png'
                output.parent.mkdir(parents=True,exist_ok=True)
                auto_depth.estimate(source,output,choice=choice)
                self.events.put(('depth',selected,str(output)))
            except Exception as exc:
                self.events.put(('error',0,str(exc)))
        threading.Thread(target=run,daemon=True).start()

    def check_updates(self):
        def run():
            from updates import check_for_update
            self.events.put(('update',0,check_for_update()))
        threading.Thread(target=run,daemon=True).start()

    def open_update(self):
        if self.release:
            __import__('webbrowser').open(self.release.url)

    def closeEvent(self,event):
        if self.busy:
            QMessageBox.information(self,'Operation in progress','Wait for the current operation to finish before closing.')
            event.ignore()
        elif self.discard():
            event.accept()
        else:
            event.ignore()


    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(12,10,12,8)
        toolbar = QHBoxLayout()
        button('Open project…',self.open_project,toolbar)
        button('Save',self.save_project,toolbar)
        toolbar.addStretch()
        self.project_title = QLabel('Untitled project')
        self.project_title.setAlignment(Qt.AlignCenter)
        toolbar.addWidget(self.project_title,1)
        toolbar.addStretch()
        self.update_button = button('Update available',self.open_update,toolbar)
        self.update_button.hide()
        self.export_button = button('Export FBMOD',lambda:self.export(False),toolbar)
        self.pack_button = button('Export all',lambda:self.export(True),toolbar)
        self.pack_button.setObjectName('primary')
        help_button('Export FBMOD saves the selected deck. Export all puts every deck in this workspace into one FBMOD.',toolbar)
        outer.addLayout(toolbar)
        tabs = QHBoxLayout()
        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setTabsClosable(True)
        self.tabs.currentChanged.connect(self.select_deck)
        self.tabs.tabCloseRequested.connect(self.remove_deck)
        tabs.addWidget(self.tabs,1)
        self.add_button = button('+ Add deck',self.add_deck,tabs)
        outer.addLayout(tabs)
        splitter = QSplitter(Qt.Horizontal)
        self.settings = QWidget()
        left = QVBoxLayout(self.settings)
        left.setContentsMargins(0,0,5,0)
        form = QFormLayout()
        self.name,self.author = QLineEdit(),QLineEdit()
        self.mode = QComboBox()
        self.mode.addItems(MODES.values())
        self.mode.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.mode.setMinimumContentsLength(12)
        self.name.textEdited.connect(self.rename)
        self.author.textEdited.connect(lambda _:self.remember())
        self.mode.currentIndexChanged.connect(self.mode_changed)
        form.addRow('Deck name',self.name)
        form.addRow('Author',self.author)
        effect = QHBoxLayout()
        effect.addWidget(self.mode)
        help_button('Lenticular flips between two pictures as the angle changes.\nDepth map gives one image depth using a greyscale map.\nForeground/background moves two layers independently.\nAnimated GIF loops an animation on the underside.',effect)
        form.addRow('Effect',effect)
        left.addLayout(form)
        group = QGroupBox('Images')
        images = QVBoxLayout(group)
        self.image_labels,self.image_names,self.image_buttons = [],[],[]
        for index in range(2):
            label = QLabel()
            images.addWidget(label)
            self.image_labels.append(label)
            row = QHBoxLayout()
            name = QLineEdit()
            name.setReadOnly(True)
            name.setPlaceholderText('No image selected')
            row.addWidget(name,1)
            browse = button('Browse…',lambda checked=False,i=index:self.choose(i),row)
            self.image_names.append(name)
            self.image_buttons.append(browse)
            images.addLayout(row)
        row = QHBoxLayout()
        self.adjust_button = button('Adjust image…',self.adjust_image,row)
        self.swap_button = button('Swap images',self.swap,row)
        images.addLayout(row)
        row = QHBoxLayout()
        self.auto_button = button('Generate auto depthmap',self.auto_depth,row)
        self.auto_help = help_button('AI-generated depth is an estimate. A carefully made depth map is more accurate. An optional local component may need downloading.',row)
        images.addLayout(row)
        self.fit = QComboBox()
        self.fit.addItems(['Stretch','Crop to fill','Fit entire image'])
        self.fit.currentTextChanged.connect(self.changed)
        images.addWidget(QLabel('Artwork sizing'))
        images.addWidget(self.fit)
        self.backfit_label = QLabel('Background sizing (independent)')
        images.addWidget(self.backfit_label)
        self.backfit = QComboBox()
        self.backfit.addItems(['Stretch','Crop to fill','Fit entire image'])
        self.backfit.currentTextChanged.connect(self.changed)
        images.addWidget(self.backfit)
        button('Padding colour…',self.padding_colour,images)
        self.quality = QComboBox()
        self.quality.addItems(['Standard · 512 × 4096','High · 1024 × 8192','Ultra · 2048 × 16384'])
        self.quality.currentIndexChanged.connect(lambda _:self.remember())
        images.addWidget(self.quality)
        left.addWidget(group)
        wood = QGroupBox('Wood')
        woodbox = QVBoxLayout(wood)
        row = QHBoxLayout()
        self.wood_mode = QComboBox()
        self.wood_mode.addItems(['Original wood','Custom tint'])
        self.wood_mode.currentIndexChanged.connect(self.wood_changed)
        row.addWidget(self.wood_mode)
        button('Colour…',self.wood_colour,row)
        woodbox.addLayout(row)
        self.intensity = Adjustment('Intensity',100,high=200,tip='Brightness of the tinted wood. The wood grain is preserved in the exported texture.')
        self.intensity.changed.connect(self.wood_changed)
        woodbox.addWidget(self.intensity)
        left.addWidget(wood)
        thumb = QGroupBox('In-game thumbnail')
        thumbbox = QHBoxLayout(thumb)
        self.thumb = QLabel()
        self.thumb.setFixedSize(64,64)
        thumbbox.addWidget(self.thumb)
        thumbactions = QVBoxLayout()
        button('Custom image…',self.choose_thumbnail,thumbactions)
        button('Use automatic',self.reset_thumbnail,thumbactions)
        thumbbox.addLayout(thumbactions)
        left.addWidget(thumb)
        self.thumb_name = QLabel()
        self.thumb_name.setWordWrap(True)
        left.addWidget(self.thumb_name)
        button('Load depth test scene',self.load_study,left)
        left.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.settings)
        scroll.setMinimumWidth(280)
        splitter.addWidget(scroll)
        preview = QWidget()
        right = QVBoxLayout(preview)
        right.setContentsMargins(5,0,0,0)
        row = QHBoxLayout()
        self.preview_title = QLabel('Deck preview')
        row.addWidget(self.preview_title)
        row.addStretch()
        button('Enlarge…',self.enlarge,row)
        right.addLayout(row)
        row = QHBoxLayout()
        self.guides = QCheckBox('Truck guides')
        self.guides.setChecked(True)
        self.guides.toggled.connect(self.guides_changed)
        row.addWidget(self.guides)
        self.detail_toggle = QCheckBox('Lens detail')
        self.detail_toggle.setChecked(True)
        self.detail_toggle.toggled.connect(self.render_reset)
        row.addWidget(self.detail_toggle)
        row.addStretch()
        right.addLayout(row)
        self.board = Board()
        right.addWidget(self.board,1)
        inspector_pane = QWidget()
        inspector_layout = QVBoxLayout(inspector_pane)
        inspector_layout.setContentsMargins(5,0,0,0)
        self.detail_box = QGroupBox('Lens detail')
        self.detail_box.setToolTip('Enlarged crop, before game lighting. The comparison selects an area where the lens changes image detail.')
        detail = QHBoxLayout(self.detail_box)
        self.detail_images = []
        for title in ('Lens texture 0%','Current lens texture'):
            col = QVBoxLayout()
            label = QLabel(title)
            label.setAlignment(Qt.AlignCenter)
            col.addWidget(label)
            image = DetailImage()
            col.addWidget(image)
            detail.addLayout(col)
            self.detail_images.append((label,image))
        inspector_layout.addWidget(self.detail_box)
        self.placement = QGroupBox('Image placement · live preview')
        placement = QVBoxLayout(self.placement)
        self.placement_choice = QComboBox()
        self.placement_choice.addItems(['First image','Second image'])
        self.placement_choice.currentIndexChanged.connect(self.choose_placement)
        placement.addWidget(self.placement_choice)
        self.positions = {}
        for key,title,value,low,high in [('zoom','Scale',100,10,500),('x','Horizontal',0,-100,100),('y','Vertical',0,-100,100)]:
            control = Adjustment(title,value,low,high)
            control.changed.connect(self.move_image)
            control.slider.sliderReleased.connect(self.finish_placement)
            self.positions[key] = control
            placement.addWidget(control)
        row = QHBoxLayout()
        button('Reset',self.reset_placement,row)
        button('Done',self.close_placement,row)
        placement.addLayout(row)
        self.placement.setMinimumHeight(300)
        self.angle = Adjustment('Viewing angle',0,-100,100,tip='Sweep through the effect. This is a transition range, not a physical camera angle.')
        self.angle.changed.connect(self.render_reset)
        right.addWidget(self.angle)
        note = QLabel('Note: may not reflect 1:1 in game')
        note.setAlignment(Qt.AlignCenter)
        note.setObjectName('muted')
        right.addWidget(note)
        splitter.addWidget(preview)
        effectbox = QGroupBox('Effect settings')
        effects = QVBoxLayout(effectbox)
        self.strength = Adjustment('Depth strength',4,tip='Amount of parallax. Higher values move surfaces farther and can stretch newly revealed edges.')
        self.bands = Adjustment('Lens texture',100,tip='Fine view variation across the 112 lens bands. It changes edge detail, not a striped overlay. At low depth strength this is subtle; compare the enlarged crop. It does not brighten the material.')
        self.convergence = Adjustment('Stationary depth',50,tip='Depth map: the depth value that stays still. Layers: the share of movement assigned to the background.')
        for control in (self.strength,self.bands,self.convergence):
            effects.addWidget(control,1)
        self.strength.changed.connect(self.changed)
        self.convergence.changed.connect(self.changed)
        self.bands.changed.connect(self.lens_changed)
        self.invert = QCheckBox('Reverse depth')
        self.invert.toggled.connect(self.changed)
        effects.addWidget(self.invert)
        inspector_layout.addWidget(effectbox)
        inspector_layout.addWidget(self.placement)
        inspector_layout.addStretch()
        self.inspectors = QScrollArea()
        self.inspectors.setWidgetResizable(True)
        self.inspectors.setWidget(inspector_pane)
        self.inspectors.setMinimumWidth(310)
        splitter.addWidget(self.inspectors)
        splitter.setSizes([300,480,340])
        splitter.setStretchFactor(0,0)
        splitter.setStretchFactor(1,1)
        splitter.setStretchFactor(2,0)
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter,1)
        footer = QHBoxLayout()
        disclaimer = QLabel('<u>DISCLAIMER</u>')
        disclaimer.setToolTip("This tool is in beta, like genuinely.\nIf something breaks, we're sorry, make\na note of it and report it")
        footer.addWidget(disclaimer)
        self.status = QLabel('Choose artwork to begin.')
        self.status.setObjectName('muted')
        footer.addWidget(self.status,1)
        footer.addWidget(QLabel(self.quote))
        outer.addLayout(footer)
        for name,items in [('File',[('Open project…',self.open_project),('Save',self.save_project)]),('Deck',[('Add deck',self.add_deck),('Remove selected',lambda:self.remove_deck(self.selected))]),('View',[('Enlarge preview',self.enlarge)]),('Help',[('Guide',self.guide)])]:
            menu = self.menuBar().addMenu(name)
            for text,action in items:
                menu.addAction(text,action)

    def current(self):
        return self.decks[self.selected]

    def remember(self):
        if self.loading:
            return
        d = self.current()
        d.update(name=self.name.text(),author=self.author.text(),mode=list(MODES)[self.mode.currentIndex()],fit=self.fit.currentText(),background_fit=self.backfit.currentText(),
            depth=dict(strength=self.strength.value()/100,convergence=self.convergence.value()/100,bands=self.bands.value()/100,invert=self.invert.isChecked()),
            animation=dict(quality=(1,2,4)[self.quality.currentIndex()]),wood_tint=d.get('wood_colour',d.get('wood_tint') or '#b98a56') if self.wood_mode.currentIndex() else None,wood_intensity=self.intensity.value()/100)

    def workspace(self):
        self.remember()
        return copy.deepcopy(dict(version=5,selected=self.selected,decks=self.decks))

    def draw_tabs(self):
        self.tabs.blockSignals(True)
        while self.tabs.count():
            self.tabs.removeTab(0)
        for d in self.decks:
            self.tabs.addTab(d['name'] or 'Untitled deck')
        self.tabs.setCurrentIndex(self.selected)
        self.tabs.blockSignals(False)
        self.pack_button.setText(f'Export all ({len(self.decks)})')

    def apply_deck(self):
        self.loading = True
        d = self.current()
        self.name.setText(d['name'])
        self.author.setText(d.get('author',''))
        self.mode.setCurrentIndex(list(MODES).index(d['mode']))
        self.fit.setCurrentText(d.get('fit','Stretch'))
        self.backfit.setCurrentText(d.get('background_fit','Crop to fill'))
        self.quality.setCurrentIndex({1:0,2:1,4:2}.get(d.get('animation',{}).get('quality',2),1))
        settings = d.get('depth',{})
        for key,default in [('strength',.04),('convergence',.5),('bands',1)]:
            getattr(self,key).set_value(settings.get(key,default)*100)
        self.invert.setChecked(settings.get('invert',False))
        self.wood_mode.setCurrentIndex(1 if d.get('wood_tint') else 0)
        self.intensity.set_value(d.get('wood_intensity',1)*100)
        self.placement_open = False
        self.placement_index = None
        self.loading = False
        self.draw_tabs()
        self.update_mode()
        self.schedule(clear=True)
        self.wood_changed()

    def update_mode(self):
        mode = list(MODES)[self.mode.currentIndex()]
        names = {'classic':('Image A','Image B'),'depth':('Colour image','Depth map'),'layers':('Foreground (transparency supported)','Background'),'gif':('Animation','Unused')}[mode]
        for i,label in enumerate(self.image_labels):
            label.setText(names[i])
            self.image_names[i].setText(Path(self.current()['images'][i]).name if self.current()['images'][i] else '')
            for w in (label,self.image_names[i],self.image_buttons[i]):
                w.setVisible(i==0 or mode!='gif')
        for w in (self.auto_button,self.auto_help):
            w.setVisible(mode=='depth')
        self.quality.setVisible(mode=='gif')
        self.backfit.setVisible(mode=='layers')
        self.backfit_label.setVisible(mode=='layers')
        for w in (self.strength,self.bands,self.convergence,self.invert):
            w.setEnabled(mode in ('depth','layers') and not self.busy)
        self.convergence.title.setText('Background motion' if mode=='layers' else 'Stationary depth')
        self.swap_button.setEnabled(mode=='classic')
        self.detail_toggle.setEnabled(mode in ('depth','layers'))
        self.placement_choice.setEnabled(mode!='depth' and mode!='gif')
        if mode in ('depth','gif'):
            self.placement_choice.setCurrentIndex(0)

    def changed(self,*args):
        if self.loading or self.busy:
            return
        self.remember()
        self.schedule()

    def mode_changed(self,*args):
        if self.loading:
            return
        self.remember()
        self.update_mode()
        self.schedule(clear=True)

    def rename(self):
        self.remember()
        self.tabs.setTabText(self.selected,self.name.text() or 'Untitled deck')

    def add_deck(self):
        if self.busy:
            return
        self.remember()
        number = len(self.decks)+1
        while any(d['name']==f'My deck {number}' for d in self.decks):
            number += 1
        self.decks.append(default_deck(f'My deck {number}'))
        self.selected = len(self.decks)-1
        self.apply_deck()

    def select_deck(self,index):
        if index<0 or index==self.selected or self.loading:
            return
        if self.busy:
            self.draw_tabs()
            return
        self.remember()
        self.selected = index
        self.apply_deck()

    def remove_deck(self,index):
        if self.busy or len(self.decks)==1:
            return
        if QMessageBox.question(self,'Remove deck','Remove this deck from the workspace? Source images will be kept.')!=QMessageBox.Yes:
            return
        self.remember()
        del self.decks[index]
        self.selected = min(self.selected,len(self.decks)-1)
        self.apply_deck()

    def choose(self,index):
        path,_ = QFileDialog.getOpenFileName(self,'Choose image','','Images (*.gif *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)')
        if path:
            self.current()['images'][index] = path
            self.update_mode()
            self.schedule()

    def swap(self):
        self.current()['images'].reverse()
        self.current()['placement'].reverse()
        self.update_mode()
        self.schedule()

    def schedule(self,clear=False):
        self.revision += 1
        self.pending = None
        self.gif_cache.clear()
        self.last_key = None
        if clear:
            self.last_detail_key = None
            self.live_placement = False
            self.placement_sources = self.placement_source_key = None
            self.renderer = self.detail_renderer = self.clip = None
            self.lens_source_key = self.clip_path = None
            self.display_revision = -1
            self.board.frame = None
            self.board.update()
            self.thumb.clear()
            for _,image in self.detail_images:
                image.setPixmap(None)
            if self.large:
                self.large_board.frame = None
                self.large_board.update()
        self.update_inspectors()
        self.status.setText('Updating preview…' if self.board.frame is not None else 'Preparing preview…')
        self.preview_timer.start()

    def prepare(self):
        if self.live_placement and any(control.slider.isSliderDown() for control in self.positions.values()):
            self.preview_timer.start(100)
            return
        self.remember()
        d = copy.deepcopy(self.current())
        if not d['images'][0] or (d['mode']!='gif' and not all(d['images'])):
            self.status.setText('Choose the images for this effect.')
            self.make_thumbnail()
            return
        self.pending = (self.revision,d)
        self.start_worker()

    def start_worker(self):
        if self.worker or self.pending is None:
            return
        revision,d = self.pending
        self.pending = None
        self.worker = True
        cached_sources = self.placement_sources if tuple(d['images'])==self.placement_source_key else None
        def run():
            try:
                settings = d.get('depth',{})
                if d['mode']=='gif':
                    clip = animation.load(d['images'][0])
                    still = animation_texture.preview_frame(clip,0,d['background'],d['placement'][0])
                    result = (None,None,clip,[still,still],None)
                else:
                    sources = cached_sources
                    if sources is None:
                        sources = []
                        for path in d['images']:
                            with Image.open(path) as source:
                                source = ImageOps.exif_transpose(source).convert('RGBA')
                                source.thumbnail((1024,4096),Image.Resampling.LANCZOS)
                                sources.append(source)
                    images = [image_placement.frame(source,d['background_fit'] if d['mode']=='layers' and i==1 else d['fit'],d['background'],d['placement'][i],alpha=d['mode']=='layers' and i==0,depth=d['mode']=='depth' and i==1) for i,source in enumerate(sources)]
                    if d['mode']=='depth' and settings.get('invert'):
                        images[1] = ImageOps.invert(images[1].convert('RGB'))
                    strength,convergence,bands = (settings.get(k,v) for k,v in [('strength',.04),('convergence',.5),('bands',1)])
                    def progress(message):
                        if revision!=self.revision:
                            raise InterruptedError()
                    if d['mode']=='depth':
                        views = preview_depth.views(*images,strength,convergence,progress)
                        atlas = engine.depth_views.pack(views,bands,balanced=True)
                        thumbs = [views[0],views[-1]]
                    elif d['mode']=='layers':
                        atlas = engine.layer_atlas.pack(*images,strength,convergence,bands,settings.get('invert',False))
                        thumbs = images
                    else:
                        atlas = engine.atlas(*images)
                        thumbs = images
                    progress('')
                    renderer = AtlasPreview(atlas,d['mode'])
                    detail = copy.copy(renderer)
                    detail.settings = detail.settings.copy()
                    result = (renderer,detail,None,thumbs,sources)
                self.events.put(('preview',revision,result))
            except InterruptedError:
                self.events.put(('preview',revision,None))
            except Exception as exc:
                self.events.put(('preview_error',revision,str(exc)))
        threading.Thread(target=run,daemon=True).start()

    def poll(self):
        while not self.events.empty():
            kind,revision,result = self.events.get()
            if kind in ('preview','preview_error'):
                self.worker = False
                if revision==self.revision:
                    if kind=='preview_error':
                        self.status.setText('Preview: '+result)
                    elif result:
                        keep_clock = self.clip is not None and result[2] is not None and self.clip_path==self.current()['images'][0]
                        self.renderer,self.detail_renderer,self.clip,self.thumbnail_sources,self.placement_sources = result
                        self.placement_source_key = tuple(self.current()['images'])
                        self.live_placement = False
                        self.display_revision = revision
                        self.gif_cache.clear()
                        # Lens changes made while the worker ran must win over its snapshot.
                        if self.renderer:
                            self.renderer.set_lens_strength(self.bands.value()/100)
                        source_key = (self.current()['mode'],tuple(self.current()['images']))
                        if self.detail_renderer and self.current()['mode'] in ('depth','layers') and source_key!=self.lens_source_key:
                            self.find_lens_detail()
                            self.lens_source_key = source_key
                        if not keep_clock:
                            self.started = time.monotonic()
                        self.clip_path = self.current()['images'][0] if self.clip else None
                        self.status.setText('Ready · preview before game lighting')
                        self.last_key = None
                        self.render()
                        self.make_thumbnail()
                self.start_worker()
            elif kind=='update':
                if result:
                    self.release = result
                    self.update_button.show()
            elif kind=='status':
                self.status.setText(result)
            elif kind in ('export','error'):
                self.set_busy(False)
                if kind=='export':
                    self.status.setText('Saved: '+result)
                    QMessageBox.information(self,'Export complete','Saved your FBMOD. Import it in ReSkate Studio to install it.\n\n'+result)
                else:
                    QMessageBox.critical(self,'Operation failed',result)
            elif kind=='depth':
                self.set_busy(False)
                if revision==self.selected:
                    self.current()['images'][1] = result
                    self.current()['placement'][1] = copy.deepcopy(self.current()['placement'][0])
                    self.update_mode()
                    self.schedule()

    def render_reset(self,*args):
        self.last_key = None
        self.render()

    def find_lens_detail(self):
        # The centre can sit exactly on stationary depth, hiding the entire effect.
        sample = self.detail_renderer
        sample.set_lens_strength(0)
        a = np.asarray(sample.render(self.angle.value()/100,(120,480)),dtype=np.int16)
        sample.set_lens_strength(1)
        b = np.asarray(sample.render(self.angle.value()/100,(120,480)),dtype=np.int16)
        difference = np.abs(a-b).sum(axis=2)
        best = (-1,.5,.5)
        for x in (.2,.35,.5,.65,.8):
            lo,hi = int((x-.125)*120),int((x+.125)*120)
            rows = difference[:,lo:hi].sum(axis=1)
            scores = np.convolve(rows,np.ones(30),mode='valid')
            y = int(np.argmax(scores))
            candidate = (float(scores[y]),x,(y+15)/480)
            if candidate[0]>best[0]:
                best = candidate
        _,x,y = best
        self.lens_region = (x-.125,max(0,y-.05),x+.125,min(1,y+.05))

    def lens_changed(self,*args):
        if self.loading:
            return
        self.remember()
        if self.renderer:
            self.renderer.set_lens_strength(self.bands.value()/100)
        self.render_reset()

    def render(self):
        mode = self.current()['mode']
        angle,bands = self.angle.value()/100,self.bands.value()/100
        gif_index = self.clip.frame_index(((time.monotonic()-self.started)*1000)%self.clip.duration_ms) if self.clip else None
        size = (180,720) if not self.large else (320,1280)
        key = (self.revision,angle,bands,self.detail_toggle.isChecked(),gif_index,size,self.live_placement)
        if self.last_key==key:
            return
        if self.clip:
            if gif_index not in self.gif_cache:
                d = self.current()
                self.gif_cache[gif_index] = animation_texture.preview_frame(self.clip,gif_index,d['background'],d['placement'][0])
                while len(self.gif_cache)>4:
                    self.gif_cache.pop(next(iter(self.gif_cache)))
            image = self.gif_cache[gif_index]
        elif self.live_placement and self.placement_sources is not None:
            image = self.placement_frame(size)
        elif self.renderer:
            image = self.renderer.render(angle,size)
        else:
            return
        self.last_key = key
        self.preview_title.setText('Deck preview · positioning' if self.live_placement and not self.clip else 'Deck preview')
        pixmap = QPixmap.fromImage(qt_image(image))
        self.board.frame = pixmap
        self.board.update()
        if self.large:
            self.large_board.frame = pixmap
            self.large_board.update()
        show = mode in ('depth','layers') and self.detail_toggle.isChecked() and self.detail_renderer is not None
        self.update_inspectors()
        detail_key = (id(self.detail_renderer),angle,bands,getattr(self,'lens_region',None))
        if show and detail_key!=self.last_detail_key:
            self.last_detail_key = detail_key
            self.detail_images[1][0].setText(f'Lens texture {bands*100:.0f}%')
            for (_,label),strength in zip(self.detail_images,(0,bands)):
                self.detail_renderer.set_lens_strength(strength)
                crop = self.detail_renderer.render(angle,(240,96),self.lens_region)
                label.setPixmap(QPixmap.fromImage(qt_image(crop)))

    def guides_changed(self,value):
        self.board.guides = value
        self.board.update()
        if self.large:
            self.large_board.guides = value
            self.large_board.update()

    def wood_changed(self,*args):
        if self.loading:
            return
        self.remember()
        d = self.current()
        colour = QColor(d.get('wood_tint') or '#9a7855')
        if d.get('wood_tint'):
            intensity = d.get('wood_intensity',1)
            colour = QColor(*[min(255,round(c*intensity)) for c in (colour.red(),colour.green(),colour.blue())])
        self.board.wood = colour.name()
        self.board.update()
        if self.large:
            self.large_board.wood = colour.name()
            self.large_board.update()

    def wood_colour(self):
        colour = QColorDialog.getColor(QColor(self.current().get('wood_tint') or '#b98a56'),self,'Wood colour')
        if colour.isValid():
            self.current()['wood_colour'] = colour.name()
            self.wood_mode.setCurrentIndex(1)
            self.wood_changed()

    def padding_colour(self):
        colour = QColorDialog.getColor(QColor(self.current()['background']),self,'Padding colour')
        if colour.isValid():
            self.current()['background'] = colour.name()
            self.schedule()

    def make_thumbnail(self):
        d = self.current()
        custom = d.get('thumbnail')
        self.thumb_name.setText(Path(custom).name if custom else 'Automatic · transparent background + '+('ANIMATED' if d['mode']=='gif' else 'LENTICULAR'))
        try:
            sources = self.thumbnail_sources if self.renderer or self.clip else [None,None]
            if custom or all(x is not None for x in sources):
                image = engine.thumbnail(*sources,custom,size=64,label='ANIMATED' if d['mode']=='gif' else 'LENTICULAR')
                self.thumb.setPixmap(QPixmap.fromImage(qt_image(image)))
            else:
                self.thumb.clear()
        except Exception as exc:
            self.status.setText('Thumbnail: '+str(exc))

    def choose_thumbnail(self):
        path,_ = QFileDialog.getOpenFileName(self,'Choose thumbnail','','Images (*.png *.jpg *.jpeg *.webp *.gif)')
        if path:
            try:
                with Image.open(path) as image:
                    image.verify()
                self.current()['thumbnail'] = path
                self.make_thumbnail()
            except Exception as exc:
                QMessageBox.warning(self,'Thumbnail',str(exc))

    def reset_thumbnail(self):
        self.current()['thumbnail'] = None
        self.make_thumbnail()

    def adjust_image(self):
        self.placement_open = True
        self.update_inspectors()
        self.inspectors.ensureWidgetVisible(self.placement)
        self.choose_placement(self.placement_choice.currentIndex())

    def close_placement(self):
        self.placement_open = False
        self.update_inspectors()

    def update_inspectors(self):
        lens = self.current()['mode'] in ('depth','layers') and self.detail_toggle.isChecked()
        self.detail_box.setVisible(lens)
        self.placement.setVisible(self.placement_open)

    def choose_placement(self,index):
        self.placement_index = index
        was_loading = self.loading
        self.loading = True
        for key,control in self.positions.items():
            control.set_value(self.current()['placement'][index].get(key,1 if key=='zoom' else 0)*100)
        self.loading = was_loading
        if not was_loading and self.current()['mode']=='classic':
            self.angle.spin.setValue(100 if index==0 else -100)

    def move_image(self,*args):
        if self.loading or self.placement_index is None:
            return
        setting = {key:control.value()/100 for key,control in self.positions.items()}
        d = self.current()
        d['placement'][self.placement_index] = setting
        if d['mode']=='depth':
            d['placement'][1-self.placement_index] = copy.deepcopy(setting)
        self.schedule()
        self.live_placement = self.clip is not None or self.placement_source_key==tuple(d['images'])
        self.status.setText('Positioning artwork · effect refreshes after release')
        self.render_reset()

    def finish_placement(self):
        if self.live_placement:
            self.preview_timer.start(0)

    def placement_frame(self,size):
        width = min(size[0],144)
        return live_placement.render(self.placement_sources,self.current(),self.angle.value()/100,(width,width*4))

    def reset_placement(self):
        if self.placement_index is not None:
            for key,control in self.positions.items():
                control.set_value(100 if key=='zoom' else 0)
            self.move_image()

    def enlarge(self):
        if self.large:
            self.large.raise_()
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('Deck preview')
        dialog.resize(620,920)
        layout = QVBoxLayout(dialog)
        self.large_board = Board()
        self.large_board.guides = self.guides.isChecked()
        self.large_board.wood = self.board.wood
        layout.addWidget(self.large_board,1)
        angle = Adjustment('Viewing angle',self.angle.value(),-100,100)
        angle.changed.connect(lambda value:self.angle.spin.setValue(value))
        self.angle.changed.connect(angle.set_value)
        layout.addWidget(angle)
        layout.addWidget(QLabel('Note: may not reflect 1:1 in game'))
        self.large = dialog
        dialog.finished.connect(self.close_enlarged)
        dialog.show()
        self.render_reset()

    def close_enlarged(self):
        self.large = None
        self.render_reset()

    def load_study(self):
        from auto_depth import DATA
        paths = engine.depth_views.depth_study(DATA/'demo')
        self.remember()
        self.current().update(mode='depth',name='3D Lens Study',images=list(map(str,paths)),depth=dict(strength=.16,convergence=.5,bands=1,invert=False))
        self.apply_deck()


def application():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle('Fusion')
    palette = QPalette()
    for role,colour in dict(Window='#24272b',WindowText='#e4e7eb',Base='#1d2024',AlternateBase='#292e33',Text='#e4e7eb',Button='#30353b',ButtonText='#e4e7eb',Highlight='#387998',HighlightedText='#ffffff',ToolTipBase='#30353b',ToolTipText='#ffffff').items():
        palette.setColor(getattr(QPalette.ColorRole,role),QColor(colour))
    palette.setColor(QPalette.Disabled,QPalette.Text,QColor('#7d858d'))
    palette.setColor(QPalette.Disabled,QPalette.WindowText,QColor('#7d858d'))
    app.setPalette(palette)
    for name in ('segoeui.ttf','seguisb.ttf'):
        path = Path('C:/Windows/Fonts')/name
        if path.is_file():
            QFontDatabase.addApplicationFont(str(path))
    app.setFont(QFont('Segoe UI',9))
    app.setWindowIcon(QIcon(str(ROOT/'assets/app-icon.ico')))
    return app


def shader_warning(parent):
    from first_run import WARNING
    marker = Path(os.environ.get('LOCALAPPDATA',Path.home()))/'Lenticular Deck Creator'/'shader-support-acknowledged.json'
    try:
        if json.loads(marker.read_text(encoding='utf8')).get('acknowledged') is True:
            return True
    except (OSError,ValueError,AttributeError):
        pass
    dialog = QDialog(parent)
    dialog.setWindowTitle('Shader support required')
    layout = QVBoxLayout(dialog)
    label = QLabel(WARNING)
    label.setAlignment(Qt.AlignCenter)
    label.setWordWrap(True)
    label.setMinimumWidth(560)
    layout.addWidget(label)
    button('Got it, chief',dialog.accept,layout)
    if dialog.exec()!=QDialog.Accepted:
        return False
    try:
        marker.parent.mkdir(parents=True,exist_ok=True)
        marker.write_text(json.dumps({'acknowledged':True}),encoding='utf8')
        return True
    except OSError as exc:
        QMessageBox.critical(parent,'Cannot save acknowledgement',str(exc))
        return False


def main():
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ReSkate.DeckTool.Beta')
    app = application()
    window = Creator()
    if shader_warning(window):
        window.show()
        app.exec()
