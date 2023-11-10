"""兑换福利码响应"""
from dataclasses import dataclass
from typing import Dict

from aligo.types import DatClass


@dataclass
class Result(DatClass):
    """..."""
    message: str = None


@dataclass
class RewardSpaceResponse(DatClass):
    """数据结构, 类型 可能不准确"""
    success: bool = None
    code: str = None
    message: str = None
    totalCount: int = None
    nextToken: str = None
    maxResults: Dict = None
    result: Result = None
    arguments: str = None
