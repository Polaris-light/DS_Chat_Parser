import sys, shutil, re
from datetime import datetime as dtime
from pathlib import Path
from collections.abc import Iterator
from typing import IO, Optional, Union, TYPE_CHECKING

from PySide6.QtCore import Signal

sys.path.append(str(Path(__file__).parent.parent))
from ds_type_defs import *

class ExpKit:
    @staticmethod
    def handle_indent(indent_text: str) -> str:
        """把词义转换为缩进符"""
        match indent_text:
            case "无缩进":
                return ""
            case "双空格":
                return "  "
            case "加号":
                return "+ "
            case "减号":
                return "- "
            case _:
                return "  "
    @staticmethod
    def handle_filename(name: str|tuple[str]) -> str:
        """处理文件名"""
        match name:
            case ("按导出时间"):
                file_name = f"DsSessions_{dtime.now().strftime("%Y%m%d_%H%M%S")}"
            case str():
                file_name = name
            case _:
                file_name = f"DsSessions_{dtime.now().strftime("%Y%m%d_%H%M%S")}"
        file_name = f"{file_name}"
        return file_name

    @staticmethod
    def sessions_precheck(raw_sessions: list[dict], signals: Signals) -> Iterator[DsSessionDict]:
        """执行预检查， 并返回一个迭代器"""
        invalid_session = 0
        for raw_session in raw_sessions:
            try:
                session = PreCheck.session_check(raw_session)
            except ValidationFailedError:
                invalid_session += 1
                continue
            yield session
        if invalid_session > 0:
            signals.tips.emit("文件格式错误", f"所选的会话中包含{invalid_session}个无效的会话，导出时已跳过")
        return
    @staticmethod
    def msg_node(mapping: dict, signals: Signals) -> Iterator[Message]:
        """包含所有可解析节点的迭代器"""
        node_ids = sorted(int(k) for k in mapping.keys() if k.isdigit())
        for node_id in node_ids:
            if signals.stop:
                return
            message = mapping.get(str(node_id))
            if not message:
                continue
            try:
                msg = Message.from_node(node_data=message)
            except FromDataError:
                continue
            yield msg


# noinspection PyShadowingNames
class Formatter:
    @staticmethod
    def export_txt(sessions: list[dict] , config: ExportConfig, signals: tuple[Signal]) -> None:
        indent_text: str = ExpKit.handle_indent(config.indent_text)
        indent_level: int = 0
        def indent() -> str:
            """直接返回当前的缩进层级，省去每次运算"""
            return str(indent_text * indent_level)

        def _export_session(f: IO, session: DsSessionDict) -> None:
            """解析并导出单个会话"""
            nonlocal indent_level
            def speaker(node: Message) -> str:
                """直接返回说话者代称"""
                if node.speaker == "User":
                    return config.speaker_name.User
                elif node.speaker == "AI":
                    return config.speaker_name.AI
                else:
                    return f"未知发言人[{node.speaker}]"
            nodes = ExpKit.msg_node(session.mapping, signals)
            for idx , node in enumerate(nodes):
                signals.progess.emit(idx, len(session.mapping))
                if config.display_items.is_msg_time:  #显示消息的时间戳
                    f.write(f"{indent()}{node.time_stamp}\n")
                f.write(f"{indent()}{speaker(node)}: \n")
                indent_level += 1
                for fragment in node.fragments:  #消息片段
                    if signals.stop:
                        signals.error.emit("中止导出", "已中止导出")
                        return
                    match fragment.type:
                        case "THINK":  #AI的思考内容
                            if not config.display_items.is_AI_think:
                                continue
                            f.write(f"{indent()}思考中: \n")
                            indent_level += 1
                            f.write(f"{indent()}<think>\n{indent()}{fragment.content}\n{indent()}</think>\n\n")
                            indent_level -= 1

                        case "FILE":  #用户引用的文件信息
                            if not config.display_items.is_User_file:
                                continue
                            f.write(f"{indent()}文件: [\n")
                            indent_level += 1
                            for file_info in fragment.files:
                                file_id = file_info.file_id or "未知"
                                file_name = file_info.file_name or "未知"
                                file_size = file_info.file_size or "未知"

                                f.write(f"{indent()}文件id: {file_id} | 文件名: {file_name} | 文件大小: {file_size}\n")
                            indent_level -= 1
                            f.write(f"{indent()}]\n\n")


                        case "REQUEST" | "RESPONSE":  #用户/AI的普通消息
                            f.write(f"{indent()}{fragment.content}\n")

                        case "TOOL_SEARCH" | "SEARCH":  #AI搜索资料
                            if not config.display_items.is_AI_search:
                                continue
                            f.write(f"{indent()}搜索资料: \n")
                            indent_level += 1
                            for found_info in fragment.results:
                                if found_info.url is not None and found_info.title is not None:
                                    f.write(f"{indent()}{found_info.title}: {found_info.url}\n")
                            indent_level -= 1
                indent_level -= 1
                f.write(f"\n")

        exp_path = Path(config.exp_path) / config.file_name
        if config.merge_sessions:  #合并会话, 即所有会话放在一个文件里
            if exp_path.with_suffix(f'.{config.file_suffix}').is_file() and not config.agree_replace_file:
                raise RuntimeError(f"文件夹已存在且未获得覆盖授权: {exp_path}")

            with open(Path(config.exp_path) / f"{config.file_name}.{config.file_suffix}",
                      "w", encoding="utf-8") as f:
                for session in ExpKit.sessions_precheck(sessions, signals):
                    if len(sessions) > 1:
                        f.write(f"\n\n\n{indent()}会话 {session.title}: \n\n\n")
                        indent_level += 1
                    _export_session(f=f, session=session)
                    indent_level = 0

        else:  #不合并会话，即每个会话为一个文件
            if exp_path.is_dir():  #如果文件夹已存在则进行删除
                if not config.agree_replace_file:
                    raise RuntimeError(f"文件夹已存在且未获得覆盖授权: {exp_path}")
                shutil.rmtree(exp_path)

            exp_path.mkdir(parents=True, exist_ok=True)
            for session in ExpKit.sessions_precheck(sessions, config):
                file_title = re.sub(r'[\\/*?:"<>|]', '_', session.title)
                file_name = f"{config.file_name}[{file_title}].{config.file_suffix}"
                with open(exp_path / file_name, "w", encoding="utf-8") as f:
                    _export_session(f=f, session=session)
                    indent_level = 0
        signals.exp_finished.emit()

    @staticmethod
    def export_json(sessions, config, signals) -> None:
        pass  #待定

    @staticmethod
    def export_md(sessions, config, signals) -> None:
        pass  #待定