"""Virtual and Inferred Foreign Keys Engine for Implicit Relationship Discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend_ide.domain.schema.enums import ForeignKeyAction
from backend_ide.domain.schema.models import (
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    Table,
)
from backend_ide.generators.naming import singularize


@dataclass(frozen=True)
class InferredRelationship:
    """Represents a discovered relationship candidate between tables."""

    source_table: str
    source_column: str
    target_table: str
    target_column: str
    confidence: float  # 0.0 to 1.0
    reason: str


class InferredRelationsEngine:
    """Discovers unconstrained foreign key relationships via naming convention heuristics."""

    @classmethod
    def discover_relations(
        cls,
        schema: DatabaseSchema,
        min_confidence: float = 0.6,
    ) -> list[InferredRelationship]:
        """Scan all tables and detect foreign key candidates."""
        all_tables: list[Table] = [t for s in schema.schemas for t in s.tables]
        table_map: dict[str, Table] = {t.name.lower(): t for t in all_tables}
        table_singular_map: dict[str, Table] = {singularize(t.name.lower()): t for t in all_tables}

        # Build set of existing explicit foreign key mappings
        existing_fks: set[tuple[str, str, str, str]] = set()
        for t in all_tables:
            for fk in t.foreign_keys:
                for m in fk.column_mappings:
                    existing_fks.add(
                        (
                            t.name.lower(),
                            m.source_column.lower(),
                            fk.target_table.lower(),
                            m.target_column.lower(),
                        )
                    )

        results: list[InferredRelationship] = []

        for src_table in all_tables:
            for col in src_table.columns:
                if col.is_primary_key:
                    continue

                col_name_lower = col.name.lower()

                # Pattern 1: target_singular_id (e.g. user_id -> users.id)
                match_id = re.match(r"^(.+)_(?:id|code|cod)$", col_name_lower)
                if match_id:
                    prefix = match_id.group(1)
                    target_tbl = table_singular_map.get(prefix) or table_map.get(prefix)

                    if target_tbl and target_tbl.name.lower() != src_table.name.lower():
                        tgt_pk_col = (
                            target_tbl.primary_key.column_names[0]
                            if target_tbl.primary_key and target_tbl.primary_key.column_names
                            else "id"
                        )

                        key_tuple = (
                            src_table.name.lower(),
                            col_name_lower,
                            target_tbl.name.lower(),
                            tgt_pk_col.lower(),
                        )
                        if key_tuple not in existing_fks:
                            reason_msg = (
                                f"Columna '{col.name}' coincide con PK de '{target_tbl.name}'"
                            )
                            results.append(
                                InferredRelationship(
                                    source_table=src_table.name,
                                    source_column=col.name,
                                    target_table=target_tbl.name,
                                    target_column=tgt_pk_col,
                                    confidence=0.95,
                                    reason=reason_msg,
                                )
                            )
                            continue

                # Pattern 2: id_target / cod_target (e.g. id_cliente -> clientes.id)
                match_prefix_id = re.match(r"^(?:id|cod|codigo)_(.+)$", col_name_lower)
                if match_prefix_id:
                    suffix = match_prefix_id.group(1)
                    target_tbl = table_singular_map.get(suffix) or table_map.get(suffix)

                    if target_tbl and target_tbl.name.lower() != src_table.name.lower():
                        tgt_pk_col = (
                            target_tbl.primary_key.column_names[0]
                            if target_tbl.primary_key and target_tbl.primary_key.column_names
                            else "id"
                        )

                        key_tuple = (
                            src_table.name.lower(),
                            col_name_lower,
                            target_tbl.name.lower(),
                            tgt_pk_col.lower(),
                        )
                        if key_tuple not in existing_fks:
                            reason_msg = (
                                f"Columna '{col.name}' coincide con entidad '{target_tbl.name}'"
                            )
                            results.append(
                                InferredRelationship(
                                    source_table=src_table.name,
                                    source_column=col.name,
                                    target_table=target_tbl.name,
                                    target_column=tgt_pk_col,
                                    confidence=0.90,
                                    reason=reason_msg,
                                )
                            )
                            continue

        return [r for r in results if r.confidence >= min_confidence]

    @classmethod
    def apply_to_schema(
        cls,
        schema: DatabaseSchema,
        min_confidence: float = 0.7,
    ) -> DatabaseSchema:
        """Return a new DatabaseSchema enriched with inferred foreign keys."""
        inferred = cls.discover_relations(schema, min_confidence=min_confidence)
        if not inferred:
            return schema

        inferred_by_table: dict[str, list[InferredRelationship]] = {}
        for rel in inferred:
            inferred_by_table.setdefault(rel.source_table, []).append(rel)

        new_schemas = []
        for s in schema.schemas:
            new_tables = []
            for t in s.tables:
                fks = list(t.foreign_keys)
                if t.name in inferred_by_table:
                    for rel in inferred_by_table[t.name]:
                        fks.append(
                            ForeignKey(
                                name=f"fk_virtual_{t.name}_{rel.source_column}",
                                source_table=t.name,
                                target_table=rel.target_table,
                                column_mappings=[
                                    ForeignKeyColumnMapping(
                                        source_column=rel.source_column,
                                        target_column=rel.target_column,
                                    )
                                ],
                                on_update=ForeignKeyAction.NO_ACTION,
                                on_delete=ForeignKeyAction.NO_ACTION,
                            )
                        )
                new_tables.append(t.model_copy(update={"foreign_keys": fks}))
            new_schemas.append(s.model_copy(update={"tables": new_tables}))

        return schema.model_copy(update={"schemas": new_schemas})
