"""..."""
from module.aligo.core import BaseAligo
from module.aligo.core.Config import V3_FILE_UPDATE
from module.aligo.request import UpdateFileRequest, RenameFileRequest
from module.aligo.types import BaseFile


class Update(BaseAligo):
    """..."""

    def update_file(self, body: UpdateFileRequest) -> BaseFile:
        """
        Update file.
        :param body: [UpdateFileRequest]
        :return: [BaseFile]

        :Example:
        >>> from module.aligo import Aligo
        >>> ali = Aligo()
        >>> new_file = ali.update_file(UpdateFileRequest(file_id='file_id', name='new_name'))
        >>> print(new_file.name)
        """
        response = self.post(V3_FILE_UPDATE, body=body)
        return self._result(response, BaseFile)

    def _core_rename_file(self, body: RenameFileRequest) -> BaseFile:
        """..."""
        return self.update_file(UpdateFileRequest(**body.to_dict()))
