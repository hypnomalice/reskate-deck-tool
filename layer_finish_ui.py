"""Layer finish controls, kept separate from whole-board legacy overlays."""
from pathlib import Path
from PySide6.QtWidgets import QGroupBox,QFormLayout,QComboBox,QPushButton,QLabel,QFileDialog
import layer_finish

def install(owner,parent,Adjustment):
    owner.layer_finish_box=QGroupBox('Parallax layer finishes')
    form=QFormLayout(owner.layer_finish_box);owner.layer_finish_controls={}
    for key in layer_finish.LAYERS:
        box=QGroupBox(key.title());rows=QFormLayout(box)
        finish=QComboBox();finish.addItems(['Normal','Holographic']);rows.addRow('Finish',finish)
        strength=Adjustment('Holographic strength',85,0,100);rows.addRow(strength)
        area=QComboBox();area.addItems(['Light artwork','Whole layer','Mask PNG']);rows.addRow('Area',area)
        button=QPushButton('Choose mask PNG…');rows.addRow(button)
        label=QLabel('No mask selected');label.setWordWrap(True);rows.addRow(label)
        def choose(checked=False,k=key):
            path,_=QFileDialog.getOpenFileName(owner,'Choose '+k+' holographic mask',filter='Mask PNG (*.png)')
            if path:
                owner.current().setdefault('layer_finishes',{}).setdefault(k,{})['mask']=path
                owner.layer_finish_controls[k]['label'].setText(Path(path).name);owner.changed()
        button.clicked.connect(choose)
        def change(*args):
            if not getattr(owner,'loading',False):
                if any(row['finish'].currentIndex() for row in owner.layer_finish_controls.values()):owner.surface_holo.setChecked(False)
                owner.changed()
        finish.currentIndexChanged.connect(change);strength.changed.connect(owner.changed);area.currentIndexChanged.connect(owner.changed)
        form.addRow(box);owner.layer_finish_controls[key]=dict(box=box,finish=finish,strength=strength,area=area,button=button,label=label)
    hint=QLabel('Normal layers keep their artwork colours. Holographic layers use the donor Pearl pattern. Light artwork leaves dark backing alone; a mask PNG follows that layer’s placement. Requires SDEC 3.6.0 or newer. Preview lighting is approximate.')
    hint.setWordWrap(True);form.addRow(hint);parent.addWidget(owner.layer_finish_box)

def remember(owner,deck):
    cfg=layer_finish.settings(deck.get('layer_finishes'))
    for key,row in owner.layer_finish_controls.items():
        cfg[key].update(finish=('normal','holographic')[row['finish'].currentIndex()],strength=row['strength'].value()/100,area=('light','all','mask')[row['area'].currentIndex()])
    deck['layer_finishes']=cfg

def apply(owner,deck):
    cfg=layer_finish.settings(deck.get('layer_finishes'))
    for key,row in owner.layer_finish_controls.items():
        row['finish'].setCurrentIndex(0 if cfg[key]['finish']=='normal' else 1)
        row['strength'].set_value(cfg[key]['strength']*100)
        row['area'].setCurrentIndex(('light','all','mask').index(cfg[key]['area']))
        row['label'].setText(Path(cfg[key]['mask']).name if cfg[key]['mask'] else 'No mask selected')

def update(owner):
    active=owner.current()['mode']=='layers';owner.layer_finish_box.setVisible(active)
    for key,row in owner.layer_finish_controls.items():
        row['box'].setVisible(key!='middle' or bool(owner.current().get('middle_image')))
        on=active and row['finish'].currentIndex()==1 and not owner.busy
        row['finish'].setEnabled(active and not owner.busy);row['strength'].setEnabled(on);row['area'].setEnabled(on)
        row['button'].setVisible(row['area'].currentIndex()==2);row['label'].setVisible(row['area'].currentIndex()==2)
        row['button'].setEnabled(on)
