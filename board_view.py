"""Lightweight Qt 3D template view; no GPU/game assets are required."""
import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF, QTransform
from board_preview import surface


def draw_3d(painter, widget):
    yaw, pitch = map(math.radians, (widget.yaw, widget.pitch))
    def point(u, v, underside=0):
        x, y, z = surface(u, v)
        z += underside
        x, z = x*math.cos(yaw)+z*math.sin(yaw), -x*math.sin(yaw)+z*math.cos(yaw)
        y, z = y*math.cos(pitch)-z*math.sin(pitch), y*math.sin(pitch)+z*math.cos(pitch)
        scale = min((widget.height()-62)/4.5, (widget.width()-52)/2.2)
        perspective = 5.5/(5.5+z)
        return QPointF(widget.width()/2+x*scale*perspective,
                       widget.height()/2+y*scale*perspective)
    # A procedural surface with curved nose/tail and concave rails. Texture
    # coordinates use the same calibrated frame as the flat board view.
    rows, columns = 48, 6
    quads = []
    for j in range(rows):
        for i in range(columns):
            u0,u1,v0,v1=i/columns,(i+1)/columns,j/rows,(j+1)/rows
            points=[point(u0,v0),point(u1,v0),point(u1,v1),point(u0,v1)]
            quads.append((QPolygonF(points),u0,u1,v0,v1))
    outline = QPolygonF([point(0,j/rows) for j in range(rows+1)] +
                        [point(1,j/rows) for j in range(rows,-1,-1)])
    painter.setBrush(QColor(widget.wood))
    painter.setPen(QPen(QColor(widget.wood),4))
    painter.drawPolygon(outline)
    if widget.frame is not None:
        # Adjacent clipped patches share exact edges. Antialiased clip coverage
        # would expose the wood beneath as a visible grid between the patches.
        painter.setRenderHint(QPainter.Antialiasing,False)
        for polygon,u0,u1,v0,v1 in quads:
            source=QRectF(u0*widget.frame.width(),v0*widget.frame.height(),
                          (u1-u0)*widget.frame.width(),(v1-v0)*widget.frame.height())
            corners=QPolygonF([source.topLeft(),source.topRight(),source.bottomRight(),source.bottomLeft()])
            transform=QTransform()
            if not QTransform.quadToQuad(corners,polygon,transform):
                continue
            painter.save()
            clip=QPainterPath();clip.addPolygon(polygon)
            stroke=QPainterPathStroker();stroke.setWidth(.65)
            painter.setClipPath(clip.united(stroke.createStroke(clip)))
            painter.setTransform(transform,True)
            full=QRectF(widget.frame.rect())
            painter.drawPixmap(full,widget.frame,full)
            painter.restore()
        painter.setRenderHint(QPainter.Antialiasing,True)
    if widget.guides:
        painter.setPen(QPen(QColor('#bec8d1'),1,Qt.DashLine))
        for v in (.225,.775):
            painter.drawLine(point(.22,v),point(.78,v))
            for u in (.36,.64):
                for offset in (-.017,.017):
                    painter.drawEllipse(point(u,v+offset),2,2)
    painter.setPen(QColor('#aeb7c1'))
    painter.drawText(QRectF(10,widget.height()-29,widget.width()-20,22),Qt.AlignCenter,
                     'Drag to orbit · Standard deck template')
