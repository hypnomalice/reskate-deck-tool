"""Author-only controls and attachment picking for the mask spring effect."""
from pathlib import Path
import numpy as np
from PIL import Image
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPainter,QColor,QImage,QPixmap,QPen
from PySide6.QtWidgets import (QGroupBox,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QComboBox,QCheckBox,QToolButton,QFileDialog,QDialog,QDialogButtonBox,QWidget,QMessageBox)
import jiggle_effect


class PinPicker(QWidget):
    def __init__(self,image,mask,top,bottom):
        super().__init__();self.setMinimumSize(300,640);self.active=0;self.pins=[list(top),list(bottom)]
        rgba=np.asarray(image.convert('RGBA')).copy();m=np.asarray(mask.convert('L'))/255.
        rgba[:,:,1]=np.uint8(rgba[:,:,1]*(1-m*.35)+m*255*.35)
        h,w=rgba.shape[:2];self.pixmap=QPixmap.fromImage(QImage(rgba.data,w,h,w*4,QImage.Format_RGBA8888).copy())
        self.rect_image=QRectF()
    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),QColor('#202326'))
        scale=min(self.width()/512,self.height()/2048);w,h=512*scale,2048*scale
        self.rect_image=QRectF((self.width()-w)/2,(self.height()-h)/2,w,h)
        painter.drawPixmap(self.rect_image,self.pixmap,QRectF(self.pixmap.rect()))
        for i,(x,y) in enumerate(self.pins):
            px=self.rect_image.left()+x*w;py=self.rect_image.top()+y*h
            painter.setPen(QPen(QColor('#2de2e6' if i==0 else '#ffc857'),2));painter.drawEllipse(QRectF(px-7,py-7,14,14))
            painter.drawText(int(px+10),int(py-8),'First' if i==0 else 'Second')
    def mousePressEvent(self,event):
        p=event.position();r=self.rect_image
        if r.contains(p):self.pins[self.active]=[(p.x()-r.left())/r.width(),(p.y()-r.top())/r.height()];self.update()


def choose_pins(owner):
    import image_placement
    try:
        owner.remember();d=owner.current();c=jiggle_effect.settings(d.get('jiggle'))
        image=image_placement.frame(d['images'][0],d['fit'],d['background'],d['placement'][0])
        mask=jiggle_effect.mask_image(c,d['fit'],d['placement'][0]);top,bottom,_=jiggle_effect.resolved_pins(c,mask)
    except Exception as exc:QMessageBox.warning(owner,'Attachments',str(exc));return
    dialog=QDialog(owner);dialog.setWindowTitle('Choose fixed attachments');layout=QVBoxLayout(dialog)
    layout.addWidget(QLabel('Place the first attachment at the root and the second toward the opposite edge. Any direction works.'))
    picker=PinPicker(image,mask,top,bottom);layout.addWidget(picker);row=QHBoxLayout()
    for index,label in enumerate(('Place first','Place second')):
        button=QPushButton(label);button.clicked.connect(lambda checked=False,i=index:setattr(picker,'active',i));row.addWidget(button)
    layout.addLayout(row);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
    if dialog.exec()==QDialog.Accepted:
        if np.hypot((picker.pins[1][0]-picker.pins[0][0])*512,(picker.pins[1][1]-picker.pins[0][1])*2048)<2:QMessageBox.warning(owner,'Attachments','Place the attachment points at least two pixels apart.');return
        d.setdefault('jiggle',{}).update(top_pin=picker.pins[0],bottom_pin=picker.pins[1]);owner.changed()


