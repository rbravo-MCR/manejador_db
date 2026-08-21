"""Pure Python Binary DBF Parser and Streamer (dBase III/IV, FoxPro, Clipper)."""

from __future__ import annotations

import datetime
import os
import struct
from collections.abc import Generator
from decimal import Decimal
from typing import Any

from backend_ide.legacy.dbf.models import DBFField, DBFFieldType, DBFHeader


class DBFParser:
    """High-performance binary DBF header and record reader with zero external dependencies."""

    @staticmethod
    def read_header(filepath: str, encoding: str = "cp1252") -> DBFHeader:
        """Parse binary DBF header and field descriptor table in O(1) time."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"DBF file not found: {filepath}")

        with open(filepath, "rb") as f:
            header_bytes = f.read(32)
            if len(header_bytes) < 32:
                raise ValueError(f"Corrupted or empty DBF file: {filepath}")

            version = header_bytes[0]
            yy, mm, dd = header_bytes[1], header_bytes[2], header_bytes[3]
            num_records = struct.unpack("<I", header_bytes[4:8])[0]
            header_len = struct.unpack("<H", header_bytes[8:10])[0]
            record_len = struct.unpack("<H", header_bytes[10:12])[0]

            last_update = None
            try:
                # dBase stores year as offset from 1900 or 2000
                year = 2000 + yy if yy < 70 else 1900 + yy
                last_update = datetime.date(year, mm, dd)
            except Exception:
                pass

            has_memo = bool(version & 0x80)

            # Read Field Descriptors (32 bytes each until terminator 0x0D)
            fields: list[DBFField] = []
            offset = 1  # 1 byte for delete flag

            while True:
                peek = f.read(1)
                if not peek or peek == b"\x0d":
                    break
                rest = f.read(31)
                if len(rest) < 31:
                    break
                field_bytes = peek + rest

                name_raw = field_bytes[:11].split(b"\x00")[0]
                field_name = name_raw.decode(encoding, errors="replace").strip()
                field_type_char = chr(field_bytes[11])
                length = field_bytes[16]
                decimal_count = field_bytes[17]

                try:
                    ft = DBFFieldType(field_type_char)
                except ValueError:
                    ft = DBFFieldType.UNKNOWN

                fields.append(
                    DBFField(
                        name=field_name,
                        field_type=ft,
                        length=length,
                        decimal_count=decimal_count,
                        offset=offset,
                    )
                )
                offset += length

            return DBFHeader(
                version=version,
                last_update=last_update,
                record_count=num_records,
                header_length=header_len,
                record_length=record_len,
                encoding=encoding,
                has_memo=has_memo,
                fields=fields,
            )

    @classmethod
    def read_records(
        cls,
        filepath: str,
        header: DBFHeader | None = None,
        limit: int | None = None,
        offset: int = 0,
        include_deleted: bool = False,
        encoding: str = "cp1252",
    ) -> list[dict[str, Any]]:
        """Read a list of records with typed value conversion."""
        header = header or cls.read_header(filepath, encoding=encoding)
        results: list[dict[str, Any]] = []

        with open(filepath, "rb") as f:
            f.seek(header.header_length)
            records_read = 0
            records_yielded = 0

            while records_read < header.record_count:
                if limit is not None and records_yielded >= limit:
                    break

                record_data = f.read(header.record_length)
                if len(record_data) < header.record_length:
                    break

                records_read += 1

                # Check delete flag (0x2A '*' is deleted, 0x20 ' ' is active)
                is_deleted = record_data[0] == 0x2A
                if is_deleted and not include_deleted:
                    continue

                if offset > 0 and records_read <= offset:
                    continue

                row = cls._parse_record(record_data, header.fields, encoding)
                if include_deleted:
                    row["_is_deleted"] = is_deleted

                results.append(row)
                records_yielded += 1

        return results

    @classmethod
    def stream_batches(
        cls,
        filepath: str,
        header: DBFHeader | None = None,
        batch_size: int = 1000,
        include_deleted: bool = False,
        encoding: str = "cp1252",
    ) -> Generator[list[dict[str, Any]]]:
        """Stream DBF records in memory-efficient batches for large migrations."""
        header = header or cls.read_header(filepath, encoding=encoding)

        with open(filepath, "rb") as f:
            f.seek(header.header_length)
            batch: list[dict[str, Any]] = []
            records_read = 0

            while records_read < header.record_count:
                record_data = f.read(header.record_length)
                if len(record_data) < header.record_length:
                    break

                records_read += 1
                is_deleted = record_data[0] == 0x2A
                if is_deleted and not include_deleted:
                    continue

                row = cls._parse_record(record_data, header.fields, encoding)
                if include_deleted:
                    row["_is_deleted"] = is_deleted

                batch.append(row)
                if len(batch) >= batch_size:
                    yield batch
                    batch = []

            if batch:
                yield batch

    @classmethod
    def count_active_records(
        cls,
        filepath: str,
        header: DBFHeader | None = None,
    ) -> tuple[int, int]:
        """Fast seek-scan to compute (active_count, deleted_count)."""
        header = header or cls.read_header(filepath)
        active_count = 0
        deleted_count = 0

        with open(filepath, "rb") as f:
            for i in range(header.record_count):
                f.seek(header.header_length + (i * header.record_length))
                flag = f.read(1)
                if not flag:
                    break
                if flag == b"*":
                    deleted_count += 1
                else:
                    active_count += 1

        return active_count, deleted_count

    @staticmethod
    def _parse_record(
        record_bytes: bytes,
        fields: list[DBFField],
        encoding: str,
    ) -> dict[str, Any]:
        """Parse raw record bytes into typed Python dictionary."""
        row: dict[str, Any] = {}

        for field in fields:
            raw_val = record_bytes[field.offset : field.offset + field.length]
            str_val = raw_val.decode(encoding, errors="replace").strip()

            if not str_val:
                row[field.name] = None
                continue

            ft = field.field_type
            if ft in (DBFFieldType.NUMERIC, DBFFieldType.FLOAT, DBFFieldType.DOUBLE):
                try:
                    if field.decimal_count == 0 and "." not in str_val:
                        row[field.name] = int(str_val)
                    else:
                        row[field.name] = Decimal(str_val)
                except Exception:
                    row[field.name] = None
            elif ft == DBFFieldType.INTEGER:
                try:
                    row[field.name] = int(str_val)
                except Exception:
                    row[field.name] = None
            elif ft == DBFFieldType.LOGICAL:
                if str_val.upper() in ("T", "Y", "1"):
                    row[field.name] = True
                elif str_val.upper() in ("F", "N", "0"):
                    row[field.name] = False
                else:
                    row[field.name] = None
            elif ft == DBFFieldType.DATE:
                # DBF Date format is typically YYYYMMDD
                if len(str_val) == 8 and str_val.isdigit():
                    try:
                        row[field.name] = f"{str_val[:4]}-{str_val[4:6]}-{str_val[6:8]}"
                    except Exception:
                        row[field.name] = str_val
                else:
                    row[field.name] = str_val
            else:
                row[field.name] = str_val

        return row
