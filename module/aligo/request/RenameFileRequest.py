"""..."""
from dataclasses import dataclass

from module.aligo.types import DatClass
from module.aligo.types.Enum import CheckNameMode


@dataclass
class RenameFileRequest(DatClass):
    """..."""
    name: str
    file_id: str
    check_name_mode: CheckNameMode = 'refuse'
    drive_id: str = None
