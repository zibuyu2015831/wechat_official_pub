"""..."""
from dataclasses import dataclass, field
from typing import List

from module.aligo.types import DatClass, BaseFile


@dataclass
class ListToCleanResponse(DatClass):
    """..."""
    items: List[BaseFile] = field(default_factory=list)
    next_marker: str = ''