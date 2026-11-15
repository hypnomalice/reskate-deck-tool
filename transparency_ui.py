"""Controls for the supported native transparency authoring values."""
from PySide6.QtWidgets import QGroupBox,QVBoxLayout,QComboBox,QPushButton,QCheckBox,QLabel,QColorDialog
from PySide6.QtGui import QColor
import transparency_finish as finish


def install(owner,parent,Adjustment):
    owner.transparency_box=QGroupBox('Transparent material');box=QVBoxLayout(owner.transparency_box)
    owner.transparency_style=QComboBox();box.addWidget(owner.transparency_style)
    owner.transparency_tint=QPushButton('Tint');box.addWidget(owner.transparency_tint)
    owner.transparency_controls={}
    for key,label,maximum in [('tint_strength','Tint strength',100),('haze','Internal haze',100),('roughness','Surface roughness',100),('reflection_strength','Reflection strength',200)]:
        control=Adjustment(label,0,0,maximum);control.changed.connect(owner.changed);box.addWidget(control);owner.transparency_controls[key]=control
    owner.fluid_controls={}
    for key,label in [('opacity','Liquid opacity'),('viscosity','Liquid viscosity')]:
        control=Adjustment(label,0,0,100)
        control.changed.connect(owner.changed)
        box.addWidget(control)
        owner.fluid_controls[key]=control
    owner.liquid_rim=Adjustment('Clear rim width (mm)',10,2,25)
    owner.liquid_rim.changed.connect(owner.changed)
    box.addWidget(owner.liquid_rim)
    owner.transparency_grip=QCheckBox('Use equipped grip tape');box.addWidget(owner.transparency_grip)
    owner.transparency_legacy=QLabel();owner.transparency_legacy.setWordWrap(True);box.addWidget(owner.transparency_legacy)
    owner.transparency_migrate=QPushButton();box.addWidget(owner.transparency_migrate)
    def migrate():
        mode=owner.current()['mode'];cfg=owner.current().setdefault(mode,{})
        if mode=='case':
            cfg['legacy_masks']={key:cfg.get(key) for key in ('screw_mask','detail_mask')}
            cfg.update(screw_mask=None,detail_mask=None)
        elif mode=='crystal':cfg['legacy_cuts']=cfg.get('cuts',140);cfg['cuts']=140
        refresh_legacy(owner,mode,cfg);owner.changed()
    owner.transparency_migrate.clicked.connect(migrate)
    note=QLabel('Artwork stays inside the shell with a clear border. Internal haze affects the contained artwork; it does not blur the surrounding world.');note.setWordWrap(True);box.addWidget(note)
    def tint():
        mode=owner.current()['mode'];cfg=finish.settings(mode,owner.current().get(mode));colour=QColorDialog.getColor(QColor(cfg['tint']),owner,'Material tint')
        if colour.isValid():owner.current().setdefault(mode,{})['tint']=colour.name();owner.transparency_tint.setText('Tint '+colour.name());owner.changed()
    owner.transparency_tint.clicked.connect(tint)
    owner.transparency_style.currentIndexChanged.connect(owner.changed);owner.transparency_grip.toggled.connect(owner.changed)
    parent.addWidget(owner.transparency_box);owner._transparency_mode=None


def apply(owner,deck):
    mode=deck.get('mode');owner.transparency_box.setVisible(mode in finish.MODES)
    if mode not in finish.MODES:return
    cfg=finish.settings(mode,deck.get(mode));owner._transparency_mode=mode
    choices=[('Display glass','display'),('Moving water','water'),('Liquid in glass','liquid')] if mode=='glass' else [('Hazy artwork case','frosted'),('Clear artwork case','glossy'),('Hazy PCB case','pcb')] if mode=='case' else [('Cut crystal','crystal')]
    combo=owner.transparency_style;combo.blockSignals(True);combo.clear()
    for label,key in choices:combo.addItem(label,key)
    key='pcb' if mode=='case' and cfg['interior']=='pcb' else cfg.get('finish','crystal')
    combo.setCurrentIndex(max(0,combo.findData(key)));combo.blockSignals(False)
    owner.transparency_tint.setText('Tint '+cfg['tint'])
    for key,control in owner.transparency_controls.items():control.set_value(cfg[key]*100)
    for name,control in owner.fluid_controls.items():
        control.set_value(cfg.get(name,.53 if name=='opacity' else .26)*100)
        control.setVisible(mode=='glass' and cfg.get('finish')=='liquid')
    owner.liquid_rim.set_value(cfg.get('rim_mm',10))
    owner.liquid_rim.setVisible(mode=='glass' and cfg.get('finish')=='liquid')
    owner.transparency_grip.setChecked(cfg['grip_tape'])
    refresh_legacy(owner,mode,cfg)
    owner.transparency_controls['haze'].setEnabled(not (mode=='case' and key=='glossy'))


def remember(owner,deck):
    mode=deck.get('mode')
    if mode not in finish.MODES or owner._transparency_mode!=mode:return
    cfg=dict(deck.get(mode,{}))
    if mode=='case' and owner.transparency_style.currentData()=='glossy' and cfg.get('finish','frosted')!='glossy':
        owner.transparency_controls['roughness'].set_value(4)
    elif mode=='case' and owner.transparency_style.currentData() in ('frosted','pcb') and cfg.get('finish')=='glossy':
        owner.transparency_controls['roughness'].set_value(48)
    cfg.update({key:c.value()/100 for key,c in owner.transparency_controls.items()});cfg['grip_tape']=owner.transparency_grip.isChecked()
    selected=owner.transparency_style.currentData()
    for name,control in owner.fluid_controls.items():
        liquid=mode=='glass' and selected=='liquid'
        control.setVisible(liquid)
        if liquid:cfg[name]=control.value()/100
    owner.liquid_rim.setVisible(mode=='glass' and selected=='liquid')
    if mode=='glass' and selected=='liquid':cfg['rim_mm']=owner.liquid_rim.value()
    if mode=='glass':cfg['finish']=selected
    elif mode=='case':cfg.update(finish='frosted' if selected=='pcb' else selected,interior='pcb' if selected=='pcb' else 'artwork')
    deck[mode]=cfg
    refresh_legacy(owner,mode,cfg)
    owner.transparency_controls['haze'].setEnabled(not (mode=='case' and selected=='glossy'))


def refresh_legacy(owner,mode,cfg):
    masks=mode=='case' and bool(cfg.get('screw_mask') or cfg.get('detail_mask'))
    cuts=mode=='crystal' and cfg.get('cuts',140)!=140
    owner.transparency_legacy.setVisible(masks or cuts);owner.transparency_migrate.setVisible(masks or cuts)
    if masks:
        owner.transparency_legacy.setText('This project has custom screw/detail masks. Choose standard details to export with the new finish. The previous masks will remain saved in the project.')
        owner.transparency_migrate.setText('Use standard moulded details')
    elif cuts:
        owner.transparency_legacy.setText('This project has an older cut-density setting. Choose the current crystal pattern to export. The previous value will remain saved in the project.')
        owner.transparency_migrate.setText('Use current crystal pattern')
