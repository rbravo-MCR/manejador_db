"""Tests for the Legacy DBF Subsystem (Binary Parser, Inspector, Record Counter, Migration)."""

from __future__ import annotations

import os
import sqlite3
import struct
from decimal import Decimal
from typing import Any

import pytest

from backend_ide.domain.schema.enums import NormalizedDataType
from backend_ide.legacy.dbf.inspector import DBFInspector
from backend_ide.legacy.dbf.migration import DBFMigrationOptions, DBFMigrationService
from backend_ide.legacy.dbf.models import DBFFieldType
from backend_ide.legacy.dbf.parser import DBFParser


def create_sample_dbf_file(
    filepath: str,
    records: list[dict[str, Any]],
    deleted_indices: set[int] | None = None,
) -> None:
    """Helper to create a valid binary dBase III DBF file for testing."""
    deleted_indices = deleted_indices or set()
    num_records = len(records)

    fields_meta = [
        (b"ID", b"N", 6, 0),
        (b"NAME", b"C", 20, 0),
        (b"BALANCE", b"N", 10, 2),
        (b"ACTIVE", b"L", 1, 0),
        (b"CREATED", b"D", 8, 0),
    ]

    record_length = 1 + sum(f[2] for f in fields_meta)  # 46
    header_length = 32 + (len(fields_meta) * 32) + 1  # 193

    with open(filepath, "wb") as f:
        # 32-byte header
        header = bytearray(32)
        header[0] = 0x03
        header[1] = 26
        header[2] = 8
        header[3] = 21
        header[4:8] = struct.pack("<I", num_records)
        header[8:10] = struct.pack("<H", header_length)
        header[10:12] = struct.pack("<H", record_length)
        f.write(header)

        # Field Descriptors (32 bytes each)
        for name_bytes, type_byte, length, decimals in fields_meta:
            field_entry = bytearray(32)
            field_entry[0 : len(name_bytes)] = name_bytes
            field_entry[11] = type_byte[0]
            field_entry[16] = length
            field_entry[17] = decimals
            f.write(field_entry)

        # Header terminator
        f.write(b"\x0d")

        # Write Records
        for idx, rec in enumerate(records):
            is_del = idx in deleted_indices
            f.write(b"*" if is_del else b" ")

            id_str = f"{rec['ID']:>6}"[:6].encode("ascii")
            f.write(id_str)

            name_str = f"{rec['NAME']:<20}"[:20].encode("ascii")
            f.write(name_str)

            bal_str = f"{rec['BALANCE']:>10.2f}"[:10].encode("ascii")
            f.write(bal_str)

            act_str = b"T" if rec.get("ACTIVE") else b"F"
            f.write(act_str)

            dt_str = rec.get("CREATED", "20260821").encode("ascii")[:8]
            f.write(dt_str)

        f.write(b"\x1a")


@pytest.fixture
def sample_dbf_directory(tmp_path: os.PathLike) -> str:
    """Fixture that generates a temporary folder with multiple DBF files."""
    folder = str(tmp_path)

    # Table 1: CLIENTES.DBF (3 records, 1 marked as deleted)
    clients_data = [
        {"ID": 101, "NAME": "Acme Corp", "BALANCE": 1500.50, "ACTIVE": True, "CREATED": "20250115"},
        {
            "ID": 102,
            "NAME": "Globex Inc",
            "BALANCE": 340.00,
            "ACTIVE": False,
            "CREATED": "20250220",
        },
        {"ID": 103, "NAME": "Initech LLC", "BALANCE": 0.00, "ACTIVE": True, "CREATED": "20250310"},
    ]
    create_sample_dbf_file(
        os.path.join(folder, "CLIENTES.DBF"),
        clients_data,
        deleted_indices={1},  # Record 102 is marked as deleted
    )

    # Table 2: PRODUCTOS.DBF (2 records, 0 deleted)
    products_data = [
        {
            "ID": 501,
            "NAME": "Laptop Pro 15",
            "BALANCE": 1299.99,
            "ACTIVE": True,
            "CREATED": "20241101",
        },
        {
            "ID": 502,
            "NAME": "Wireless Mouse",
            "BALANCE": 29.50,
            "ACTIVE": True,
            "CREATED": "20241115",
        },
    ]
    create_sample_dbf_file(
        os.path.join(folder, "PRODUCTOS.DBF"),
        products_data,
    )

    return folder


def test_dbf_header_reading(sample_dbf_directory: str):
    """DBFParser must read binary header and field descriptors accurately in O(1)."""
    dbf_path = os.path.join(sample_dbf_directory, "CLIENTES.DBF")
    header = DBFParser.read_header(dbf_path)

    assert header.version == 3
    assert header.record_count == 3
    assert header.record_length == 46
    assert len(header.fields) == 5

    field_names = [f.name for f in header.fields]
    assert field_names == ["ID", "NAME", "BALANCE", "ACTIVE", "CREATED"]

    assert header.fields[0].field_type == DBFFieldType.NUMERIC
    assert header.fields[0].length == 6
    assert header.fields[1].field_type == DBFFieldType.CHARACTER
    assert header.fields[1].length == 20
    assert header.fields[2].field_type == DBFFieldType.NUMERIC
    assert header.fields[2].decimal_count == 2


