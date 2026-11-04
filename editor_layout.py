"""Lightweight editor layout. Reuses the existing controls and export contract."""
from PySide6.QtCore import Qt,QObject,QEvent,QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTabWidget,QScrollArea,QGroupBox,QToolButton,QComboBox,QPushButton,QSplitter,QCheckBox,QListWidget,QAbstractSpinBox,QSlider

class ScrollGuard(QObject):
    def eventFilter(self,watched,event):
        if event.type()==QEvent.Wheel:
            event.ignore()
            return True
        return False

STYLE='''
QWidget { color:#dfe5ee; font-size:12px; }
QMainWindow,QDialog { background:#11151b; }
QScrollArea,QScrollArea>QWidget>QWidget { background:#171d25; border:0; }
QGroupBox { background:#171d25; border:1px solid #2b3543; border-radius:8px; margin-top:13px; padding:16px 12px 12px; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 5px; color:#a7b5c9; }
QLineEdit,QComboBox { background:#10161e; border:1px solid #344153; border-radius:5px; padding:6px; min-height:20px; }
QDoubleSpinBox { background:#10161e; color:#dfe5ee; }
QDoubleSpinBox QLineEdit { border:0; padding:0; background:transparent; min-height:0; }
QPushButton,QToolButton { background:#222d3b; border:1px solid #344153; border-radius:5px; padding:6px 10px; min-height:20px; }
QPushButton:hover,QToolButton:hover { border-color:#73a4f5; background:#28374b; }
QPushButton:checked,QPushButton#primary { background:#365eab; border-color:#719af0; color:white; }
QSlider::groove:horizontal { height:3px; background:#344153; border-radius:1px; }
QSlider::sub-page:horizontal { background:#719af0; }
QSlider::handle:horizontal { width:12px; margin:-5px 0; background:#bfd3fa; border-radius:6px; }
QTabBar::tab { padding:10px 16px; background:#171d25; color:#9babc1; border:0; border-bottom:2px solid transparent; }
QTabBar::tab:selected { color:#f0f5ff; background:#202b3a; border-bottom:2px solid #85adff; }
QTabWidget::pane { border:0; background:#171d25; }
QLabel#muted { color:#91a1b7; }
QLabel#sectionHeading { font-size:16px; font-weight:600; color:#f0f5ff; padding:4px 0; }
QMenuBar,QMenu { background:#11151b; } QMenu::item:selected { background:#365eab; }
QToolTip { background:#253246; color:white; border:1px solid #6b8fc3; padding:8px; }
QScrollBar:vertical { background:#171d25; width:9px; } QScrollBar::handle:vertical { background:#394a60; min-height:24px; border-radius:4px; }
'''

def scroll(content):
    box=QScrollArea();box.setWidgetResizable(True);box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);box.setWidget(content);return box

