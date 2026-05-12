from typing import Any, Protocol, runtime_checkable

from lumen.warehouse.schema import Schema


@runtime_checkable
class Warehouse(Protocol):
    def introspect(self) -> Schema: ...

    def execute(self, sql: str) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...
