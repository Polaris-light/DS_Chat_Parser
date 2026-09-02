import re
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QFile, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QWidget, QListWidgetItem, \
    QAbstractItemView
from astroid.nodes import Match

# 导入本地模块
from Workers import JsonParser, ExpKit
from custom_widgets import UiLoader
from ds_type_defs import *

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        # 打包后：可执行文件所在目录
        base_path = Path(sys.executable).parent
    else:
        # 开发环境：main.py 所在目录
        base_path = Path(__file__).parent
    return str(base_path / relative_path)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        ui_path = resource_path("Resources/UI/main.ui")
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        ui_file.close()

        self.ui: QWidget = UiLoader().load(ui_file)
        self.replace_color_widgets: list = [self.ui.FileBox, ]
        self.replace_style_color()  #匹配主题色

        #----------初始化----------
        self.parser_thread: None | JsonParser = None

        self.file_list: list[str] = []
        #禁用 列表项被点击时高亮
        self.ui.session_list.setSelectionMode(QAbstractItemView.NoSelection)
        # 初始禁用的控件
        self.disabled_widget: list[QWidget] = [self.ui.ExportFile_name, ]
        for disa_wid in self.disabled_widget:
            disa_wid.setEnabled(False)
        #初始隐藏的控件
        self.hide_widget: list[QWidget] = [self.ui.session_section, self.ui.parsing_progress, self.ui.setting]
        for hide_wid in self.hide_widget:
            sp = hide_wid.sizePolicy()  # 获取当前大小策略
            sp.setRetainSizeWhenHidden(True)  # 设置隐藏后保留空间
            hide_wid.setSizePolicy(sp)  # 应用新的策略
            hide_wid.hide()
        #初始化控件
        self.ui.ExportFile_path.setText(str(Path.home() / "Desktop"))
        #----------控件信号连接槽----------
        self.ui.parse.clicked.connect(self.parse)
        self.ui.FileBox.clicked.connect(self.choice_file)
        self.ui.FileBox.files_dropped.connect(self.on_files_dropped)
        self.ui.session_list.itemPressed.connect(self.on_sessionlist_item_pressed)  #使点击非复选框区域也能勾选复选框
        self.ui.s_allcheck.clicked.connect(self.on_s_allcheck)
        self.ui.export.clicked.connect(self.export)
        ##-----配置项信号连接-----
        self.ui.Browse.clicked.connect(self.on_browse)
        self.ui.ExportFile_NamingFormat.currentIndexChanged.connect(self.on_naming_format_change)


    #----------线程管理----------
    def start_parser(self, method, par: dict[str, Any]) -> None:
        self.parser_thread = JsonParser(method, par)

        #-----线程信号连接槽-----
        self.parser_thread.s_info.connect(self.list_s_title)
        self.parser_thread.progress.connect(self.on_progress)
        self.parser_thread.tips.connect(self.on_tips)
        self.parser_thread.error.connect(self.on_error)
        self.parser_thread.finished.connect(self.on_finished)
        self.parser_thread.finished.connect(self.parser_thread.deleteLater)

        self.parser_thread.exp_finished.connect(self.on_exp_finished)


        self.parser_thread.start()
    ##-----线程槽-----
    def list_s_title(self, title, session) -> None:
        item = QListWidgetItem(title)
        item.setCheckState(Qt.CheckState.Unchecked)
        self.ui.session_list.addItem(item)
        item.setData(Qt.ItemDataRole.UserRole, session)

    def on_progress(self, progress: int, session_len: int) -> None:
        self.ui.parsing_progress.setRange(0, session_len)
        self.ui.parsing_progress.setValue(progress)

    def on_tips(self, name, msg):
        QMessageBox.information(self, name, msg)

    def on_error(self, name, details) -> None:
        QMessageBox.about(self.ui, name, details)
        self.finished_parser()

    def on_finished(self) -> None:
        self.ui.parse.setEnabled(True)
        self.ui.parsing_progress.hide()
        self.allcheck_str()

    def finished_parser(self) -> None:
        self.ui.parsing_progress.hide()


    def on_exp_finished(self) -> None:
        QMessageBox.about(self.ui, "导出结束", "导出已结束               ")
        self.ui.export.setEnabled(True)  #启用按钮

    #----------方法----------
    def replace_style_color(self) -> None:
        """查找控件的样式表中的特殊颜色并替换为主题色, 如果未找到则跳过"""
        color: str = self.palette().text().color().name()
        #需要设置主题色的控件
        for widget in self.replace_color_widgets:
            old_style = widget.styleSheet()
            new_style = re.sub(r'#cccccc;', color, old_style,flags = re.M | re.DOTALL)
            if new_style == old_style:
                print(f"Control {widget} no color'#cccccc', skipped")
            else:
                widget.setStyleSheet(new_style)#

    def update_filelist(self, file_path: str) -> None:
        """更新待解析文件的列表，并同步显示已添加的文件"""
        #更新列表
        if not file_path.endswith(".json"):
            return
        self.file_list.clear() # 限制最多一个文件
        self.file_list.append(file_path)

        #同步显示
        prt = self.ui.FilelistLabel.setText
        if not self.file_list:
            prt("点击选择文件 或 直接拖入文件")
        else:
            prt("\n".join(self.file_list))

    #----------控件槽----------
    def parse(self) -> None:
        """解析"""
        if len(self.file_list) == 0:
            return
        self.ui.parse.setEnabled(False)
        if not self.ui.session_section.isVisible(): self.ui.session_section.show()  #显示会话列表
        if not self.ui.setting.isVisible(): self.ui.setting.show()  #显示可配置项
        self.ui.session_list.clear()  #清除旧列表
        self.ui.parsing_progress.show()  #显示进度条
        self.ui.parsing_progress.setValue(0)  #重置进度
        self.start_parser('ls',{'file_list':self.file_list})

    def export(self) -> None:
        """执行导出前置，随后启动导出线程"""
        #获取选中的会话
        sessions: list[dict] = [self.ui.session_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.ui.session_list.count())
                 if self.ui.session_list.item(i).checkState() == Qt.CheckState.Checked]
        if not sessions:
            QMessageBox.about(self.ui, "未选中会话", "当前未选中任何会话，请勾选需要导出的会话")
            return

        #获取配置项:是否合并会话
        _merge_sessions_choice: str = self.ui.Merge_sessions.checkedButton().objectName()
        if "0" in _merge_sessions_choice and len(sessions) > 1:
            merge_sessions: bool = False
        else:
            merge_sessions: bool = True

        #获取文件后缀/文件导出格式
        exp_suffix_match: Match = re.search(r"\.([a-zA-z]+)", self.ui.ExportFile_format.currentText())
        if exp_suffix_match:
            file_suffix: str = exp_suffix_match.group(1).lower()
        else:
            file_suffix = "txt"
        exp_path: str = self.ui.ExportFile_path.text()  #获取文件保存路径
        if not (Path(exp_path).exists() and Path(exp_path).is_dir()):
            QMessageBox.about(self.ui, "路径错误", "当前填写的路径不存在,请输入正确的文件路径")
            return
        exp_naming_format = self.ui.ExportFile_NamingFormat.currentText()
        #获取文件名格式或自定义的文件名
        lllegal_character = r'\/:*<>"|'
        if exp_naming_format == "自定义":
            file_name: Union[str, tuple[str]] = self.ui.ExportFile_name.text()
            if not 1 < len(file_name) < 100:
                QMessageBox.about(self.ui, "文件名过短", "文件名长度应该在1~100之间")
                return
        else:
            file_name: Union[str, tuple[str]] = (self.ui.ExportFile_NamingFormat.currentText(), )  #返回元组
        if any(lllegal in file_name for lllegal in lllegal_character):
            QMessageBox.about(self.ui, "文件名不符合规范",  f"文件名不能包含下列任何字符:\n    {lllegal_character}")
            return

        #检查文件路径和文件名是否存在，已存在则提供替换或取消的选择
        agree_replace_file = False
        file_name: str = ExpKit.handle_filename(file_name)
        _file_path = Path(exp_path) / file_name
        if merge_sessions and _file_path.with_suffix(f'.{file_suffix}').is_file():
            reply = QMessageBox.question(self.ui,
                    "文件已存在",
                         f"文件 {file_name} 已存在于路径中，是否替换文件？",
                         QMessageBox.Yes | QMessageBox.No,
                         QMessageBox.No
                    )
            if reply == QMessageBox.No:
                return
            agree_replace_file = True
        elif (not merge_sessions) and _file_path.is_dir():
            reply = QMessageBox.question(self.ui,
                                         "文件夹已存在",
                                         f"文件夹 {file_name} 已存在于路径中，是否替换该文件夹？",
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No
                                         )
            if reply == QMessageBox.No:
                return
            agree_replace_file = True
        #获取需要显示的条目
        display_items: ConfigDisplayItems = ConfigDisplayItems(
            is_AI_search= self.ui.Is_show_AISearch.isChecked(),  #显示AI搜索内容
            is_AI_think= self.ui.Is_show_AIThink.isChecked(),  #显示AI思考内容
            is_User_file= self.ui.Is_show_UserFile.isChecked(),  #显示用户引用的文件信息
            is_msg_time= self.ui.Is_show_MsgTime.isChecked(),  #显示消息的时间戳
        )
        speaker_name:tuple[str,str] = SpeakersName(User= self.ui.user_name.text(), AI= self.ui.ai_name.text())  #获取发言人代称,索引0为User，1为AI
        #获取缩进符
        indent_text_match: Match = re.search(r'^(.*?)(?= ".*")', self.ui.Indent_text.currentText())
        if indent_text_match:
            indent_text: str = indent_text_match.group(1)
        else:
            indent_text = "双空格"

        #启动并传入参数
        self.ui.parsing_progress.show()  #显示进度条
        self.ui.parsing_progress.setValue(0)  #重置进度
        self.ui.export.setEnabled(False)  #禁用按钮
        self.start_parser('exp',{"sessions":sessions,
            "config":ExportConfig(
                file_suffix= file_suffix,
                exp_path= exp_path,
                file_name= file_name,
                merge_sessions= merge_sessions,
                agree_replace_file= agree_replace_file,
                sessions= sessions,
                display_items= display_items,
                speaker_name= speaker_name,
                indent_text= indent_text,
                )
        })


    def choice_file(self) -> None:
        """左击选择文件的信号槽"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择对话文件（json)", "","JSON文件 (*.json);;所有文件 (*.*)"
        )
        if file_path:
            self.update_filelist(file_path)
    def on_files_dropped(self, file_list: list[str]) -> None:
        """拖动文件后的信号槽"""
        for file_path in file_list:
            self.update_filelist(file_path)

    def on_browse(self) -> None:
        """点击浏览按钮的信号槽"""
        exp_path = QFileDialog.getExistingDirectory(
            self, "导出至...", "", options= QFileDialog.ShowDirsOnly
        )
        if exp_path:
            self.ui.ExportFile_path.setText(exp_path)

    def on_sessionlist_item_pressed(self, item: QListWidgetItem) -> None:
        """使点击非勾选框区域也可勾选"""
        new_state = item.checkState()
        new_state = Qt.CheckState.Unchecked if new_state == Qt.CheckState.Checked else Qt.CheckState.Checked
        item.setCheckState(new_state)
        self.allcheck_str()
    def allcheck_str(self) -> None:
        """设置文本为取消全选"""
        items = [self.ui.session_list.item(i) for i in range(self.ui.session_list.count())]
        s_alc = self.ui.s_allcheck
        if any(item.checkState() == Qt.CheckState.Unchecked for item in items):
            if s_alc.text != '全选': s_alc.setText('全选')
        else:
            if s_alc.text != '取消全选': s_alc.setText('取消全选')
    def on_s_allcheck(self) -> None:
        """点击全选按钮"""
        if self.ui.s_allcheck.text() == "全选":
            for i in range(self.ui.session_list.count()):
                self.ui.session_list.item(i).setCheckState(Qt.CheckState.Checked)
        else:
            for i in range(self.ui.session_list.count()):
                self.ui.session_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.allcheck_str()

    def on_naming_format_change(self) -> None:
        wid = self.ui.ExportFile_NamingFormat
        naming_format = wid.currentText()
        if naming_format == "自定义":
            self.ui.ExportFile_name.setEnabled(True)
            return
        else:
            self.ui.ExportFile_name.setEnabled(False)




if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(resource_path("Resources/icon/ds_chat_parser.ico")))
        main = MainWindow()
        main.ui.show()
        if "--sandbox" in sys.argv:
            import sandbox  #进入沙箱环境
        app.exec()
    except Exception as e:
        with open("crash.log", "w") as f:
            f.write(str(e))
        raise