def test_dbf_record_reading_and_type_conversions(sample_dbf_directory: str):
    """DBFParser must convert DBF fields to typed Python objects and respect deletion flags."""
    dbf_path = os.path.join(sample_dbf_directory, "CLIENTES.DBF")

    # Read active records only
    active_records = DBFParser.read_records(dbf_path, include_deleted=False)
    assert len(active_records) == 2
    assert active_records[0]["ID"] == 101
    assert active_records[0]["NAME"] == "Acme Corp"
    assert active_records[0]["BALANCE"] == Decimal("1500.50")
    assert active_records[0]["ACTIVE"] is True
    assert active_records[0]["CREATED"] == "2025-01-15"

    assert active_records[1]["ID"] == 103
    assert active_records[1]["NAME"] == "Initech LLC"

    # Read all records including deleted
    all_records = DBFParser.read_records(dbf_path, include_deleted=True)
    assert len(all_records) == 3
    assert all_records[1]["ID"] == 102
    assert all_records[1]["_is_deleted"] is True


def test_dbf_active_record_counter(sample_dbf_directory: str):
    """DBFParser.count_active_records must quickly count active and deleted records."""
    dbf_path = os.path.join(sample_dbf_directory, "CLIENTES.DBF")
    active, deleted = DBFParser.count_active_records(dbf_path)
    assert active == 2
    assert deleted == 1


def test_dbf_streaming_batches(sample_dbf_directory: str):
    """DBFParser.stream_batches must yield batches of requested chunk size."""
    dbf_path = os.path.join(sample_dbf_directory, "CLIENTES.DBF")
    batches = list(DBFParser.stream_batches(dbf_path, batch_size=1, include_deleted=True))
    assert len(batches) == 3
    assert batches[0][0]["ID"] == 101


def test_dbf_inspector_directory_summaries(sample_dbf_directory: str):
    """DBFInspector must scan folder and return table summaries with record counts."""
    summaries = DBFInspector.inspect_directory(sample_dbf_directory, scan_deleted=True)
    assert len(summaries) == 2

    table_map = {s.table_name: s for s in summaries}
    assert "CLIENTES" in table_map
    assert "PRODUCTOS" in table_map

    clientes = table_map["CLIENTES"]
    assert clientes.record_count == 3
    assert clientes.active_record_count == 2
    assert clientes.deleted_record_count == 1
    assert clientes.field_count == 5

    productos = table_map["PRODUCTOS"]
    assert productos.record_count == 2
    assert productos.active_record_count == 2
    assert productos.deleted_record_count == 0


def test_dbf_to_universal_database_schema(sample_dbf_directory: str):
    """DBFInspector.to_database_schema must convert DBF directory to Universal Schema Model."""
    schema = DBFInspector.to_database_schema(sample_dbf_directory, sanitize_names=True)
    assert schema.engine_name == "dbf"
    assert len(schema.schemas[0].tables) == 2

    tbl_names = [t.name for t in schema.schemas[0].tables]
    assert "clientes" in tbl_names
    assert "productos" in tbl_names

    clientes_tbl = next(t for t in schema.schemas[0].tables if t.name == "clientes")
    col_names = [c.name for c in clientes_tbl.columns]
    assert col_names == ["id", "name", "balance", "active", "created"]

    col_types = {c.name: c.normalized_type for c in clientes_tbl.columns}
    assert col_types["id"] == NormalizedDataType.INTEGER
    assert col_types["name"] == NormalizedDataType.VARCHAR
    assert col_types["balance"] == NormalizedDataType.DECIMAL
    assert col_types["active"] == NormalizedDataType.BOOLEAN
    assert col_types["created"] == NormalizedDataType.DATE


def test_dbf_migration_to_sqlite(sample_dbf_directory: str, tmp_path: os.PathLike):
    """DBFMigrationService must migrate DBF files to a SQLite database with real data rows."""
    output_sqlite = os.path.join(str(tmp_path), "migrated_db.sqlite")

    results = DBFMigrationService.migrate_directory_to_sqlite_file(
        sample_dbf_directory,
        output_sqlite,
        options=DBFMigrationOptions(
            sanitize_column_names=True,
            include_deleted_records=False,
            add_auto_increment_pk=True,
        ),
    )

    assert len(results) == 2
    assert all(not r.has_error for r in results)

    # Verify SQLite database contains the tables and populated rows
    conn = sqlite3.connect(output_sqlite)
    cursor = conn.cursor()

    # Query clientes
    cursor.execute("SELECT id, name, balance, active, created FROM clientes ORDER BY id;")
    rows = cursor.fetchall()
    assert len(rows) == 2  # 1 deleted row was excluded
    assert rows[0][1] == "Acme Corp"
    assert rows[0][2] == 1500.5
    assert rows[1][1] == "Initech LLC"

    # Query productos
    cursor.execute("SELECT id, name, balance FROM productos ORDER BY id;")
    prod_rows = cursor.fetchall()
    assert len(prod_rows) == 2
    assert prod_rows[0][1] == "Laptop Pro 15"

    conn.close()
