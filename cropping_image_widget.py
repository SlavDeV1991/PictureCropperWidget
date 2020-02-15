import sys

from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2.QtCore import Signal
from PySide2.QtCore import QRectF
from PySide2.QtCore import QLineF
from PySide2.QtCore import QObject
from PySide2.QtGui import QPalette
from PySide2.QtGui import QColor
from PySide2.QtGui import QPixmap
from PySide2.QtGui import QImage
from PySide2.QtWidgets import QGraphicsView
from PySide2.QtWidgets import QGraphicsScene
from PySide2.QtWidgets import QGraphicsItem
from PySide2.QtWidgets import QGraphicsPixmapItem
from PySide2.QtWidgets import QGridLayout

DARK_THEME = True


class CroppingLineGraphicsItem(QGraphicsItem):
    """
    Linia pozwalajaca kadrowac/wycinac obraz
    """
    MAX_MIN_OFFSET = 10

    class ChangedPosSignal(QObject):
        changed_pos_sig = Signal(int)

        def __init__(self):
            super(CroppingLineGraphicsItem.ChangedPosSignal, self).__init__()

    def __init__(self, pos, start, length, min_pos, max_pos, vertical=False, parent=None):
        super(CroppingLineGraphicsItem, self).__init__(parent)
        self.changed_pos_sig = CroppingLineGraphicsItem.ChangedPosSignal()
        self._width = 10
        self._vertical = vertical
        self._start = start
        self._length = length
        self._min = 0
        self._max = 0
        self._bounding_rect = None
        self._line = None
        self._pen_width = 3
        self.set_max(max_pos)
        self.set_min(min_pos)
        self._set_pos(pos)
        self._set_line_and_border()
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)

    def set_max(self, max_pos):
        self._max = max_pos - self.MAX_MIN_OFFSET

    def set_min(self, min_pos):
        self._min = min_pos + self.MAX_MIN_OFFSET

    def _set_line_and_border(self):
        if self._vertical:
            self._bounding_rect = QRectF(-self._width/2, self._start, self._width, self._length)
            self._line = QLineF(0, self._start, 0, self._start + self._length)
        else:
            self._bounding_rect = QRectF(self._start, -self._width/2, self._length, self._width)
            self._line = QLineF(self._start, 0, self._start + self._length, 0)

    def _set_pos(self, pos):
        if self._min < pos < self._max:
            self._pos = pos
            self.changed_pos_sig.changed_pos_sig.emit(pos)
            if self._vertical:
                self.setPos(pos, 0)
            else:
                self.setPos(0, pos)

    def boundingRect(self, *args, **kwargs):
        return self._bounding_rect

    def paint(self, painter, option, widget):
        pen = painter.pen()
        pen.setStyle(Qt.DashLine)
        pen.setWidth(self._pen_width)
        painter.setPen(pen)
        painter.setOpacity(0.5)
        painter.drawLine(self._line)

    def mouseMoveEvent(self, event):
        pos = event.scenePos().x() if self._vertical else event.scenePos().y()
        self._set_pos(pos)
        self.update()

    def hoverEnterEvent(self, event):
        self._pen_width = 6
        self.update()

    def hoverLeaveEvent(self, event):
        self._pen_width = 3
        self.update()

    def get_pos(self):
        return self._pos


class CropperGraphicsItem(QGraphicsItem):
    """
    Nakladka na zdjecie obrazujaca kadrowanie kamery - po polsku
    """
    def __init__(self, cam_item, left, right, top, bottom, parent=None):
        super(CropperGraphicsItem, self).__init__(parent)
        self._cam_item = cam_item
        self._top = top
        self._bottom = bottom
        self._left = left
        self._right = right
        self.setPos(cam_item.pos().x(), cam_item.pos().y())
        self._bounding_rect = cam_item.boundingRect()

    def boundingRect(self):
        return self._bounding_rect

    def paint(self, painter, option, widget):
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.black)
        painter.setOpacity(0.5)
        painter.drawRect(0, 0, self._left, self.boundingRect().height())
        painter.drawRect(self._right, 0, self.boundingRect().width()-self._right,
                         self.boundingRect().height())
        painter.drawRect(self._left, 0, self._right - self._left, self._top)
        painter.drawRect(self._left, self._bottom,
                         self._right - self._left,
                         self._bounding_rect.height()-self._bottom)

    def on_top_changed(self, top):
        self._top = top

    def on_bottom_changed(self, bottom):
        self._bottom = bottom

    def on_left_changed(self, left):
        self._left = left

    def on_right_changed(self, right):
        self._right = right


