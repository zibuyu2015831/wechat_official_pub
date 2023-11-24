"""..."""
from dataclasses import dataclass

from module.aligo.types import DatClass


@dataclass
class MoveFileToTrashRequest(DatClass):
    """..."""
    file_id: str
    drive_id: str = None
