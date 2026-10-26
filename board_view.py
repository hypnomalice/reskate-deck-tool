"""Authored deck geometry with a visible shell; no extracted game mesh."""
from functools import lru_cache
import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF, QTransform
from board_preview import surface, texture_uv, rotate, DECK_THICKNESS, CAMERA_DISTANCE, TRUCK_CENTRES, PLATE_CENTRES, PLATE_WIDTH, PLATE_LENGTH, BOLT_HALF_WIDTH, BOLT_HALF_LENGTH


def draw_3d(painter, widget):
    scale=min((widget.height()-62)/4.5,(widget.width()-52)/2.2)
    @lru_cache(maxsize=None)
    def point(u,v,layer=0):
        x,y,z=surface(u,v)
        x,y,z=rotate(x,y,z+layer*DECK_THICKNESS,widget.yaw,widget.pitch)
        perspective=CAMERA_DISTANCE/(CAMERA_DISTANCE+z)
        return QPointF(widget.width()/2+x*scale*perspective,widget.height()/2+y*scale*perspective),z
    rows,columns=48,6
    plies=7 if scale*DECK_THICKNESS>=10 else 3
    # More samples at the round tips without increasing the number of painted faces.
    steps=[.5-.5*math.cos(math.pi*j/rows) for j in range(rows+1)]
    perimeter=[(0,v) for v in steps]+[(1,v) for v in reversed(steps)]
    faces=[]
    # Seven actual shell layers replace the constant-width painted wood outline.
    for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):
        for ply in range(plies):
            corners=[point(*a,ply/plies),point(*b,ply/plies),point(*b,(ply+1)/plies),point(*a,(ply+1)/plies)]
            faces.append((sum(z for _,z in corners)/4,QPolygonF([q for q,_ in corners]),None,ply))
    for j in range(rows):
        for i in range(columns):
            u0,u1,v0,v1=i/columns,(i+1)/columns,steps[j],steps[j+1]
            coords=[(u0,v0),(u1,v0),(u1,v1),(u0,v1)]
            corners=[point(u,v) for u,v in coords]
            source=QPolygonF([QPointF(texture_uv(u,v)[0]*widget.frame.width(),v*widget.frame.height()) for u,v in coords])
            faces.append((sum(z for _,z in corners)/4,QPolygonF([q for q,_ in corners]),source,None))
    painter.setPen(Qt.NoPen)
    painter.setRenderHint(QPainter.Antialiasing,False)
    for _,polygon,source,ply in sorted(faces,key=lambda f:f[0],reverse=True):
        if source is None:
            colour=QColor(widget.wood);colour=colour.lighter(110) if ply%2==0 else colour.darker(120)
            painter.setBrush(colour);painter.drawPolygon(polygon)
            continue
        transform=QTransform()
        if not QTransform.quadToQuad(source,polygon,transform):continue
        painter.save()
        clip=QPainterPath();clip.addPolygon(polygon)
        stroke=QPainterPathStroker();stroke.setWidth(.5)
        painter.setClipPath(clip.united(stroke.createStroke(clip)))
        painter.setTransform(transform,True)
        full=QRectF(widget.frame.rect());painter.drawPixmap(full,widget.frame,full)
        painter.restore()
    painter.setRenderHint(QPainter.Antialiasing,True)
    if widget.guides:
        painter.setPen(QPen(QColor('#bec8d1'),1,Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        for axle, centre in zip(TRUCK_CENTRES,PLATE_CENTRES):
            corners=[point(.5+dx,centre+dv)[0] for dx,dv in [(-PLATE_WIDTH/2,-PLATE_LENGTH/2),(PLATE_WIDTH/2,-PLATE_LENGTH/2),(PLATE_WIDTH/2,PLATE_LENGTH/2),(-PLATE_WIDTH/2,PLATE_LENGTH/2)]]
            painter.drawPolygon(QPolygonF(corners))
            painter.drawLine(point(.04,axle)[0],point(.96,axle)[0])
            for u in (.5-BOLT_HALF_WIDTH,.5+BOLT_HALF_WIDTH):
                for offset in (-BOLT_HALF_LENGTH,BOLT_HALF_LENGTH):painter.drawEllipse(point(u,centre+offset)[0],2,2)
    painter.setPen(QColor('#aeb7c1'))
    painter.drawText(QRectF(10,widget.height()-29,widget.width()-20,22),Qt.AlignCenter,
                     'Drag to orbit · Calibrated standard deck')
