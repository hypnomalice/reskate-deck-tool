import copy
import json
import math
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
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal, QSettings
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPalette, QImage
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QPushButton, QToolButton, QLineEdit, QComboBox, QSlider,
    QDoubleSpinBox, QAbstractSpinBox, QCheckBox, QGroupBox, QScrollArea, QSplitter,
    QListWidget, QTabBar, QInputDialog, QFileDialog, QColorDialog, QMessageBox, QDialog, QTextBrowser, QTabWidget)

import creator_engine as engine
import animation
import animation_texture
import image_placement
import preview_depth
import live_placement
import board_preview
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
QPushButton:checked { background:#356b86; border-color:#8cb5ca; }
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
    orbit_changed = Signal(float, float, bool)
    def __init__(self):
        super().__init__()
        self.frame = None
        self.wood = '#9a7855'
        self.guides = True
        self.view_mode = '2D'
        self.yaw, self.pitch = 0., 0.
        self.drag_position = None
        self.setMinimumSize(250,180)

    def mousePressEvent(self,event):
        if self.view_mode=='3D' and event.button()==Qt.LeftButton:
            self.drag_position=event.position()
            event.accept()

    def mouseMoveEvent(self,event):
        if self.drag_position is not None:
            delta=event.position()-self.drag_position
            self.drag_position=event.position()
            self.yaw=max(-70.,min(70.,self.yaw+delta.x()*.4))
            self.pitch=max(-65.,min(65.,self.pitch+delta.y()*.3))
            self.orbit_changed.emit(self.yaw,self.pitch,True)
            self.update()

    def mouseReleaseEvent(self,event):
        was_dragging = self.drag_position is not None
        self.drag_position=None
        if was_dragging:
            self.orbit_changed.emit(self.yaw,self.pitch,False)

    def mouseDoubleClickEvent(self,event):
        self.yaw,self.pitch=0.,0.
        self.orbit_changed.emit(self.yaw,self.pitch,False)
        self.update()

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(),QColor('#191c20'))
        if self.view_mode=='3D' and self.frame is not None:
            from board_view import draw_3d
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            draw_3d(painter,self)
            return
        h = min(self.height()-30,(self.width()-45)*board_preview.DECK_LENGTH)
        w = h/board_preview.DECK_LENGTH
        area = QRectF((self.width()-w)/2,(self.height()-h)/2,w,h)
        path = QPainterPath()
        steps=[.5-.5*math.cos(math.pi*j/80) for j in range(81)]
        outline=[(0,v) for v in steps]+[(1,v) for v in reversed(steps)]
        for i,(u,v) in enumerate(outline):
            x,_,_=board_preview.surface(u,v)
            point=QPointF(area.left()+(x+.5)*w,area.top()+v*h)
            if i==0:path.moveTo(point)
            else:path.lineTo(point)
        path.closeSubpath()
        painter.setPen(QPen(QColor(self.wood),2))
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
            for axle,centre in zip(board_preview.TRUCK_CENTRES,board_preview.PLATE_CENTRES):
                y = area.top()+h*centre
                painter.drawRoundedRect(QRectF(area.left()+w*(.5-board_preview.PLATE_WIDTH/2),y-h*board_preview.PLATE_LENGTH/2,w*board_preview.PLATE_WIDTH,h*board_preview.PLATE_LENGTH),3,3)
                painter.drawLine(round(area.left()+w*.04),round(area.top()+h*axle),round(area.right()-w*.04),round(area.top()+h*axle))
                for x in (.5-board_preview.BOLT_HALF_WIDTH,.5+board_preview.BOLT_HALF_WIDTH):
                    for offset in (-board_preview.BOLT_HALF_LENGTH,board_preview.BOLT_HALF_LENGTH):
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