def install(owner,parent,Adjustment):
    owner.jiggle_box=QGroupBox('Artwork springs');box=QVBoxLayout(owner.jiggle_box);owner.spring_layer_buttons={}
    def hint(parent,text):
        label=QLabel(text);label.setWordWrap(True);parent.addWidget(label)
    def fold(parent,title):
        toggle=QToolButton();toggle.setText(title);toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);toggle.setCheckable(True);toggle.setArrowType(Qt.RightArrow);parent.addWidget(toggle)
        body=QWidget();layout=QVBoxLayout(body);layout.setContentsMargins(12,0,0,8);parent.addWidget(body);body.hide()
        def change(value):body.setVisible(value);toggle.setArrowType(Qt.DownArrow if value else Qt.RightArrow)
        toggle.toggled.connect(change);return layout
    def picker(parent,key,label,empty='Choose…'):
        if label:parent.addWidget(QLabel(label))
        row=QHBoxLayout();pick=QPushButton(empty);clear=QPushButton('Clear');row.addWidget(pick,1);row.addWidget(clear);parent.addLayout(row);owner.spring_layer_buttons[key]=(pick,empty)
        def select(checked=False):
            path,_=QFileDialog.getOpenFileName(owner,label or empty,'','Images (*.png *.jpg *.jpeg *.webp *.bmp)')
            if path:owner.current().setdefault('jiggle',{})[key]=path;pick.setText(Path(path).name);owner.changed()
        def remove(checked=False):owner.current().setdefault('jiggle',{})[key]=None;pick.setText(empty);owner.changed()
        pick.clicked.connect(select);clear.clicked.connect(remove)
    moving=QGroupBox('1. What moves?');controls=QVBoxLayout(moving);box.addWidget(moving)
    owner.jiggle_mask_button=QPushButton('Choose jiggle mask');controls.addWidget(owner.jiggle_mask_button)
    def choose():
        path,_=QFileDialog.getOpenFileName(owner,'Choose jiggle mask','','Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if path:owner.current().setdefault('jiggle',{}).update(mask=path,top_pin=None,bottom_pin=None);owner.jiggle_mask_button.setText(Path(path).name);owner.changed()
    owner.jiggle_mask_button.clicked.connect(choose)
    hint(controls,'White moves; black stays fixed.')
    for key,label in [('amount','Jiggle amount'),('stiffness','Stiffness')]:
        control=Adjustment(label,65 if key=='amount' else 50,0,100);control.changed.connect(owner.changed);setattr(owner,'jiggle_'+key,control);controls.addWidget(control)
    owner.jiggle_attachment=QComboBox();owner.jiggle_attachment.addItems(['First attachment','Both attachments']);owner.jiggle_attachment.currentIndexChanged.connect(owner.changed);controls.addWidget(owner.jiggle_attachment)
    button=QPushButton('Choose fixed attachment points');button.clicked.connect(lambda:choose_pins(owner));controls.addWidget(button)
    front=QGroupBox('2. What stays in front? · optional');layout=QVBoxLayout(front);box.addWidget(front)
    picker(layout,'foreground_mask',None,'Choose arm / foreground mask')
    hint(layout,'Keep an arm, hand or other area still, above the moving artwork.')
    back=QGroupBox('3. What appears underneath? · optional');layout=QVBoxLayout(back);box.addWidget(back)
    picker(layout,'background_image',None,'Choose clean background image')
    hint(layout,'Revealed when the artwork moves. Uses your jiggle mask as the cutout.')
    advanced=fold(box,'Advanced')
    for key,label,value,lo,hi in [('depth_strength','Depth strength',12,0,30),('pin_radius','Attachment radius',28,8,128)]:
        control=Adjustment(label,value,lo,hi);control.changed.connect(owner.changed);setattr(owner,'jiggle_'+key,control);advanced.addWidget(control)
        if key=='pin_radius':control.spin.setSuffix(' px')
    owner.jiggle_reverse=QCheckBox('Raised depth (reverse parallax)');owner.jiggle_reverse.setChecked(True);owner.jiggle_reverse.toggled.connect(owner.changed);advanced.addWidget(owner.jiggle_reverse)
    picker(advanced,'cutout_mask','Separate cutout mask','Use jiggle mask')
    picker(advanced,'moving_image','Clean moving artwork','Use base artwork')
    picker(advanced,'foreground_image','Foreground image','Use base artwork')
    picker(advanced,'foreground_depth','Foreground depth','Use artwork depth')
    picker(advanced,'background_depth','Background depth','Flat background')
    hint(advanced,'Clean moving artwork supplies pixels hidden behind the fixed foreground. Masks cannot recreate hidden pixels.')
    parent.addWidget(owner.jiggle_box)


def remember(owner,d):
    if not hasattr(owner,'jiggle_box'):return
    c=dict(d.get('jiggle',{}));c.update(amount=owner.jiggle_amount.value(),stiffness=owner.jiggle_stiffness.value(),depth_strength=owner.jiggle_depth_strength.value()/100,
        pin_radius=owner.jiggle_pin_radius.value(),attachment='both' if owner.jiggle_attachment.currentIndex() else 'top',reverse=owner.jiggle_reverse.isChecked());d['jiggle']=c


def apply(owner,d):
    c=jiggle_effect.settings(d.get('jiggle'))
    for key in ('amount','stiffness','depth_strength','pin_radius'):getattr(owner,'jiggle_'+key).set_value(c[key]*(100 if key=='depth_strength' else 1))
    owner.jiggle_attachment.setCurrentIndex(c['attachment']=='both');owner.jiggle_reverse.setChecked(c['reverse'])
    owner.jiggle_mask_button.setText(Path(c['mask']).name if c['mask'] else 'Choose jiggle mask')
    for key,(button,label) in owner.spring_layer_buttons.items():button.setText(Path(c[key]).name if c[key] else label)