def install(w):
    w.setStyleSheet(STYLE);w.setWindowTitle('ReSkate Deck Tool · '+__import__('app_version').APP_VERSION)
    w.resize(1380,920)
    w.adjust_button.setText('Place artwork');w.swap_button.setVisible(False)
    w.export_button.setObjectName('primary')
    w.export_preview.setText('Check export texture')
    w.studio_light.setText('Studio light');w.studio_light.setToolTip('Approximate game-style lighting. Turn off to inspect the artwork colours.')
    w.preview_note.setText('Drag to inspect · Artwork tab to move your image')
    w.preview_note.setWordWrap(True)
    w.thumb_name.hide()
    for control in w.findChildren(QPushButton):
        if control.text()=='Load depth test scene':control.hide()
    # The original effect inspector stays intact inside its own tab.
    splitter=w.inspectors.parentWidget()
    while not isinstance(splitter,QSplitter):splitter=splitter.parentWidget()
    w.inspector_tabs=QTabWidget();w.inspector_tabs.setMinimumWidth(350)
    index=splitter.indexOf(w.inspectors);w.inspectors.setParent(None);splitter.insertWidget(index,w.inspector_tabs)
    artwork=QWidget();art=QVBoxLayout(artwork);art.setContentsMargins(14,14,14,14);art.setSpacing(14)
    heading=QLabel('Place your artwork');heading.setObjectName('sectionHeading');art.addWidget(heading)
    hint=QLabel('Drag on the board to move. Scroll to resize. Shift + scroll rotates. Numeric controls give precise placement.');hint.setWordWrap(True);hint.setObjectName('muted');art.addWidget(hint)
    w.placement.setTitle('Transform');art.addWidget(w.placement);art.addStretch()
    actions=QHBoxLayout()
    for title,action in [('Fit',lambda:w.fit.setCurrentText('Fit entire image')),('Fill',lambda:w.fit.setCurrentText('Crop to fill')),('+90°',lambda:w.rotate_artwork(90))]:
        button=QPushButton(title);button.clicked.connect(action);actions.addWidget(button)
    w.placement.layout().insertLayout(1,actions)
    w.artwork_scroll=scroll(artwork);w.inspector_tabs.addTab(w.artwork_scroll,'Artwork')
    w.inspector_tabs.addTab(w.inspectors,'Effect')
    finish=QWidget();fin=QVBoxLayout(finish);fin.setContentsMargins(14,14,14,14);fin.setSpacing(12)
    w.cd_surface_box=QGroupBox('CD surface');layout=QVBoxLayout(w.cd_surface_box)
    for control in [w.cd_clear,w.cd_controls['sheen_strength'],w.cd_backing]:layout.addWidget(control)
    extra_toggle=QToolButton();extra_toggle.setText('Surface details');extra_toggle.setCheckable(True);extra_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);extra_toggle.setArrowType(Qt.RightArrow);layout.addWidget(extra_toggle)
    extra=QWidget();extra_layout=QVBoxLayout(extra);extra_layout.setContentsMargins(0,8,0,0)
    for key in ('rim_strength','boundary_strength','scratch_strength','scratch_amount'):extra_layout.addWidget(w.cd_controls[key])
    w.cd_controls['scratch_amount'].spin.setSuffix(' lines');extra.setVisible(False)
    def details(opened):extra.setVisible(opened);extra_toggle.setArrowType(Qt.DownArrow if opened else Qt.RightArrow)
    extra_toggle.toggled.connect(details);layout.addWidget(extra);fin.addWidget(w.cd_surface_box);fin.addWidget(w.surface_box)
    # Wood is a finish, not a required artwork-input step.
    for group in w.settings.findChildren(QGroupBox):
        if group.title()=='Wood':fin.addWidget(group)
        elif group.title()=='In-game thumbnail':
            group.setTitle('Export thumbnail');group.setVisible(False)
            toggle=QToolButton();toggle.setText('Export thumbnail options');toggle.setCheckable(True);toggle.toggled.connect(group.setVisible)
            w.settings.layout().insertWidget(w.settings.layout().count()-1,toggle)
    fin.addStretch();w.inspector_tabs.addTab(scroll(finish),'Finish');w.inspector_tabs.setCurrentIndex(1)
    w.inspector_tabs.currentChanged.connect(w.inspector_tab_changed)
    # Small preview resolution is an explicit choice, independent of export quality.
    w.preview_quality=QComboBox();w.preview_quality.addItems(['Light preview','Balanced preview','Detailed preview']);w.preview_quality.setToolTip('Preview quality only. Export quality is unchanged. Light reduces the pixel workload and caps animated preview playback at 24 FPS.')
    w.preview_quality.currentIndexChanged.connect(w.render_reset)
    parent_layout=w.view_mode.parentWidget().layout()
    # Locate the preview toolbar without relying on widget coordinates.
    preview_layout=w.preview_title.parentWidget().layout()
    toolbar=None
    for i in range(preview_layout.count()):
        row=preview_layout.itemAt(i).layout()
        if row and row.indexOf(w.view_mode)>=0:toolbar=row;break
    if toolbar:toolbar.insertWidget(max(1,toolbar.indexOf(w.view_mode)),w.preview_quality)
    splitter.setSizes([285,700,365])
    # Every slider already has a numeric entry; duplicate +/- buttons add clutter.
    for control in w.findChildren(__import__('qt_ui').Adjustment):
        for tool in control.findChildren(QToolButton):
            if tool.text() in ('+','−'):tool.hide()
        control.spin.setFixedWidth(86)
    for control in w.positions.values():control.spin.setDecimals(2);control.spin.setFixedWidth(98)
    w.positions['rotation'].spin.setSuffix(' °')
    for label in w.findChildren(QLabel):
        if label.text()==w.quote:label.hide()
        if label.text()=='<u>DISCLAIMER</u>':label.hide()
    w.angle.slider.sliderReleased.connect(w.render_reset)
    w.board.artwork_dragged.connect(w.drag_artwork);w.board.artwork_zoomed.connect(w.zoom_artwork);w.board.artwork_rotated.connect(w.rotate_artwork)
    # Keep the primary effect choice permanently visible in the left column.
    w.mode.setObjectName('effectType')
    w.mode.setMinimumHeight(30)
    w.settings.layout().insertWidget(0,QLabel('EFFECT TYPE'))
    w.settings.layout().insertWidget(1,w.mode)
    w.effect_picker=QComboBox();w.effect_picker.addItem('Choose an effect…');w.effect_picker.addItems([w.mode.itemText(i) for i in range(w.mode.count())])
    w.effect_picker.setObjectName('effectType');w.effect_picker.setMinimumHeight(30)
    w.settings.layout().insertWidget(1,w.effect_picker);w.mode.hide()
    def choose_effect(index):
        if index<1:return
        w.current()['effect_chosen']=True
        w.mode.setCurrentIndex(index-1)
        w.inspector_tabs.setVisible(True)
    w.effect_picker.currentIndexChanged.connect(choose_effect)
    for label in w.settings.findChildren(QLabel):
        if label.text()=='Effect':label.hide()
    for tool in w.settings.findChildren(QToolButton):
        if tool.text()=='?' and 'Animated / GIF' in tool.toolTip():
            w.settings.layout().insertWidget(3,tool)
    w.settings.layout().insertWidget(0,w.add_button)
    w.settings.layout().insertWidget(0,w.tabs)
    # Image inputs belong with artwork, rather than occupying the left column.
    for group in list(w.settings.findChildren(QGroupBox)):
        if group.title()=='Images':
            group.setTitle('Upload artwork & layers')
            art.insertWidget(2,group)
    w.image_buttons[0].setText('Upload artwork…')
    w.image_buttons[1].setText('Upload second layer…')
    w.adjust_button.hide()
    # Secondary image setup stays available without pushing transform controls off-screen.
    advanced_toggle=QToolButton();advanced_toggle.setText('Additional image options');advanced_toggle.setCheckable(True)
    advanced=QWidget();advanced_layout=QVBoxLayout(advanced)
    advanced_layout.addWidget(w.auto_button);advanced_layout.addWidget(w.auto_help)
    advanced_layout.addWidget(QLabel('Artwork sizing'));advanced_layout.addWidget(w.fit)
    advanced_layout.addWidget(w.backfit_label);advanced_layout.addWidget(w.backfit)
    advanced.hide();advanced_toggle.toggled.connect(advanced.setVisible)
    art.insertWidget(art.count()-1,advanced_toggle);art.insertWidget(art.count()-1,advanced)
    for label in w.artwork_scroll.findChildren(QLabel):
        if label.text()=='Artwork sizing' and label.parentWidget()!=advanced:label.hide()
    w.link_transforms=QCheckBox('Link transforms')
    w.link_transforms.setToolTip('Apply movement, scaling and rotation to both layers while preserving their relative placement. Artwork and depth maps start linked.')
    w.placement.layout().insertWidget(1,w.link_transforms)
    def link_changed(checked):
        if w.loading:return
        w.current()['link_transforms']=checked
        w.mode_changed()
    w.link_transforms.toggled.connect(link_changed)
    precise=QToolButton();precise.setText('Precise placement');precise.setCheckable(True)
    precise.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);precise.setArrowType(Qt.RightArrow)
    w.placement.layout().addWidget(precise)
    for key in ('x','y'):w.positions[key].setVisible(False)
    def precision(opened):
        for key in ('x','y'):w.positions[key].setVisible(opened)
        precise.setArrowType(Qt.DownArrow if opened else Qt.RightArrow)
    precise.toggled.connect(precision)
    w.placement.setMinimumHeight(0)
    w.inspector_tabs.setCurrentIndex(0)
    w.export_mode.setMinimumWidth(165)
    w.setStyleSheet(STYLE+'''\nQComboBox#effectType { background:#303b55; border:1px solid #9b94e8; }\nQDoubleSpinBox { padding:2px 4px; min-height:24px; }\nQDoubleSpinBox QLineEdit { padding:0; min-height:0; color:#dfe5ee; }\n''')
    for control in w.findChildren(__import__('qt_ui').Adjustment):
        control.spin.lineEdit().setMinimumWidth(control.spin.width()-14)
    w.tabs.hide()
    w.deck_list=QListWidget();w.deck_list.setMinimumHeight(100);w.deck_list.setMaximumHeight(180)
    w.deck_list.currentRowChanged.connect(w.select_deck)
    w.settings.layout().insertWidget(0,w.deck_list)
    w.settings.layout().insertWidget(0,QLabel('YOUR DECKS'))
    remove=QPushButton('Remove selected deck');remove.clicked.connect(lambda:w.remove_deck(w.selected))
    w.settings.layout().insertWidget(4,remove)
    w.placement_render_timer=QTimer(w);w.placement_render_timer.setSingleShot(True);w.placement_render_timer.timeout.connect(w.render_reset)
    w.board.artwork_released.connect(w.finish_placement)
    w.scroll_guard=ScrollGuard(w)
    for control in w.findChildren(QWidget):
        if isinstance(control,(QComboBox,QAbstractSpinBox,QSlider)):
            control.installEventFilter(w.scroll_guard)
    for label in w.findChildren(QLabel):
        if label.text().startswith('Drag on the board to move.'):
            label.setText('Drag on the deck to move artwork. Use the sliders for size and rotation. Ctrl + scroll zooms; Ctrl + Shift + scroll rotates.')
