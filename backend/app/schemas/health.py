from typing import Literal

from pydantic import BaseModel


class Liveness(BaseModel):
    status: Literal["ok"] = "ok"


class Readiness(BaseModel):
    status: Literal["ready", "unavailable"]
    dependencies: dict[str, Literal["ok", "unavailable"]]
