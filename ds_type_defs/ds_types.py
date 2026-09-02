import os
import sys
from pathlib import Path
from typing import IO, Optional, NamedTuple
from dataclasses import dataclass

import pydantic
from pydantic_core import ErrorDetails
from pydantic import BaseModel, Field
import json, types

"""
定义ds_chat_parser的不同类型的定义
"""

#文件内容校验类
class DsSearchResultsDict(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
class DsFileInfoDict(BaseModel):
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
class DsFragmentDict(BaseModel):
    type: str
    content: Optional[str] = None
    files: Optional[list[DsFileInfoDict]] = None
    results: Optional[list[DsSearchResultsDict]] = None
class DsMessageDict(BaseModel):
    model: str
    inserted_at: str
    fragments: list[DsFragmentDict]
class DsNodeDict(BaseModel):
    id: str
    parent: str | None
    children: list[str]
    message: DsMessageDict | None
class DsSessionDict(BaseModel):
    id: str
    title: str
    inserted_at: str
    updated_at: str
    mapping: dict[str, DsNodeDict]

#异常类
class ValidationFailedError(Exception):
    def __init__(self, message: str, errors: Optional[list[ErrorDetails]] = None) -> None:
        super().__init__(message)
        self.errors = errors
class FromDataError(Exception):
    def __init__(self, message):
        self.message = message

#定义解析数据类
@dataclass
class Fragment:
    type: str
    content: str | None = None
    files: list[DsFileInfoDict] | None = None
    results: list[DsSearchResultsDict] | None = None

    @classmethod
    def from_json(cls, data: DsFragmentDict):
        type_ = data.type
        if type_ in ("REQUEST", "RESPONSE", "THINK") and not data.content is None:
            return cls(type=type_, content=data.content)
        elif type_ == "FILE" and not data.files is None:
            return cls(type=type_, files=data.files)
        elif type_ in ("TOOL_SEARCH", "SEARCH") and not data.results is None:
            return cls(type=type_, results=data.results)
        else:
            return cls(type=type_)
@dataclass
class Message:
    node_id: str
    model: str
    time_stamp: str
    speaker: str
    fragments: list[Fragment]

    @classmethod
    def from_node(cls, node_data: DsNodeDict):
        node_id_ = node_data.id
        if node_data.message is None:
            raise FromDataError("Cannot get 'message' data")
        model_ = node_data.message.model
        time_stamp_ = node_data.message.inserted_at
        fragments_ = [Fragment.from_json(f) for f in node_data.message.fragments]
        speaker_ = "User" if any(f.type in ('REQUEST', 'FILE') for f in fragments_) else "AI"
        return cls(
            node_id=node_id_,
            model = model_,
            time_stamp = time_stamp_,
            speaker = speaker_,
            fragments = fragments_
        )

#文件格式预检查方法
class PreCheck:
    @staticmethod
    def file_check(file: IO) -> list[dict]:
        """进行文件检查，返回已解析的数据"""
        if not file.name.endswith('.json'):
            raise ValidationFailedError("文件校验失败: The file extension is not .json.")
        if not file.read(1) == '[':
            raise ValidationFailedError("文件校验失败: This file should be an array.")

        file.seek(0)
        try:
            file_content: list[dict] = json.load(file)
        except json.decoder.JSONDecodeError:
            raise ValidationFailedError("文件校验失败: The file cannot be parsed as JSON.")

        if not (isinstance(file_content, list) and len(file_content) > 0 and
                all(isinstance(item, dict) for item in file_content)):
            raise ValidationFailedError("文件校验失败: This file should be an array composed of objects.")

        return file_content

    @staticmethod
    def session_check(data: dict) -> DsSessionDict:
        try:
            validated = DsSessionDict(**data)
        except pydantic.ValidationError as e:
            raise ValidationFailedError("会话校验失败", e.errors())
        return validated

#配置项的数据字典格式
class SpeakersName(NamedTuple):
    """存储发言人代称的元组格式"""
    User: str
    AI: str
@dataclass
class ConfigDisplayItems:
    """存储配置的消息显示项的容器格式"""
    is_AI_search: bool
    is_AI_think: bool
    is_User_file: bool
    is_msg_time: bool
@dataclass
class ExportConfig:
    file_suffix: str
    exp_path: str
    file_name: str
    merge_sessions: bool
    agree_replace_file: bool
    sessions: list[DsSessionDict]
    sessions: list[DsSessionDict]
    display_items: ConfigDisplayItems
    speaker_name: SpeakersName  #键User为用户代称，键AI为AI代称
    indent_text: str
#打包信号的容器
class Signals:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)