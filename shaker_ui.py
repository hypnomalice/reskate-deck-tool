"""Shaker authoring: independent PNG pieces in one shallow glass chamber."""
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QComboBox,QDoubleSpinBox,QCheckBox,QSizePolicy
import time,math,copy

def install(owner,parent):
    owner.shaker_box=QGroupBox('Shaker · rigid pieces in glass');layout=QVBoxLayout(owner.shaker_box)
    hint=QLabel('Requires SDEC 3.5.0 or newer. Pieces slide, spin and collide on one plane. PNG transparency defines each outline.');hint.setWordWrap(True);layout.addWidget(hint)
    owner.shaker_count=QComboBox();owner.shaker_count.addItems(['1 piece','2 pieces','3 pieces']);layout.addWidget(owner.shaker_count)
    owner.shaker_rim=QCheckBox('Clear acrylic rims');owner.shaker_rim.setChecked(True);layout.addWidget(owner.shaker_rim)
    owner.shaker_rows=[]
    for i in range(3):
        box=QGroupBox(f'Piece {i+1}');col=QVBoxLayout(box);button=QPushButton('Choose PNG…');col.addWidget(button)
        width=QDoubleSpinBox();width.setRange(10,100);width.setDecimals(1);width.setSingleStep(1);width.setSuffix(' mm wide');width.setValue(55)
        weight=QDoubleSpinBox();weight.setRange(.1,10);weight.setDecimals(2);weight.setSingleStep(.1);weight.setPrefix('Weight × ');weight.setValue(1)
        width.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);weight.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        props=QHBoxLayout();props.addWidget(width);props.addWidget(weight);col.addLayout(props)
        collision=QComboBox();collision.addItem('Follow PNG outline','outline');collision.addItem('Rectangle','rectangle');collision.addItem('Circle','circle');col.addWidget(collision)
        rim_width=QDoubleSpinBox();rim_width.setRange(0,5);rim_width.setDecimals(2);rim_width.setSingleStep(.1);rim_width.setPrefix('Rim: ');rim_width.setSuffix(' mm')
        rim_width.setToolTip('Clear acrylic outside the printed artwork. Included in the piece’s collision outline.')
        rim_strength=QDoubleSpinBox();rim_strength.setRange(0,100);rim_strength.setDecimals(0);rim_strength.setSingleStep(5);rim_strength.setPrefix('Strength: ');rim_strength.setSuffix(' %')
        rim_strength.setToolTip('How strongly the clear acrylic rim catches light. Does not change its collision size.')
        rim_props=QHBoxLayout()
        for widget in (rim_width,rim_strength):widget.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);rim_props.addWidget(widget)
        col.addLayout(rim_props)
        layout.addWidget(box)
        def choose(checked=False,index=i):
            path,_=QFileDialog.getOpenFileName(owner,f'Choose piece {index+1}','','PNG images (*.png)')
            if path:
                cfg=owner.current().setdefault('shaker',{});pieces=cfg.setdefault('pieces',[])
                while len(pieces)<=index:pieces.append({})
                pieces[index]['image']=path;owner.shaker_rows[index]['button'].setText(Path(path).name);owner.changed()
        button.clicked.connect(choose)
        if i:
            same=QPushButton('Use first piece’s image');col.addWidget(same)
            def duplicate(checked=False,index=i):
                pieces=owner.current().setdefault('shaker',{}).setdefault('pieces',[])
                if pieces and pieces[0].get('image'):
                    while len(pieces)<=index:pieces.append({})
                    pieces[index]['image']=pieces[0]['image'];owner.shaker_rows[index]['button'].setText(Path(pieces[0]['image']).name);owner.changed()
            same.clicked.connect(duplicate)
        owner.shaker_rows.append(dict(box=box,button=button,width=width,weight=weight,collision=collision,rim_width=rim_width,rim_strength=rim_strength))
        width.valueChanged.connect(owner.changed);weight.valueChanged.connect(owner.changed);collision.currentIndexChanged.connect(owner.changed)
        rim_width.valueChanged.connect(owner.changed);rim_strength.valueChanged.connect(owner.changed)
    owner.shaker_blur=QDoubleSpinBox();owner.shaker_blur.setRange(0,30);owner.shaker_blur.setDecimals(1);owner.shaker_blur.setPrefix('Background blur: ');owner.shaker_blur.setSuffix(' px');layout.addWidget(owner.shaker_blur)
    note=QLabel('Weight changes collisions, not falling speed. Use equipped grip tape can be switched on or off in Transparent material.');note.setWordWrap(True);layout.addWidget(note)
    view_box=QGroupBox('Inspect moving pieces');view=QVBoxLayout(view_box)
    row=QHBoxLayout();owner.shaker_demo=QPushButton('Shake preview');owner.shaker_demo.setCheckable(True);owner.shaker_pause=QPushButton('Pause');owner.shaker_pause.setCheckable(True);reset=QPushButton('Reset pieces')
    row.addWidget(owner.shaker_demo);row.addWidget(owner.shaker_pause);view.addLayout(row);view.addWidget(reset)
    owner.shaker_dim=QCheckBox('Dim background to see clear rims');view.addWidget(owner.shaker_dim)
    inspection_hint=QLabel('Preview only. Pause to inspect a rim, or enlarge the preview for detail.');inspection_hint.setWordWrap(True);view.addWidget(inspection_hint)
    layout.insertWidget(2,view_box)
    def reset_pieces():
        renderer=getattr(owner,'renderer',None)
        if getattr(renderer,'mode',None)=='shaker':renderer.solver.reset();renderer.poses=renderer.solver.step();owner.shaker_demo_seconds=0;owner.render()
    reset.clicked.connect(reset_pieces)
    owner.shaker_rim.toggled.connect(owner.changed);owner.shaker_blur.valueChanged.connect(owner.changed)
    def enable_rims(enabled):
        for row in owner.shaker_rows:
            row['rim_width'].setEnabled(enabled);row['rim_strength'].setEnabled(enabled)
    owner.shaker_rim.toggled.connect(enable_rims)
    def changed_count():
        for i,row in enumerate(owner.shaker_rows):row['box'].setVisible(i<=owner.shaker_count.currentIndex())
        owner.changed()
    owner.shaker_count.currentIndexChanged.connect(changed_count)
    parent.insertWidget(max(0,parent.indexOf(owner.transparency_box)),owner.shaker_box)
    owner.shaker_time=None;owner.shaker_demo_seconds=0
    def inspect():
        renderer=getattr(owner,'renderer',None)
        if getattr(renderer,'mode',None)=='shaker':renderer.dim_background=owner.shaker_dim.isChecked()
        owner.render()
    owner.shaker_dim.toggled.connect(inspect)
    owner.shaker_pause.toggled.connect(lambda paused:owner.shaker_pause.setText('Resume' if paused else 'Pause'))
    owner.shaker_demo.toggled.connect(lambda _:setattr(owner,'shaker_demo_seconds',0))
    owner.shaker_timer=QTimer(owner);owner.shaker_timer.setInterval(16)
    def tick():
        renderer=getattr(owner,'renderer',None)
        if owner.current()['mode']!='shaker' or not owner.isVisible() or owner.isMinimized() or getattr(renderer,'mode',None)!='shaker':owner.shaker_time=None;return
        now=time.monotonic();dt=min((now-owner.shaker_time) if owner.shaker_time else 0,1/30);owner.shaker_time=now
        yaw,pitch=owner.board.yaw,owner.board.pitch
        renderer.dim_background=owner.shaker_dim.isChecked()
        if owner.shaker_pause.isChecked():owner.render();return
        velocity=(0,0,0)
        if owner.shaker_demo.isChecked():
            owner.shaker_demo_seconds+=dt
            velocity=renderer.shake_velocity(owner.shaker_demo_seconds)
        try:renderer.advance(yaw,pitch,dt,velocity=velocity)
        except Exception as error:owner.status.setText('Shaker preview: '+str(error));return
        owner.render()
    owner.shaker_timer.timeout.connect(tick);owner.shaker_timer.start()

