"""..."""
from dataclasses import dataclass

from module.aligo.types import DatClass


@dataclass
class GetDriveRequest(DatClass):
    """..."""
    drive_id: str = None