def default_deck(name='My Deck'):
    return dict(version=7,name=name,mode='gif',lenticular=False,author='',images=[None,None],fit='Stretch',
        extra_images=[],ghost={kind:dict(selection='all',mask=None,colour='#ffffff',tolerance=.15) for kind in ('silver','holo')},neon=dict(selection='mask',colour='#00dfff',tolerance=.15,brightness=1),middle_image=None,middle_placement=dict(zoom=1,x=0,y=0),layer_depths=[.1,.45,.9],
        background_fit='Crop to fill',background='#ffffff',thumbnail=None,
        placement=[dict(zoom=1,x=0,y=0),dict(zoom=1,x=0,y=0)],
        depth=dict(strength=.04,convergence=.5,bands=1,invert=False),
        liquid=dict(colour='#9630d8',cloudiness=.15,depth=.09,amount=.5),
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
        self.clip_source_key = None
        self.placement_sources = None
        self.placement_source_key = None
        self.live_placement = False
        self.last_detail_key = None
        self.pending = None
        self.frame_worker = False
        self.orbit_dragging = self.camera_sync = self.texture_worker = False
        self.export_renderer = self.export_renderer_key = None
        self.frame_renderer = self.frame_renderer_key = self.frame_request_key = None
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
            deck['lenticular']=source.get('lenticular',True)
            if deck['mode'] not in MODES or len(deck['images'])!=2:
                raise ValueError('Invalid deck settings.')
            deck['images'] = [str((Path(path).parent/p).resolve()) if p else None for p in deck['images']]
            deck['extra_images']=[str((Path(path).parent/p).resolve()) for p in deck.get('extra_images',[])]
            if len(deck['extra_images'])>6:raise ValueError('Lenticular supports up to eight pictures.')
            if deck.get('middle_image'):
                deck['middle_image']=str((Path(path).parent/deck['middle_image']).resolve())
            if deck.get('thumbnail'):
                deck['thumbnail'] = str((Path(path).parent/deck['thumbnail']).resolve())
            for cfg in deck.get('ghost',{}).values():
                if cfg.get('mask'):cfg['mask']=str((Path(path).parent/cfg['mask']).resolve())
            normalized.append(deck)
        self.decks = normalized
        self.selected = max(0,min(data.get('selected',0),len(decks)-1))
        self.path = Path(path)
        self.project_title.setText(self.path.stem)
        self.apply_deck()
        self.baseline = self.workspace()

    def set_busy(self,busy):
        self.busy = busy
        for widget in (self.settings,self.tabs,self.add_button,self.export_button,self.pack_button,self.export_mode,self.export_change,self.strength,self.bands,self.convergence,self.invert,self.placement,self.ghost_box,*self.layer_depth_controls):
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
                if not d['images'][0] or (d['mode'] not in ('gif','metal') and not (d['mode']=='neon' and d.get('neon',{}).get('selection')=='colour') and not all(d['images'])):
                    raise ValueError('Choose the images for '+d['name']+'.')
            if len({engine.validate_name(d['name']).casefold() for d in projects})!=len(projects):
                raise ValueError('Give each deck a different name.')
        except ValueError as exc:
            QMessageBox.warning(self,'Check the decks',str(exc))
            return
        title = (self.path.stem if self.path else 'Deck Pack') if all_decks else projects[0]['name']
        mode = self.export_mode.currentData()
        folder_export = mode == 'game'
        native = mode != 'fbmod'
        if folder_export:
            folder_name,accepted = QInputDialog.getText(self,'Name your deck pack','Folder name in Mods:',text=title)
            if not accepted:
                return
            if not folder_name.strip():
                QMessageBox.warning(self,'Name your deck pack','Enter a folder name before installing.')
                return
            title = folder_name.strip()
        native_options = None
        if native:
            native_options = self.native_export_options()
            if native_options is None:
                return
            self.update_export_controls()
        if folder_export:
            import native_export
            path = str(Path(native_options['game_root'])/'Mods'/native_export.mod_name(title))
            try:
                native_export.check_folder(path)
            except ValueError as error:
                QMessageBox.warning(self,'Cannot replace this deck pack',str(error))
                return
        else:
            suffix = '.zip' if mode == 'zip' else '.fbmod'
            file_filter = 'Mod ZIP (*.zip)' if mode == 'zip' else 'FBMOD for Studio (*.fbmod)'
            path,_ = QFileDialog.getSaveFileName(self,'Export deck pack',title+suffix,file_filter)
            if not path:
                return
            if not Path(path).suffix:
                path += suffix
        self.set_busy(True)
        self.status.setText('Preparing export…')
        def run():
            try:
                progress = lambda message:self.events.put(('status',0,message))
                if native:
                    import native_export
                    exporter = native_export.export_folder if folder_export else native_export.export_zip
                    result = exporter(projects,path,progress,title=Path(path).name if folder_export else Path(path).stem,author=projects[0].get('author',''),**native_options)
                else:
                    result = engine.export_pack(projects,path,progress,title=title,author=projects[0].get('author',''),shared_runtime=True)
                self.events.put(('export',0,str(result)))
            except Exception as exc:
                self.events.put(('error',0,str(exc)))
        threading.Thread(target=run,daemon=True).start()

    def export_mode_changed(self):
        QSettings('hypnomalice','ReSkate Deck Tool').setValue('export/mode',self.export_mode.currentData())
        self.update_export_controls()

    def update_export_controls(self):
        mode = self.export_mode.currentData()
        self.export_button.setText({'zip':'Export ZIP','game':'Install deck','fbmod':'Export FBMOD'}[mode])
        self.pack_button.setText(('Install all' if mode=='game' else 'Export all')+f' ({len(self.decks)})')
        self.export_hint.setText({'zip':'Ready to install or share.','game':'Close the game and launcher before installing.','fbmod':'For editing in Studio.'}[mode])
        game = str(QSettings('hypnomalice','ReSkate Deck Tool').value('native/game',''))
        self.export_destination.setText(str(Path(game)/'Mods') if game else 'Choose your game folder on first install.')
        self.export_destination_row.setVisible(mode=='game')

    def change_export_game(self):
        self.native_export_options(True)
        self.update_export_controls()

    def native_export_options(self, force=False):
        import native_export
        preferences = QSettings('hypnomalice','ReSkate Deck Tool')
        game = str(preferences.value('native/game',''))
        compiler = str(preferences.value('native/compiler',''))
        if force or not (Path(game)/'Skate.exe').is_file() or not (Path(game)/'Data/layout.toc').is_file():
            QMessageBox.information(self,'Native mod export',
                'This exports compiled mod files directly, without opening Studio. Select your Skate folder and the reskate_cli.exe from your shader-capable Studio installation once. The compiler is still required; it is not bundled or downloaded.')
            game = QFileDialog.getExistingDirectory(self,'Choose your Skate game folder',game)
            if not game:
                return None
        if force or not Path(compiler).is_file():
            candidates = [Path(game)/folder/'reskate_cli.exe' for folder in ('Studio','Studio with Shaders')]
            compiler = '' if force else str(next((p for p in candidates if p.is_file()),''))
            if not compiler:
                compiler,_ = QFileDialog.getOpenFileName(self,'Choose Studio reskate_cli.exe',filter='Studio compiler (reskate_cli.exe)')
            if not compiler:
                return None
        try:
            native_export.validate_inputs(game,compiler)
        except ValueError as error:
            QMessageBox.warning(self,'Native export setup',str(error))
            return None
        preferences.setValue('native/game',game)
        preferences.setValue('native/compiler',compiler)
        return dict(game_root=game,compiler=compiler)

    def update_fbmods(self):
        if self.busy:
            return
        paths,_ = QFileDialog.getOpenFileNames(self,'Convert older packs for SDEC',filter='ReSkate mod (*.fbmod)')
        if not paths:
            return
        folder = QFileDialog.getExistingDirectory(self,'Save SDEC content copies in…')
        if not folder:
            return
        self.set_busy(True)
        self.status.setText('Converting packs for SDEC…')
        def run():
            from effects_runtime import write_content_export
            saved,failed = [],[]
            for path in paths:
                destination = Path(folder)/(Path(path).stem+' - SDEC.fbmod')
                self.events.put(('status',0,'Updating '+Path(path).name+'…'))
                try:
                    if destination.resolve()==Path(path).resolve():
                        raise ValueError('Choose a separate destination for the migrated copy.')
                    decks = write_content_export(Path(path).read_bytes(),destination)['decks']
                    saved.append(str(destination)+f' ({decks} decks)')
                except Exception as exc:
                    failed.append(Path(path).name+': '+str(exc))
            self.events.put(('compatibility',0,(saved,failed)))
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
        if not self.release or self.busy:
            return
        if not getattr(sys,'frozen',False) or not self.release.download_url:
            __import__('webbrowser').open(self.release.url)
            return
        if not self.discard():
            return
        self.set_busy(True)
        self.update_button.setEnabled(False)
        self.update_button.setText('Downloading update…')
        release=self.release
        def run():
            import tempfile
            from updates import download_update
            try:
                folder=tempfile.mkdtemp(prefix='reskate-update-')
                download=download_update(release,folder,lambda done,total:self.events.put(('update_progress',0,round(done*100/total))))
                self.events.put(('update_ready',0,(download,release.sha256)))
            except Exception as exc:
                self.events.put(('update_failed',0,str(exc)))
        threading.Thread(target=run,daemon=True).start()

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
        outer.addLayout(toolbar)
        export_row = QHBoxLayout()
        export_row.addWidget(QLabel('Export as'))
        self.export_mode = QComboBox()
        for label,key in [('Mod ZIP','zip'),('Install to game','game'),('FBMOD','fbmod')]:
            self.export_mode.addItem(label,key)
        preferences = QSettings('hypnomalice','ReSkate Deck Tool')
        self.export_mode.setCurrentIndex(max(0,self.export_mode.findData(preferences.value('export/mode','zip'))))
        self.export_mode.currentIndexChanged.connect(self.export_mode_changed)
        export_row.addWidget(self.export_mode)
        self.export_hint = QLabel()
        export_row.addWidget(self.export_hint,1)
        self.export_button = button('Export ZIP',lambda:self.export(False),export_row)
        self.pack_button = button('Export all',lambda:self.export(True),export_row)
        self.pack_button.setObjectName('primary')
        outer.addLayout(export_row)
        self.export_destination_row = QWidget()
        destination_layout = QHBoxLayout(self.export_destination_row)
        destination_layout.setContentsMargins(0,0,0,0)
        self.export_destination = QLabel()
        self.export_destination.setWordWrap(True)
        destination_layout.addWidget(self.export_destination,1)
        self.export_change = button('Change…',self.change_export_game,destination_layout)
        outer.addWidget(self.export_destination_row)
        self.update_export_controls()
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
        help_button('Animated / GIF plays an animation.\nLenticular transitions between two to eight ordered pictures with lens bands. Neon uses a mask PNG or a picked colour.\nDepth Map and Foreground / Background move smoothly unless Enable lenticular is selected.\nGhost Rare combines smooth depth, silver shading and depth-guided holographic sheen.',effect)
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
        self.multi_panel=QGroupBox('Lenticular pictures · 2–8')
        multi=QVBoxLayout(self.multi_panel)
        self.picture_list=QListWidget();self.picture_list.setMaximumHeight(145);multi.addWidget(self.picture_list)
        row=QHBoxLayout();button('Choose pictures…',self.choose_pictures,row);multi.addLayout(row)
        row=QHBoxLayout();button('Move up',lambda:self.move_picture(-1),row);button('Move down',lambda:self.move_picture(1),row);button('Remove',self.remove_picture,row);multi.addLayout(row)
        images.addWidget(self.multi_panel)
        self.middle_panel=QWidget()
        middle_layout=QVBoxLayout(self.middle_panel);middle_layout.setContentsMargins(0,0,0,0)
        self.middle_label=QLabel('Middle layer (optional · transparency supported)');self.middle_label.setWordWrap(True);middle_layout.addWidget(self.middle_label)
        middle_row=QHBoxLayout();self.middle_name=QLineEdit();self.middle_name.setReadOnly(True);self.middle_name.setMinimumWidth(40)
        self.middle_name.setPlaceholderText('Add a third image for independent parallax')
        middle_row.addWidget(self.middle_name,1)
        button('Browse…',self.choose_middle,middle_row);button('Clear',self.clear_middle,middle_row)
        middle_layout.addLayout(middle_row);images.insertWidget(2,self.middle_panel)
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
        self.view_mode = QComboBox()
        self.view_mode.addItems(['2D','3D'])
        self.view_mode.setToolTip('Both views use the standard deck artwork mapping. 3D is a procedural shape preview, not game lighting. Drag to orbit and change the effect together; double-click to reset.')
        self.view_mode.currentTextChanged.connect(self.preview_view_changed)
        row.addWidget(self.view_mode)
        self.export_preview = QPushButton('Export texture')
        self.export_preview.setCheckable(True)
        self.export_preview.setToolTip('Prepare the actual exported BC7 texture in the background. Includes export placement and depth views. Static decks only; lighting and shape remain approximate. Editing returns to fast preview.')
        self.export_preview.toggled.connect(self.export_texture_checked)
        row.addWidget(self.export_preview)
        button('Enlarge…',self.enlarge,row)
        right.addLayout(row)
        row = QHBoxLayout()
        self.guides = QCheckBox('Truck guides')
        self.guides.setChecked(True)
        self.guides.toggled.connect(self.guides_changed)
        row.addWidget(self.guides)
        self.studio_light = QCheckBox('Game room light')
        self.studio_light.setChecked(True)
        self.studio_light.setEnabled(True)
        self.studio_light.setToolTip('Colour and light calibrated from the supplied native menu captures. Different maps, HDR settings and effect materials can differ. 2D uses face-on menu light; 3D follows the orbit. Turn off to inspect unlit artwork.')
        self.studio_light.toggled.connect(self.render_reset)
        row.addWidget(self.studio_light)
        self.detail_toggle = QCheckBox('Lens detail')
        self.detail_toggle.setChecked(True)
        self.detail_toggle.toggled.connect(self.render_reset)
        row.addWidget(self.detail_toggle)
        row.addStretch()
        right.addLayout(row)
        self.board = Board()
        self.board.orbit_changed.connect(self.preview_orbit_changed)
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
        self.angle.changed.connect(self.preview_angle_changed)
        right.addWidget(self.angle)
        note = QLabel('Fast texture preview · game lighting and shape are approximate')
        self.preview_note = note
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
        self.layer_depth_controls=[]
        for title,value in [('Foreground depth',10),('Middle depth',45),('Background depth',90)]:
            control=Adjustment(title,value,0,100,tip='0 is nearest; 100 is farthest. Each image moves at its own depth. 50 is the stationary plane.')
            control.changed.connect(self.changed);effects.addWidget(control)
            self.layer_depth_controls.append(control)
        self.strength.changed.connect(self.changed)
        self.convergence.changed.connect(self.changed)
        self.bands.changed.connect(self.lens_changed)
        self.invert = QCheckBox('Reverse depth')
        self.lenticular = QCheckBox('Enable lenticular')
        self.lenticular.toggled.connect(self.changed)
        lensrow=QHBoxLayout()
        lensrow.addWidget(self.lenticular)
        self.lenticular_help=help_button('Adds lens banding and stepped transitions as the deck tilts. Leave off for smooth depth movement.',lensrow)
        effects.addLayout(lensrow)
        self.invert.toggled.connect(self.changed)
        effects.addWidget(self.invert)
        self.neon_method=QComboBox();self.neon_method.addItems(['Mask PNG','Pick a colour'])
        self.neon_method.currentIndexChanged.connect(self.changed);effects.addWidget(self.neon_method)
        self.neon_colour=button('Choose glow colour…',self.choose_neon_colour,effects)
        self.neon_tolerance=Adjustment('Colour tolerance',15,0,100,tip='Include colours close to the selected glow colour.')
        self.neon_brightness=Adjustment('Neon brightness',100,0,100,tip='100% matches the approved Neon C test. Black areas of the mask never glow.')
        for control in (self.neon_tolerance,self.neon_brightness):effects.addWidget(control);control.changed.connect(self.changed)
        self.ghost_box=QGroupBox('Ghost Rare finish areas')
        ghost_form=QFormLayout(self.ghost_box);self.ghost_area_controls={}
        for kind,title in (('silver','Silver'),('holo','Holo')):
            method=QComboBox();method.addItems(['Whole board','Mask PNG','Pick a colour'])
            method.currentIndexChanged.connect(self.changed);ghost_form.addRow(title+' area',method)
            mask_button=QPushButton('Choose '+kind+' mask...');mask_button.clicked.connect(lambda checked=False,k=kind:self.choose_ghost_mask(k));ghost_form.addRow('',mask_button)
            mask_name=QLabel();mask_name.setWordWrap(True);ghost_form.addRow('',mask_name)
            colour_button=QPushButton('Choose artwork colour...');colour_button.clicked.connect(lambda checked=False,k=kind:self.choose_ghost_colour(k));ghost_form.addRow('',colour_button)
            tolerance=Adjustment('Colour tolerance',15,0,100,tip='Include artwork colours near the selected colour.');tolerance.changed.connect(self.changed);ghost_form.addRow('',tolerance)
            self.ghost_area_controls[kind]=(method,mask_button,mask_name,colour_button,tolerance)
        ghost_help=QLabel('White mask areas receive the finish; black stays as artwork. Grey softens it. Silver and holo are independent. Requires SDEC core 1.3.0 from Thunderstore.')
        ghost_help.setWordWrap(True);ghost_help.setMinimumHeight(100);ghost_form.addRow(ghost_help);effects.addWidget(self.ghost_box)
        self.liquid_colour=button('Liquid colour…',self.choose_liquid_colour,effects)
        self.liquid_cloud=Adjustment('Cloudiness',15,0,100,tip='Clear to cloudy. Softens the background through liquid; the front PNG stays sharp.')
        self.liquid_depth=Adjustment('Liquid depth',42,0,100,tip='Thickness of the sealed liquid chamber. The middle setting matches the approved test.')
        self.liquid_amount=Adjustment('Liquid amount',50,0,100,tip='0 is empty; 100 is full. The amount is retained as the board tilts.')
        self.liquid_thickness=Adjustment('Thickness (visual)',25,0,100,tip='Slower, smaller ripples for a syrup-like appearance. This does not simulate physical viscosity or persistent settling.')
        for control in (self.liquid_cloud,self.liquid_depth,self.liquid_amount,self.liquid_thickness):
            effects.addWidget(control);control.changed.connect(self.changed)
        self.ink_background=button('Background ink colour...',lambda:self.choose_ink_colour('background_colour'),effects)
        self.ink_revealed=button('Revealed ink colour...',lambda:self.choose_ink_colour('revealed_colour'),effects)
        self.ink_showthrough=Adjustment('Graphic show-through',0,0,100,tip='0% shows only the two ink colours; 100% shows the original graphic. Applies to both ink states.')
        effects.addWidget(self.ink_showthrough);self.ink_showthrough.changed.connect(self.changed)
        self.ink_strength=Adjustment('Mask strength',100,0,100,tip='Reduce how strongly white mask areas receive the ink reveal. Saved into the exported mask.')
        self.ink_contrast=Adjustment('Mask contrast',100,0,400,tip='Increase to sharpen grey mask boundaries; decrease for a softer mask. 100% preserves the original mask.')
        self.ink_invert=QCheckBox('Invert reveal mask')
        for control in (self.ink_strength,self.ink_contrast):
            effects.addWidget(control);control.changed.connect(self.changed)
        effects.addWidget(self.ink_invert);self.ink_invert.toggled.connect(self.changed)
        self.finish_hint=QLabel()
        self.finish_hint.setWordWrap(True)
        self.finish_hint.setAlignment(Qt.AlignTop|Qt.AlignLeft)
        effects.addWidget(self.finish_hint)
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
        disclaimer.setToolTip("If something breaks, please report it.\nIn-game shadows and banding are known issues\nand are being worked on.")
        footer.addWidget(disclaimer)
        dependency=QLabel('Effects require <a href="https://thunderstore.io/c/reskate/p/IdolRiot/Sofis_Deck_Effect_Core/">SDEC: Sofis Deck Effect Core</a> · enable one current copy.')
        dependency.setOpenExternalLinks(True);dependency.setWordWrap(True);outer.addWidget(dependency)

        self.status = QLabel('Choose artwork to begin.')
        self.status.setObjectName('muted')
        footer.addWidget(self.status,1)
        footer.addWidget(QLabel(self.quote))
        outer.addLayout(footer)
        for name,items in [('File',[('Open project…',self.open_project),('Save',self.save_project),('Export setup…',lambda:self.native_export_options(True)),('Convert older packs for SDEC…',self.update_fbmods)]),('Deck',[('Add deck',self.add_deck),('Remove selected',lambda:self.remove_deck(self.selected))]),('View',[('Enlarge preview',self.enlarge)]),('Help',[('Guide',self.guide)])]:
            menu = self.menuBar().addMenu(name)
            for text,action in items:
                menu.addAction(text,action)

    def current(self):
        return self.decks[self.selected]

    def remember(self):
        if self.loading:
            return
        d = self.current()
        d.update(name=self.name.text(),author=self.author.text(),mode=list(MODES)[self.mode.currentIndex()],lenticular=self.lenticular.isChecked(),fit=self.fit.currentText(),background_fit=self.backfit.currentText(),
            depth=dict(strength=self.strength.value()/100,convergence=self.convergence.value()/100,bands=self.bands.value()/100,invert=self.invert.isChecked()),
            animation=dict(quality=(1,2,4)[self.quality.currentIndex()]),wood_tint=d.get('wood_colour',d.get('wood_tint') or '#b98a56') if self.wood_mode.currentIndex() else None,wood_intensity=self.intensity.value()/100)
        d['neon']=dict(selection='colour' if self.neon_method.currentIndex() else 'mask',colour=d.get('neon',{}).get('colour','#00dfff'),tolerance=self.neon_tolerance.value()/100,brightness=self.neon_brightness.value()/100)
        for kind,(method,mask_button,mask_name,colour_button,tolerance) in self.ghost_area_controls.items():
            cfg=d.setdefault('ghost',{}).setdefault(kind,{})
            cfg.update(selection=('all','mask','colour')[method.currentIndex()],tolerance=tolerance.value()/100)
        d['ink']=dict(background_colour=d.get('ink',{}).get('background_colour','#242c42'),revealed_colour=d.get('ink',{}).get('revealed_colour','#88c0d3'),showthrough=self.ink_showthrough.value()/100,strength=self.ink_strength.value()/100,contrast=self.ink_contrast.value()/100,invert=self.ink_invert.isChecked())
        d['layer_depths']=[control.value()/100 for control in self.layer_depth_controls]
        d['liquid']=dict(colour=d.get('liquid',{}).get('colour','#9630d8'),cloudiness=self.liquid_cloud.value()/100,depth=.025+.155*self.liquid_depth.value()/100,amount=self.liquid_amount.value()/100,thickness=self.liquid_thickness.value()/100)

    def workspace(self):
        self.remember()
        return copy.deepcopy(dict(version=7,selected=self.selected,decks=self.decks))

    def draw_tabs(self):
        self.tabs.blockSignals(True)
        while self.tabs.count():
            self.tabs.removeTab(0)
        for d in self.decks:
            self.tabs.addTab(d['name'] or 'Untitled deck')
        self.tabs.setCurrentIndex(self.selected)
        self.tabs.blockSignals(False)
        self.update_export_controls()

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
        ink=d.get('ink',{})
        self.ink_showthrough.set_value(ink.get('showthrough',0)*100)
        self.ink_strength.set_value(ink.get('strength',1)*100)
        self.ink_contrast.set_value(ink.get('contrast',1)*100)
        self.ink_invert.setChecked(ink.get('invert',False))
        neon=d.get('neon',{})
        self.neon_method.setCurrentIndex(1 if neon.get('selection')=='colour' else 0)
        self.neon_tolerance.set_value(neon.get('tolerance',.15)*100)
        self.neon_brightness.set_value(neon.get('brightness',1)*100)
        for kind,(method,mask_button,mask_name,colour_button,tolerance) in self.ghost_area_controls.items():
            cfg=d.get('ghost',{}).get(kind,{})
            method.setCurrentIndex({'all':0,'mask':1,'colour':2}.get(cfg.get('selection','all'),0))
            tolerance.set_value(cfg.get('tolerance',.15)*100)
        liquid=d.get('liquid',{})
        self.liquid_cloud.set_value(liquid.get('cloudiness',.15)*100)
        self.liquid_depth.set_value((liquid.get('depth',.09)-.025)/.155*100)
        self.liquid_amount.set_value(liquid.get('amount',.5)*100)
        self.liquid_thickness.set_value(liquid.get('thickness',.25)*100)
        self.lenticular.setChecked(d.get('lenticular',True))
        for control,value in zip(self.layer_depth_controls,d.get('layer_depths',(.1,.45,.9))):control.set_value(value*100)
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
        names = {'classic':('Image A','Image B'),'depth':('Colour image','Depth map'),'ghost':('Colour image','Depth map'),'layers':('Foreground (transparency supported)','Background'),'gif':('Animation','Unused'),'metal':('Graphic','Unused'),'ink':('Graphic','Reveal mask (white reveals ink)'),'window':('Front frame (transparent PNG)','Background'),'liquid':('Front image (transparent PNG)','Background'),'neon':('Artwork','Glow mask (white glows, black stays unlit)')}[mode]
        self.lenticular.setVisible(mode in ('depth','layers'))
        self.lenticular_help.setVisible(mode in ('depth','layers'))
        self.lenticular.setEnabled(not self.busy)
        for i,label in enumerate(self.image_labels):
            label.setText(names[i])
            self.image_names[i].setText(Path(self.current()['images'][i]).name if self.current()['images'][i] else '')
            for w in (label,self.image_names[i],self.image_buttons[i]):
                w.setVisible(i==0 or (mode not in ('gif','metal') and not (mode=='neon' and self.neon_method.currentIndex()==1)))
        for w in (self.auto_button,self.auto_help):
            w.setVisible(mode in ('depth','ghost'))
        self.multi_panel.setVisible(mode=='classic')
        if mode=='classic':
            selected=self.picture_list.currentRow();self.picture_list.clear()
            for i,path in enumerate([*self.current()['images'],*self.current().get('extra_images',[])]):self.picture_list.addItem(f'{i+1}. '+(Path(path).name if path else 'Choose image'))
            self.picture_list.setCurrentRow(max(0,selected))
        self.neon_method.setVisible(mode=='neon');self.neon_colour.setVisible(mode=='neon' and self.neon_method.currentIndex()==1)
        self.neon_tolerance.setVisible(mode=='neon' and self.neon_method.currentIndex()==1);self.neon_brightness.setVisible(mode=='neon')
        self.quality.setVisible(mode=='gif')
        self.backfit.setVisible(mode=='layers')
        self.backfit_label.setVisible(mode=='layers')
        three=mode=='layers' and bool(self.current().get('middle_image'))
        self.middle_panel.setVisible(mode in ('layers','window'))
        self.middle_label.setText('Object layer (optional · transparent PNG)' if mode=='window' else 'Middle layer (optional · transparency supported)')
        self.middle_name.setText(Path(self.current()['middle_image']).name if self.current().get('middle_image') else '')
        for control in self.layer_depth_controls:control.setVisible(three)
        self.convergence.setVisible(not three)
        count=1 if mode=='metal' else 3 if (three or mode=='window' and self.current().get('middle_image')) else 2
        placement_labels=['Graphic'] if mode=='metal' else ['Front frame','Background','Object layer'][:count] if mode=='window' else ['Foreground','Background','Middle layer'] if three else ['First image','Second image']
        if [self.placement_choice.itemText(i) for i in range(self.placement_choice.count())]!=placement_labels:
            self.placement_choice.blockSignals(True)
            self.placement_choice.clear();self.placement_choice.addItems(placement_labels)
            self.placement_choice.blockSignals(False)
            self.placement_index=None
        for w in (self.strength,self.bands,self.convergence,self.invert):
            w.setEnabled(mode in ('depth','layers','ghost') and not self.busy)
        self.bands.setEnabled(mode in ('depth','layers') and self.lenticular.isChecked() and not self.busy)
        self.bands.setVisible(mode in ('depth','layers') and self.lenticular.isChecked())
        for w in (self.strength,self.convergence,self.invert):
            w.setVisible(mode not in ('classic','metal','ink','window','liquid','neon') and not (three and w==self.convergence))
        for control in (self.ink_background,self.ink_revealed,self.ink_showthrough,self.ink_strength,self.ink_contrast,self.ink_invert):
            control.setVisible(mode=='ink');control.setEnabled(not self.busy)
        self.ghost_box.setVisible(mode=='ghost')
        for kind,(method,mask_button,mask_name,colour_button,tolerance) in self.ghost_area_controls.items():
            cfg=self.current().get('ghost',{}).get(kind,{})
            mask_button.setVisible(method.currentIndex()==1);mask_name.setVisible(method.currentIndex()==1)
            mask_name.setText(Path(cfg['mask']).name if cfg.get('mask') else 'No mask selected')
            colour_button.setVisible(method.currentIndex()==2);tolerance.setVisible(method.currentIndex()==2)
        for control in (self.liquid_colour,self.liquid_cloud,self.liquid_depth,self.liquid_amount,self.liquid_thickness):control.setVisible(mode=='liquid')
        self.finish_hint.setVisible(mode in ('classic','metal','ink','window','liquid','neon'))
        self.finish_hint.setText({'classic':'Choose two to eight pictures, then use Move up / Move down to set their viewing order. Fine lens bands and slight overlap match the original lenticular effect.',
            'neon':'White mask areas glow in the artwork colour; black stays unlit. Greys reduce the glow. The colour picker creates a mask automatically. Preview glow is illustrative; game bloom varies.',
            'metal':'Sparkle changes with viewing angle. Choose one graphic image.',
            'ink':'The mask controls the transition between background and revealed ink. Graphic show-through blends your artwork into both colours. Custom colours require SDEC core 1.4.0 or the updated PSDEC package.',
            'liquid':'The front PNG stays on the outer face. Transparent areas reveal the liquid and background; opaque areas cast an internal approximate shadow.',
            'window':'Use a transparent front frame to reveal the recessed background. The optional object sits between them.'}.get(mode,''))
        self.convergence.title.setText('Background motion' if mode=='layers' else 'Stationary depth')
        self.swap_button.setEnabled(mode=='classic')
        self.detail_toggle.setEnabled(mode in ('depth','layers') and self.lenticular.isChecked())
        self.detail_toggle.setVisible(mode in ('depth','layers') and self.lenticular.isChecked())
        self.placement_choice.setEnabled(mode not in ('depth','ghost','gif','neon'))
        if mode in ('depth','ghost','gif','neon'):
            self.placement_choice.setCurrentIndex(0)

    def choose_ghost_mask(self,kind):
        path,_=QFileDialog.getOpenFileName(self,'Choose '+kind+' finish mask',filter='Mask images (*.png *.webp *.tif *.tiff *.bmp)')
        if path:
            self.current().setdefault('ghost',{}).setdefault(kind,{})['mask']=path
            self.changed()

    def choose_ghost_colour(self,kind):
        cfg=self.current().setdefault('ghost',{}).setdefault(kind,{})
        colour=QColorDialog.getColor(QColor(cfg.get('colour','#ffffff')),self,'Choose artwork colour for '+kind)
        if colour.isValid():cfg['colour']=colour.name();self.changed()

    def choose_ink_colour(self,key):
        defaults={'background_colour':'#242c42','revealed_colour':'#88c0d3'}
        cfg=self.current().setdefault('ink',{})
        colour=QColorDialog.getColor(QColor(cfg.get(key,defaults[key])),self,'Choose '+('background' if key=='background_colour' else 'revealed')+' ink colour')
        if colour.isValid():cfg[key]=colour.name();self.changed()

    def choose_neon_colour(self):
        colour=QColorDialog.getColor(QColor(self.current().get('neon',{}).get('colour','#00dfff')),self,'Choose artwork colour to glow')
        if colour.isValid():self.current().setdefault('neon',{})['colour']=colour.name();self.changed()

    def choose_pictures(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Choose 2–8 lenticular pictures',filter='Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if not paths:return
        if not 2<=len(paths)<=8:QMessageBox.warning(self,'Picture count','Choose between two and eight pictures.');return
        self.set_pictures(paths)

    def set_pictures(self,paths):
        self.current()['images']=paths[:2];self.current()['extra_images']=paths[2:]
        self.current()['placement']=[dict(zoom=1,x=0,y=0),dict(zoom=1,x=0,y=0)]
        self.changed()

    def move_picture(self,offset):
        paths=[*self.current()['images'],*self.current().get('extra_images',[])]
        index=self.picture_list.currentRow();other=index+offset
        if index<0 or not 0<=other<len(paths):return
        paths[index],paths[other]=paths[other],paths[index];self.set_pictures(paths);self.picture_list.setCurrentRow(other)

    def remove_picture(self):
        paths=[*self.current()['images'],*self.current().get('extra_images',[])]
        index=self.picture_list.currentRow()
        if len(paths)<=2:QMessageBox.information(self,'Two pictures needed','A lenticular deck needs at least two pictures.');return
        if index>=0:paths.pop(index);self.set_pictures(paths)

    def choose_liquid_colour(self):
        colour=QColorDialog.getColor(QColor(self.current().get('liquid',{}).get('colour','#9630d8')),self,'Liquid colour')
        if colour.isValid():
            self.current().setdefault('liquid',{})['colour']=colour.name()
            self.changed()

    def changed(self,*args):
        if self.loading or self.busy:
            return
        self.remember()
        self.update_mode()
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

    def choose_middle(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose middle layer','','Images (*.png *.webp *.tif *.tiff *.jpg *.jpeg *.bmp)')
        if path:
            self.current()['middle_image']=path;self.update_mode();self.schedule(clear=True)

    def clear_middle(self):
        self.current()['middle_image']=None;self.update_mode();self.schedule(clear=True)

    def schedule(self,clear=False):
        self.invalidate_export_preview()
        self.revision += 1
        self.pending = None
        self.gif_cache.clear()
        self.last_key = None
        if clear:
            self.frame_renderer = self.frame_renderer_key = None
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
        if not d['images'][0] or (d['mode'] not in ('gif','metal') and not (d['mode']=='neon' and d.get('neon',{}).get('selection')=='colour') and not all(d['images'])):
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
        clip_key = None
        if d['mode']=='gif':
            path = Path(d['images'][0])
            try:
                stamp = path.stat()
                clip_key = (str(path.resolve()),stamp.st_mtime_ns,stamp.st_size)
            except OSError:
                pass
        cached_clip = self.clip if clip_key is not None and clip_key==self.clip_source_key else None
        def run():
            try:
                settings = d.get('depth',{})
                if d['mode']=='gif':
                    clip = cached_clip if cached_clip is not None else animation.load(d['images'][0])
                    still = animation_texture.preview_frame(clip,0,d['background'],d['placement'][0])
                    result = (None,None,clip,[still,still],None,clip_key)
                else:
                    sources = cached_sources
                    if sources is None:
                        sources = []
                        paths=(d['images'][:1] if d['mode']=='metal' or (d['mode']=='neon' and d.get('neon',{}).get('selection')=='colour') else d['images'])+([d['middle_image']] if d['mode'] in ('layers','window') and d.get('middle_image') else [])
                        for path in paths:
                            with Image.open(path) as source:
                                source = ImageOps.exif_transpose(source).convert('RGBA')
                                source.thumbnail((1024,4096),Image.Resampling.LANCZOS)
                                sources.append(source)
                    images = [image_placement.frame(source,d['background_fit'] if d['mode']=='layers' and i==1 else d['fit'],d['background'],d.get('middle_placement',{}) if i==2 else d['placement'][i],alpha=(d['mode'] in ('layers','window','liquid') and i in (0,2)) or (d['mode']=='neon' and i==1),depth=d['mode'] in ('depth','ghost','ink') and i==1) for i,source in enumerate(sources)]
                    if d['mode'] in ('depth','ghost') and settings.get('invert'):
                        images[1] = ImageOps.invert(images[1].convert('RGB'))
                    strength,convergence,bands = (settings.get(k,v) for k,v in [('strength',.04),('convergence',.5),('bands',1)])
                    def progress(message):
                        if revision!=self.revision:
                            raise InterruptedError()
                    preview_mode=d['mode']
                    if d['mode']=='neon':
                        import advanced_atlas
                        atlas=advanced_atlas.neon_pack(images[0],images[1] if len(images)>1 else None,d.get('neon'))
                        thumbs=[images[0],images[0]]
                    elif d['mode']=='classic' and d.get('extra_images'):
                        import advanced_atlas
                        extra=[image_placement.frame(path,d['fit'],d['background'],{}) for path in d['extra_images']]
                        atlas=advanced_atlas.multi_pack([*images,*extra]);preview_mode='multi';thumbs=[images[0],extra[-1]]
                    elif d['mode']=='liquid':
                        import liquid_atlas
                        atlas=liquid_atlas.pack(images[0],images[1],d.get('liquid'))
                        preview=AtlasPreview(atlas,'liquid')
                        thumbs=[preview.render(a,(128,512)) for a in (-.4,.4)]
                    elif d['mode'] in ('metal','ink','window'):
                        import finish_atlas
                        atlas=finish_atlas.pack(d['mode'],images[0],images[1] if len(images)>1 else None,images[2] if len(images)>2 else None,ink=d.get('ink'))
                        preview_mode=d['mode']
                        preview=AtlasPreview(atlas,preview_mode)
                        thumbs=[preview.render(a,(128,512)) for a in (-.4,.4)]
                    elif d['mode']=='ghost' or (d['mode']=='depth' and not d.get('lenticular',True)):
                        import smooth_effect
                        atlas=smooth_effect.pack(*images,strength,convergence,d['mode']=='ghost',d.get('ghost'),d['fit'],d['placement'][0])
                        thumbs=images
                        preview_mode='ghost' if d['mode']=='ghost' else 'smooth'
                        if d['mode']=='ghost':
                            ghost_preview=AtlasPreview(atlas,'ghost');thumbs=[ghost_preview.render(a,(128,512)) for a in (-.4,.4)]
                    elif d['mode']=='depth':
                        views = preview_depth.views(*images,strength,convergence,progress)
                        atlas = engine.depth_views.pack(views,bands,balanced=True)
                        thumbs = [views[0],views[-1]]
                    elif d['mode']=='layers':
                        if len(images)==3:
                            atlas=engine.layer_atlas.pack_three(images[0],images[2],images[1],strength,d.get('layer_depths',(.1,.45,.9)),bands if d.get('lenticular',True) else 0,settings.get('invert',False))
                            preview_mode='layers3'
                            thumb_renderer=AtlasPreview(atlas,preview_mode)
                            thumbs=[thumb_renderer.render(a,(128,512)) for a in (-1,1)]
                        else:
                            atlas = engine.layer_atlas.pack(*images,strength,convergence,bands if d.get('lenticular',True) else 0,settings.get('invert',False))
                            thumbs = images
                    else:
                        atlas = engine.atlas(*images)
                        thumbs = images
                    progress('')
                    renderer = AtlasPreview(atlas,preview_mode)
                    detail = copy.copy(renderer)
                    detail.settings = detail.settings.copy()
                    result = (renderer,detail,None,thumbs,sources,None)
                self.events.put(('preview',revision,result))
            except InterruptedError:
                self.events.put(('preview',revision,None))
            except Exception as exc:
                self.events.put(('preview_error',revision,str(exc)))
        threading.Thread(target=run,daemon=True).start()

    def poll(self):
        while not self.events.empty():
            kind,revision,result = self.events.get()
            if kind=='export_preview':
                self.texture_worker = False
                self.export_preview.setEnabled(True)
                source, decoded, error = result
                if revision == self.revision and source is self.renderer and self.export_preview.isChecked():
                    if error:
                        self.invalidate_export_preview()
                        self.status.setText('Export texture preview: '+error)
                    else:
                        self.export_renderer, self.export_renderer_key = decoded, (revision,source)
                        self.preview_note.setText('Exported BC7 pixels · game lighting and shape are approximate')
                        self.status.setText('Export texture ready')
                        self.render_reset()
                elif self.export_preview.isChecked():
                    self.invalidate_export_preview()
            elif kind=='frame':
                self.frame_worker = False
                key, image, error = result
                dragging = self.angle.slider.isSliderDown() or self.orbit_dragging
                wanted = self.frame_request_key
                acceptable = key == wanted or (dragging and wanted is not None and key[2:7] == wanted[2:7] and key[7][:2] == wanted[7][:2] and key[-1] == wanted[-1])
                if revision == self.revision and acceptable:
                    if error:
                        self.last_key = key
                        self.status.setText('Preview: '+error)
                    else:
                        self.present_frame(image, key, prepared=True)
                self.render()
            elif kind in ('preview','preview_error'):
                self.worker = False
                if revision==self.revision:
                    if kind=='preview_error':
                        self.status.setText('Preview: '+result)
                    elif result:
                        keep_clock = self.clip is not None and result[2] is not None and self.clip_path==self.current()['images'][0]
                        self.renderer,self.detail_renderer,self.clip,self.thumbnail_sources,self.placement_sources,self.clip_source_key = result
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
            elif kind=='update_progress':
                self.update_button.setText(f'Downloading update {result}%')
            elif kind=='update_ready':
                try:
                    from updates import stage_install
                    stage_install(result[0],sys.executable,result[1])
                except Exception as exc:
                    self.set_busy(False)
                    self.update_button.setEnabled(True)
                    self.update_button.setText('Update available')
                    QMessageBox.warning(self,'Update failed',str(exc))
                else:
                    self.baseline=self.workspace()
                    self.set_busy(False)
                    self.close()
                    QApplication.instance().quit()
            elif kind=='update_failed':
                self.set_busy(False)
                self.update_button.setEnabled(True)
                self.update_button.setText('Update available')
                QMessageBox.warning(self,'Update failed',result)
            elif kind=='status':
                self.status.setText(result)
            elif kind=='compatibility':
                self.set_busy(False)
                saved,failed = result
                self.status.setText(f'Updated {len(saved)} pack(s); {len(failed)} skipped.')
                message = 'Original files were left unchanged.\n\n'
                if saved:
                    message += 'Saved:\n'+'\n'.join(saved)+'\n\nInstall SDEC, then import these content copies and disable their older bundled versions. Originals are preserved.'
                if failed:
                    message += '\n\nSkipped:\n'+'\n'.join(failed)
                QMessageBox.information(self,'SDEC conversion',message)
            elif kind in ('export','error'):
                self.set_busy(False)
                if kind=='export':
                    self.status.setText('Saved: '+result)
                    instruction = ('Deck pack installed. Enable it in the ReSkate launcher. Previous tool exports are backed up in .deck-tool-backups beside the mod folder.'
                        if Path(result).is_dir() else 'Install this ZIP through the ReSkate launcher, or extract its mod folder into Mods. No manual Studio import is needed.'
                        if Path(result).suffix.lower()=='.zip' else 'Import this FBMOD in Studio when you want to build or edit it.')
                    QMessageBox.information(self,'Export complete',instruction+'\n\nRequires SDEC, installed separately from Thunderstore. The tool does not download or bundle it.\n\nhttps://thunderstore.io/c/reskate/p/IdolRiot/Sofis_Deck_Effect_Core/\n\n'+result)
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
        self.invalidate_export_preview()
        if self.renderer:
            self.renderer.set_lens_strength(self.bands.value()/100)
        self.render_reset()

    def render(self):
        active_renderer = self.active_preview_renderer()
        mode = self.current()['mode']
        angle,bands = self.angle.value()/100,self.bands.value()/100
        gif_index = self.clip.frame_index(((time.monotonic()-self.started)*1000)%self.clip.duration_ms) if self.clip else None
        size = (120,480) if self.angle.slider.isSliderDown() or self.orbit_dragging else (180,720) if not self.large else (320,1280)
        surface_state = (self.view_mode.currentText(),self.studio_light.isChecked(),self.board.yaw,self.board.pitch)
        key = (self.revision,angle,bands,self.detail_toggle.isChecked(),gif_index,size,self.live_placement,surface_state,active_renderer is self.export_renderer and active_renderer is not None)
        self.frame_request_key = key
        if self.last_key==key:
            return
        if active_renderer is not None and not self.clip and not self.live_placement:
            if self.display_revision != self.revision or self.frame_worker:
                return
            renderer_key = (active_renderer, bands)
            if self.frame_renderer_key != renderer_key:
                self.frame_renderer = copy.copy(active_renderer)
                self.frame_renderer.settings = active_renderer.settings.copy()
                if active_renderer is not self.export_renderer:
                    self.frame_renderer.set_lens_strength(bands)
                self.frame_renderer_key = renderer_key
            snapshot = self.frame_renderer
            self.frame_worker = True
            def draw():
                try:
                    result = (key, self.prepare_surface(self.effect_frame(snapshot,angle,size,key), key), None)
                except Exception as exc:
                    result = (key, None, str(exc))
                self.events.put(('frame', key[0], result))
            threading.Thread(target=draw, daemon=True).start()
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
            image = self.effect_frame(self.renderer,angle,size,key)
        else:
            return
        if surface_state[1]:
            if self.frame_worker:
                return
            self.frame_worker = True
            def finish_surface():
                try:
                    result = (key,self.prepare_surface(image.resize(size,Image.Resampling.LANCZOS),key),None)
                except Exception as exc:
                    result = (key,None,str(exc))
                self.events.put(('frame',key[0],result))
            threading.Thread(target=finish_surface,daemon=True).start()
        else:
            self.present_frame(image, key)

    @staticmethod
    def effect_frame(renderer,angle,size,key,region=None):
        if key[7][0]=='3D' and getattr(renderer,'mode',None) in ('classic','multi','depth','smooth','ghost'):
            return renderer.render(angle,size,region or (0,0,1,1),view_profile=board_preview.LENS_VIEW_PROFILE)
        if key[7][0]=='3D' and getattr(renderer,'mode',None) in ('metal','ink','window','liquid'):
            return renderer.render(angle,size,region or (0,0,1,1),view_pose=key[7][2:4])
        if key[7][1] and getattr(renderer,'mode',None)=='neon':
            return renderer.render(angle,size,region or (0,0,1,1),material=True)
        return renderer.render(angle,size,region) if region is not None else renderer.render(angle,size)

    @staticmethod
    def prepare_surface(image,key):
        emission=image.info.get('linear_emission')
        image=board_preview.map_artwork(image)
        view,lit,yaw,pitch=key[7]
        if lit:
            from preview_lighting import shade, map_emission
            # 2D is a face-on inspection, regardless of the last 3D orbit.
            if view=='2D':yaw,pitch=0.,0.
            image=shade(image,yaw,pitch,emission=map_emission(emission,image.size) if emission is not None else None)
        return image

    def present_frame(self, image, key, prepared=False):
        mode = self.current()['mode']
        angle, bands = key[1:3]
        self.last_key = key
        self.preview_title.setText('Deck preview · positioning' if self.live_placement and not self.clip else 'Deck preview · export texture' if key[-1] else 'Deck preview')
        if not prepared:
            image = board_preview.map_artwork(image)
        pixmap = QPixmap.fromImage(qt_image(image))
        self.board.frame = pixmap
        self.board.update()
        if self.large:
            self.large_board.frame = pixmap
            self.large_board.update()
        show = mode in ('depth','layers') and self.current().get('lenticular',True) and self.detail_toggle.isChecked() and self.detail_renderer is not None
        self.update_inspectors()
        inspected = self.export_renderer if key[-1] else self.detail_renderer
        detail_key = (id(inspected),angle,bands,getattr(self,'lens_region',None))
        if show and detail_key!=self.last_detail_key:
            self.last_detail_key = detail_key
            self.detail_images[1][0].setText(f'Lens texture {bands*100:.0f}%')
            inspection = copy.copy(inspected)
            inspection.settings = inspected.settings.copy()
            for (_,label),strength in zip(self.detail_images,(0,bands)):
                inspection.set_lens_strength(strength)
                crop = self.effect_frame(inspection,angle,(240,96),key,self.lens_region)
                label.setPixmap(QPixmap.fromImage(qt_image(crop)))

    def guides_changed(self,value):
        self.board.guides = value
        self.board.update()
        if self.large:
            self.large_board.guides = value
            self.large_board.update()

    def active_preview_renderer(self):
        if self.export_preview.isChecked() and self.export_renderer_key == (self.revision,self.renderer):
            return self.export_renderer
        return self.renderer

    def invalidate_export_preview(self):
        self.export_renderer = self.export_renderer_key = None
        self.export_preview.blockSignals(True)
        self.export_preview.setChecked(False)
        self.export_preview.blockSignals(False)
        self.preview_note.setText('Fast texture preview · game lighting and shape are approximate')

    def export_texture_checked(self,enabled):
        self.render_reset()
        if not enabled:
            self.preview_note.setText('Fast texture preview · game lighting and shape are approximate')
            return
        if self.texture_worker or self.renderer is None or self.clip or self.live_placement or self.display_revision != self.revision:
            self.invalidate_export_preview()
            self.status.setText('Finish editing a static deck before checking its export texture.')
            return
        self.remember()
        revision, source, project = self.revision, self.renderer, copy.deepcopy(self.current())
        self.texture_worker = True
        self.export_preview.setEnabled(False)
        self.status.setText('Preparing export texture; fast preview remains available…')
        def run():
            try:
                import preview_texture
                decoded = preview_texture.prepare(project,source.mode)
                result = (source,decoded,None)
            except Exception as exc:
                result = (source,None,str(exc))
            self.events.put(('export_preview',revision,result))
        threading.Thread(target=run,daemon=True).start()

    def preview_angle_changed(self,*args):
        if self.view_mode.currentText() == '3D' and not self.camera_sync:
            yaw = board_preview.orbit_yaw(self.angle.value()/100)
            for board in ([self.board,self.large_board] if self.large else [self.board]):
                board.yaw = yaw
                board.update()
        self.render_reset()

    def preview_orbit_changed(self,yaw,pitch,dragging):
        self.orbit_dragging = dragging
        for board in ([self.board,self.large_board] if self.large else [self.board]):
            board.yaw,board.pitch = yaw,pitch
            board.update()
        self.camera_sync = True
        try:
            self.angle.spin.setValue(board_preview.orbit_angle(yaw)*100)
        finally:
            self.camera_sync = False
        self.render_reset()

    def preview_view_changed(self,value):
        self.studio_light.setEnabled(True)
        if value == '3D':
            self.preview_orbit_changed(self.board.yaw,self.board.pitch,False)
        else:
            self.orbit_dragging = False
        self.board.view_mode=value
        self.board.update()
        if self.large:
            self.large_board.view_mode=value
            self.large_board.update()
        self.render_reset()

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
        label={'neon':'NEON','liquid':'LIQUID','gif':'ANIMATED','metal':'METALLIC','ink':'INK FLOW','window':'WINDOW'}.get(d['mode'],'LENTICULAR')
        self.thumb_name.setText(Path(custom).name if custom else 'Automatic · transparent background + '+label)
        try:
            sources = self.thumbnail_sources if self.renderer or self.clip else [None,None]
            if custom or all(x is not None for x in sources):
                image = engine.thumbnail(*sources,custom,size=64,label=label)
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
        lens = self.current()['mode'] in ('depth','layers') and self.current().get('lenticular',True) and self.detail_toggle.isChecked()
        self.detail_box.setVisible(lens)
        self.placement.setVisible(self.placement_open)

    def choose_placement(self,index):
        if index<0:return
        self.placement_index = index
        was_loading = self.loading
        self.loading = True
        for key,control in self.positions.items():
            setting=self.current().get('middle_placement',{}) if index==2 else self.current()['placement'][index]
            control.set_value(setting.get(key,1 if key=='zoom' else 0)*100)
        self.loading = was_loading
        if not was_loading and self.current()['mode']=='classic':
            self.angle.spin.setValue(100 if index==0 else -100)

    def move_image(self,*args):
        if self.loading or self.placement_index is None:
            return
        setting = {key:control.value()/100 for key,control in self.positions.items()}
        d = self.current()
        if self.placement_index==2:d['middle_placement']=setting
        else:d['placement'][self.placement_index] = setting
        if d['mode'] in ('depth','ghost'):
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
        self.large_board.orbit_changed.connect(self.preview_orbit_changed)
        self.large_board.view_mode = self.view_mode.currentText()
        self.large_board.yaw,self.large_board.pitch = self.board.yaw,self.board.pitch
        self.large_board.guides = self.guides.isChecked()
        self.large_board.wood = self.board.wood
        layout.addWidget(self.large_board,1)
        angle = Adjustment('Viewing angle',self.angle.value(),-100,100)
        angle.changed.connect(lambda value:self.angle.spin.setValue(value))
        self.angle.changed.connect(angle.set_value)
        layout.addWidget(angle)
        layout.addWidget(QLabel('Standard deck mapping · shape and lighting are approximate'))
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
