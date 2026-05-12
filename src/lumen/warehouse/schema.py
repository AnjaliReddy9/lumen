from pydantic import BaseModel, Field


class Column(BaseModel):
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool = Field(default=False)


class ForeignKey(BaseModel):
    from_column: str
    to_table: str
    to_column: str


class Table(BaseModel):
    name: str
    schema_name: str | None
    columns: list[Column]
    foreign_keys: list[ForeignKey]


class Schema(BaseModel):
    tables: list[Table]

    def find_table(self, name: str) -> Table | None:
        key = name.casefold()
        for table in self.tables:
            if table.name.casefold() == key:
                return table
        return None
