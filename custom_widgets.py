from PySide6.QtCore import Signal, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QGroupBox


class UiLoader(QUiLoader):  #自定义QUiLoader类，实现自定义部件自动注册
    def __init__(self):
        super().__init__()
        self.registerCustomWidget(AddFileBox)



class AddFileBox(QGroupBox):  #可拖拽/单击以添加文件的GroupBox
    clicked = Signal()
    files_dropped = Signal(list)

    def __init__(self, title = '', parent=None):
        super().__init__(title,parent)
        self.setAcceptDrops(True)

    #左击选择文件
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    #拖动添加文件
    def dragEnterEvent(self, event):
        """检查拖拽的数据是否为文件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    def dropEvent(self, event):
        """接受拖拽的数据"""
        urls = event.mimeData().urls()
        if urls:
            file_path = [url.toLocalFile() for url in urls]
            self.files_dropped.emit(file_path)
        event.acceptProposedAction()