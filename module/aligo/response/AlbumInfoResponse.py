"""..."""
from dataclasses import dataclass

from module.aligo.types import DatClass


@dataclass
class AlbumInfoResponse(DatClass):
    """..."""
    driveId: str = None
    driveName: str = None
