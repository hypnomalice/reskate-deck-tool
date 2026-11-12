"""Author-only controls and attachment picking for the mask spring effect."""
from pathlib import Path
import numpy as np
from PIL import Image
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPainter,QColor,QImage,QPixmap,QPen
from PySide6.QtWidgets import (QGroupBox,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
    QComboBox,QCheckBox,QFileDialog,QDialog,QDialogButtonBox,QWidget,QMessageBox)
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
            painter.drawText(int(px+10),int(py-8),'Top' if i==0 else 'Bottom')
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
    layout.addWidget(QLabel('The green selection can move. Click to place the selected fixed attachment.'))
    picker=PinPicker(image,mask,top,bottom);layout.addWidget(picker);row=QHBoxLayout()
    for index,label in enumerate(('Place top','Place bottom')):
        button=QPushButton(label);button.clicked.connect(lambda checked=False,i=index:setattr(picker,'active',i));row.addWidget(button)
    layout.addLayout(row);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
    if dialog.exec()==QDialog.Accepted:
        if picker.pins[0][1]>=picker.pins[1][1]:QMessageBox.warning(owner,'Attachments','Place the top attachment above the bottom attachment.');return
        d.setdefault('jiggle',{}).update(top_pin=picker.pins[0],bottom_pin=picker.pins[1]);owner.changed()


def install(owner,parent,Adjustment):
    owner.jiggle_box=QGroupBox('Artwork springs');box=QVBoxLayout(owner.jiggle_box)
    owner.jiggle_mask_button=QPushButton('Choose jiggle mask');box.addWidget(owner.jiggle_mask_button)
    def choose():
        path,_=QFileDialog.getOpenFileName(owner,'Choose jiggle mask','','Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if path:owner.current().setdefault('jiggle',{}).update(mask=path,top_pin=None,bottom_pin=None);owner.jiggle_mask_button.setText(Path(path).name);owner.changed()
    owner.jiggle_mask_button.clicked.connect(choose)
    for key,label,value,lo,hi in [('amount','Jiggle amount',65,0,100),('stiffness','Stiffness',50,0,100),('depth_strength','Depth strength',12,0,30),('pin_radius','Attachment radius',28,8,128)]:
        control=Adjustment(label,value,lo,hi);control.changed.connect(owner.changed);setattr(owner,'jiggle_'+key,control);box.addWidget(control)
        if key=='pin_radius':control.spin.setSuffix(' px')
    owner.jiggle_attachment=QComboBox();owner.jiggle_attachment.addItems(['Top attachment','Top and bottom attachments']);owner.jiggle_attachment.currentIndexChanged.connect(owner.changed);box.addWidget(owner.jiggle_attachment)
    owner.jiggle_reverse=QCheckBox('Raised depth (reverse parallax)');owner.jiggle_reverse.setChecked(True);owner.jiggle_reverse.toggled.connect(owner.changed);box.addWidget(owner.jiggle_reverse)
    button=QPushButton('Choose fixed attachment points');button.clicked.connect(lambda:choose_pins(owner));box.addWidget(button)
    hint=QLabel('White mask moves; black stays fixed. Rotate the preview, then release to watch it settle. These settings are saved in the deck; no in-game adjustment is needed.');hint.setWordWrap(True);box.addWidget(hint);parent.addWidget(owner.jiggle_box)


def remember(owner,d):
    if not hasattr(owner,'jiggle_box'):return
    c=dict(d.get('jiggle',{}));c.update(amount=owner.jiggle_amount.value(),stiffness=owner.jiggle_stiffness.value(),depth_strength=owner.jiggle_depth_strength.value()/100,
        pin_radius=owner.jiggle_pin_radius.value(),attachment='both' if owner.jiggle_attachment.currentIndex() else 'top',reverse=owner.jiggle_reverse.isChecked());d['jiggle']=c


def apply(owner,d):
    c=jiggle_effect.settings(d.get('jiggle'))
    for key in ('amount','stiffness','depth_strength','pin_radius'):getattr(owner,'jiggle_'+key).set_value(c[key]*(100 if key=='depth_strength' else 1))
    owner.jiggle_attachment.setCurrentIndex(c['attachment']=='both');owner.jiggle_reverse.setChecked(c['reverse'])
    owner.jiggle_mask_button.setText(Path(c['mask']).name if c['mask'] else 'Choose jiggle mask')
