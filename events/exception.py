from dataclasses import dataclass
from typing import Any, Optional
from requests.exceptions import RequestException

class BaseException(Exception):
    message: str = ''

    def __post_init__(self) -> None:
        self.message = self.message.capitalize()

    def __str__(self) -> str:
        return self.message

@dataclass
class EmptyResponseException(BaseException):
    message: str = 'Empty response from server!'


@dataclass
class InvalidCredentialException(BaseException):
    message: str = 'Wrong username or password!'
