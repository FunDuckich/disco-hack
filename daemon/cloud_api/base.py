from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class BaseCloudClient(ABC):
    """Базовый класс для всех облачных коннекторов"""

    @abstractmethod
    def get_metadata(self, path: str) -> List[Dict]:
        """
        Возвращает содержимое папки или инфу о файле.
        Ожидаемый формат ответа (единый для всех облаков):
        [
            {
                "name": "photo.jpg",
                "is_dir": False,
                "size": 102450,
                "etag": "ab123456789", # или revision для Яндекса
                "path": "disk:/MyFolder/photo.jpg"
            },
            ...
        ]
        """
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Скачивает файл из облака в локальный кэш (~/.cache/...)"""
        pass

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Загружает файл из кэша в облако"""
        pass