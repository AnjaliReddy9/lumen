from lumen.warehouse.schema import Column, Schema, Table


def test_find_table_case_insensitive() -> None:
    schema = Schema(
        tables=[
            Table(
                name="Artist",
                schema_name=None,
                columns=[
                    Column(
                        name="ArtistId",
                        data_type="INTEGER",
                        nullable=False,
                        is_primary_key=True,
                    )
                ],
                foreign_keys=[],
            )
        ]
    )
    assert schema.find_table("artist") is not None
    assert schema.find_table("artist") is schema.tables[0]
    assert schema.find_table("missing") is None


def test_find_table_first_match() -> None:
    schema = Schema(
        tables=[
            Table(name="A", schema_name=None, columns=[], foreign_keys=[]),
            Table(name="a", schema_name=None, columns=[], foreign_keys=[]),
        ]
    )
    assert schema.find_table("A") is schema.tables[0]