class CroppingImageWidget(QtWidgets.QWidget):

    def __init__(self, cam_item, parent=None):
        super(CroppingImageWidget, self).__init__(parent)
        self._set_layout()
        self._camera_item = cam_item
        if DARK_THEME:
            self._set_dark_theme()
        self._create_items(cam_item)
        self.scene.setSceneRect(cam_item.boundingRect())

    def _create_items(self, cam_item):
        l = 0.2*cam_item.boundingRect().width()
        r = 0.8*cam_item.boundingRect().width()
        t = 0.2*cam_item.boundingRect().height()
        b = 0.8*cam_item.boundingRect().height()
        cropper = CropperGraphicsItem(cam_item, l, r, t, b)
        offset = 1000
        self.line_left = CroppingLineGraphicsItem(l, -offset, cam_item.boundingRect().height()+2*offset, 0,
                                                  r, vertical=True)
        self.line_right = CroppingLineGraphicsItem(r, -offset, cam_item.boundingRect().height()+2*offset, l,
                                                   cam_item.boundingRect().width(), vertical=True)
        self.line_top = CroppingLineGraphicsItem(t, -offset, cam_item.boundingRect().width()+2*offset, 0, b)
        self.line_bottom = CroppingLineGraphicsItem(b, -offset, cam_item.boundingRect().width()+2*offset,
                                                    t, cam_item.boundingRect().height())
        self.line_left.changed_pos_sig.changed_pos_sig.connect(cropper.on_left_changed)
        self.line_right.changed_pos_sig.changed_pos_sig.connect(cropper.on_right_changed)
        self.line_top.changed_pos_sig.changed_pos_sig.connect(cropper.on_top_changed)
        self.line_bottom.changed_pos_sig.changed_pos_sig.connect(cropper.on_bottom_changed)
        for line in [self.line_left, self.line_right, self.line_top, self.line_bottom]:
            line.changed_pos_sig.changed_pos_sig.connect(self.scene.update)
        for item in [cam_item, cropper, self.line_left, self.line_right, self.line_top, self.line_bottom]:
            self.scene.addItem(item)
        self.line_left.changed_pos_sig.changed_pos_sig.connect(self.line_right.set_min)
        self.line_right.changed_pos_sig.changed_pos_sig.connect(self.line_left.set_max)
        self.line_top.changed_pos_sig.changed_pos_sig.connect(self.line_bottom.set_min)
        self.line_bottom.changed_pos_sig.changed_pos_sig.connect(self.line_top.set_max)

    def resizeEvent(self, event):
        """
        ResiczeEvent do nadpisania w qgraphicsView
        """
        self.graphics_view.fitInView(self._camera_item.boundingRect(), Qt.KeepAspectRatio)
        QGraphicsView.resizeEvent(self.graphics_view, event)

    def _set_layout(self):
        """
        tworzy layout okna i tyle
        """
        self.layout = QGridLayout()
        self.scene = QGraphicsScene(self)
        self.graphics_view = QGraphicsView(self)
        self.graphics_view.setScene(self.scene)
        self.graphics_view.show()
        self.layout.addWidget(self.graphics_view, 0, 0)
        self.setLayout(self.layout)
        self.graphics_view.resizeEvent = self.resizeEvent

    def _set_dark_theme(self):
        """
        ustawia piekny ciemny motyw
        """
        qApp = QtWidgets.qApp
        qApp.setStyle("Fusion")
        default_font = QtWidgets.qApp.font()
        default_font.setPointSize(default_font.pointSize() + 2)
        qApp.setFont(default_font)
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        qApp.setPalette(dark_palette)
        qApp.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")

    def get_border(self):
        """
        zwraca zaznaczony/skrojony prostokat
        """
        return (self.line_left.get_pos(),
                self.line_right.get_pos(),
                self.line_top.get_pos(),
                self.line_bottom.get_pos())


def main():
    app = QtWidgets.QApplication(sys.argv)
    image = QImage("wallpaper.jpg")
    item = QGraphicsPixmapItem(QPixmap.fromImage(image))
    main_window = CroppingImageWidget(item)
    main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
