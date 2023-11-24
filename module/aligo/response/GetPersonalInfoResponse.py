"""..."""
from dataclasses import dataclass

from module.aligo.types import DatClass, PersonalRightsInfo, PersonalSpaceInfo


@dataclass
class GetPersonalInfoResponse(DatClass):
    """..."""
    personal_rights_info: PersonalRightsInfo = None
    personal_space_info: PersonalSpaceInfo = None
