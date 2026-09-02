import json,sys
from typing import Any, Union
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from dataclasses import dataclass
from pydantic import BaseModel

from ds_type_defs import *
from .exporters import Formatter

#JSON解析线程
class JsonParser(QThread):
    #共有信号
    error = Signal(str, str)
    progress = Signal(int, int)  #当前索引，总数
    tips = Signal(str, str)
    #解析信号
    s_info = Signal(str, dict)
    finished = Signal()
    #导出信号
    exp_finished = Signal()

    TYPE_NAME: dict = {"FILE":"文件", "THINK":"思考", "TOOL_SEARCH":"搜索资料", "SEARCH":"搜索资料" }

    def __init__(self, method,par: dict[str, Any]) -> None:
        super().__init__()
        self.par: dict = par
        self.method: str = method
        self.stop: bool = False


    def stop_thread(self) -> None:
        self.stop = True

    def run(self) -> None:
        """任务分发"""
        if self.method == 'ls':
            self.list_session()
        elif self.method == 'exp':
            sessions: list[dict] | None = self.par.get('sessions')
            config: ExportConfig | None = self.par.get('config')
            # self.error.emit("测试中", "导出函数已停用")
            if sessions is not None and config is not None:
                self.export(sessions, config)


    def list_session(self) -> None:
        """列出文件内包含的会话并存入列表项"""
        try:
            with open(self.par["file_list"][0],'r' , encoding="utf-8") as f:
                try:
                    data = PreCheck.file_check(f)
                except ValidationFailedError as e:
                    self.error.emit("文件错误", str(e))
                    return
                session_len = len(data)
                progress = 0
                for raw_session in data:
                    if self.stop:
                        self.error.emit("中断任务", "已取消解析")
                        return
                    try:
                        session: DsSessionDict =  PreCheck.session_check(raw_session)  #校验
                    except ValidationFailedError:
                        self.error.emit("文件格式错误", "文件内容不符合规范，请确认是官方的会话导出文件")
                        return
                    progress += 1
                    s_title = session.title
                    self.s_info.emit(f'{s_title}', session.model_dump())
                    self.progress.emit(progress, session_len)
                self.finished.emit()
        except FileNotFoundError:
                self.error.emit("路径不存在", f"{self.par['file_list'][0]}  文件不存在或被移动，请检查路径是否正确")
                return

    def export(self, sessions: list[dict], config: ExportConfig) -> None:
        """-----检查导出格式，分发任务-----"""
        signals:Signals = Signals(error= self.error,
                                  stop= self.stop,
                                  progess= self.progress,
                                  tips= self.tips,
                                  exp_finished= self.exp_finished)  #打包所需信号
        #检查后缀以执行不同的导出
        match config.file_suffix:
            case "txt":
                Formatter.export_txt(sessions, config, signals)
            case _:  #临时占位
                Formatter.export_txt(sessions, config, signals)
            # case "json":
            #     Formatter.export_json(sessions, config, signals)
            # case "md":
            #     Formatter.export_md(sessions, config, signals)