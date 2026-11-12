"""Independent spring clock and a source-space motion inspector."""
import math,time
import numpy as np
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QGroupBox,QVBoxLayout,QHBoxLayout,QLabel,QPushButton
from PySide6.QtGui import QPixmap
import jiggle_physics,jiggle_effect

def install(owner,right):
    box=QGroupBox('Moving area · close-up');layout=QVBoxLayout(box)
    image=QLabel('Choose artwork and a jiggle mask');image.setAlignment(Qt.AlignCenter);image.setMinimumSize(280,210)
    layout.addWidget(image,1);row=QHBoxLayout()
    for text,action in [('Tilt and release',lambda:setattr(owner,'spring_demo',time.monotonic())),('Stop moving',lambda:setattr(owner,'spring_demo',None))]:
        button=QPushButton(text);button.clicked.connect(action);row.addWidget(button)
    layout.addLayout(row)
    label=QLabel('Same movement as the board, enlarged. Drag the board or test a tilt; release and watch it settle.');label.setWordWrap(True);layout.addWidget(label)
    owner.spring_closeup=image;owner.spring_box=box;box.setMaximumWidth(360)
    row=QHBoxLayout();row.addWidget(owner.board,1);row.addWidget(box);right.addLayout(row,1)
    owner.spring_demo=None;owner.spring_clock=time.monotonic();owner.spring_identity=None
    timer=QTimer(owner);timer.setTimerType(Qt.PreciseTimer);timer.setInterval(16)
    timer.timeout.connect(lambda:tick(owner));timer.start();owner.spring_timer=timer

def tick(owner):
    active=owner.current()['mode']=='jiggle';owner.spring_box.setVisible(active)
    now=time.monotonic();dt=now-owner.spring_clock;owner.spring_clock=now
    if not active or not owner.isVisible() or owner.isMinimized():return
    identity=(owner.selected,owner.current()['images'][0])
    if owner.spring_identity!=identity or not hasattr(owner,'jiggle_solver'):
        owner.jiggle_solver=jiggle_physics.Solver();owner.spring_identity=identity
    if owner.spring_demo is not None:
        t=now-owner.spring_demo
        if t<.8:
            owner.preview_orbit_changed(28*math.sin(2*math.pi*t/.8)*math.sin(math.pi*t/.8),12*math.sin(math.pi*t/.8)**2,False)
        else:
            owner.spring_demo=None;owner.preview_orbit_changed(0,0,False)
    c=jiggle_effect.settings(owner.current().get('jiggle'))
    solver=owner.jiggle_solver;solver.strength=c['amount']/100;solver.stiffness=c['stiffness']
    pose=jiggle_physics.preview_pose(owner.board.yaw,owner.board.pitch)
    # Rendering delays must never trigger the runtime's discontinuity reset.
    duration=min(max(dt,.00001),.1);steps=max(1,math.ceil(duration/(1/60)))
    previous=solver.last['rotation'].copy() if solver.last is not None else pose['rotation']
    if np.dot(previous,pose['rotation'])<0:previous=-previous
    for i in range(steps):
        q=previous+(pose['rotation']-previous)*((i+1)/steps);q=q/np.linalg.norm(q)
        solver.step(dict(pose,rotation=q),duration/steps)
    owner.render()

def region(renderer):
    if not hasattr(renderer,'spring_region'):
        y,x=np.where(renderer.pixels[2048:,:,0]>.02)
        if not len(x):return None
        left=max(0,(x.min()-32)/512);right=min(1,(x.max()+33)/512)
        top=max(0,(y.min()-40)/2048);bottom=min(1,(y.max()+41)/2048)
        renderer.spring_region=(left,top,right,bottom)
    return renderer.spring_region

def detail(renderer,angle,pose):
    crop=region(renderer)
    if crop is None:return None
    region_=crop
    aspect=(region_[3]-region_[1])*2048/((region_[2]-region_[0])*512)
    return renderer.render(angle,(288,max(100,min(300,round(288*aspect)))),region_,view_pose=pose)

def present(owner,image):
    if owner.current()['mode']!='jiggle':return
    crop=image.info.get('springs_detail')
    if crop is None:return
    from qt_ui import qt_image
    owner.spring_closeup.setPixmap(QPixmap.fromImage(qt_image(crop)).scaled(owner.spring_closeup.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
