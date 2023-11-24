"""..."""
from dataclasses import dataclass

from module.aligo.types import DatClass
from module.aligo.types.Enum import CheckNameMode, BaseFileType


@dataclass
class CreateFolderRequest(DatClass):
    """..."""
    name: str
    parent_file_id: str = 'root'
    drive_id: str = None
    check_name_mode: CheckNameMode = 'auto_rename'
    type: BaseFileType = None

    def __post_init__(self):
        self.type: BaseFileType = 'folder'
        super().__post_init__()
