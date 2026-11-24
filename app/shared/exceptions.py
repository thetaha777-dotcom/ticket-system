from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class DomainError(Exception):
    def __init__(self, message: str, code:str | None = None, details: dict[str, Any] | None = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            body["details"] = self.details
        return body

    def represent(self) -> str:
        return f"DomainError(code={self.code}, message={self.message}, details={self.details})"