def remember(owner,deck):
    if deck.get('mode')!='shaker':return
    c=deck.setdefault('shaker',{});previous=c.get('pieces',[]);pieces=[]
    for i,row in enumerate(owner.shaker_rows[:owner.shaker_count.currentIndex()+1]):
        p=dict(previous[i] if i<len(previous) else {});p.update(width_mm=row['width'].value(),weight=row['weight'].value(),collision=row['collision'].currentData(),rim_mm=row['rim_width'].value(),rim_strength=row['rim_strength'].value()/100);pieces.append(p)
    c.update(pieces=pieces,rim=owner.shaker_rim.isChecked(),blur=owner.shaker_blur.value())

def apply(owner,deck):
    cfg=deck.get('shaker',{});pieces=cfg.get('pieces') or [{}]
    widgets=[owner.shaker_count,owner.shaker_rim,owner.shaker_blur]
    widgets.extend(w for row in owner.shaker_rows for k,w in row.items() if k in ('width','weight','collision','rim_width','rim_strength'))
    for w in widgets:w.blockSignals(True)
    try:
        owner.shaker_count.setCurrentIndex(min(3,len(pieces))-1)
        owner.shaker_rim.setChecked(cfg.get('rim',True));owner.shaker_blur.setValue(cfg.get('blur',0))
        for i,row in enumerate(owner.shaker_rows):
            p=pieces[i] if i<len(pieces) else {};row['box'].setVisible(i<len(pieces))
            row['button'].setText(Path(p['image']).name if p.get('image') else 'Choose PNG…')
            row['width'].setValue(p.get('width_mm',55));row['weight'].setValue(p.get('weight',1));row['collision'].setCurrentIndex(max(0,row['collision'].findData(p.get('collision','outline'))))
            row['rim_width'].setValue(p.get('rim_mm',__import__('shaker_effect').DEFAULT_RIM_MM));row['rim_strength'].setValue(p.get('rim_strength',1)*100)
            row['rim_width'].setEnabled(cfg.get('rim',True));row['rim_strength'].setEnabled(cfg.get('rim',True))
    finally:
        for w in widgets:w.blockSignals(False)
