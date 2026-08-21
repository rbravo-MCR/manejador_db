"""Intelligent Foreign Key JOIN Resolution and SQL Query Builder."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from backend_ide.domain.schema.models import DatabaseSchema


class JoinRelationship(BaseModel):
    """Represents a resolvable JOIN relationship between two tables."""

    model_config = ConfigDict(frozen=True)

    target_table: str
    target_schema: str
    target_alias: str | None = None
    source_table: str
    source_alias: str | None = None
    condition_pairs: list[tuple[str, str]]  # (source_col, target_col)
    is_outbound: bool = True  # True: source -> target; False: target -> source (reverse)
    relationship_name: str | None = None

    @property
    def on_clause(self) -> str:
        """Construct the ON condition (e.g. 'c.id = r.customer_id')."""
        src_prefix = self.source_alias or self.source_table
        tgt_prefix = self.target_alias or self.target_table

        conditions = []
        for src_col, tgt_col in self.condition_pairs:
            conditions.append(f"{tgt_prefix}.{tgt_col} = {src_prefix}.{src_col}")
        return " AND ".join(conditions)

    @property
    def full_join_clause(self) -> str:
        """Construct complete JOIN statement (e.g. 'JOIN customers c ON c.id = r.customer_id')."""
        alias_part = f" {self.target_alias}" if self.target_alias else ""
        return f"JOIN {self.target_table}{alias_part}\n    ON {self.on_clause}"

    @property
    def completion_text(self) -> str:
        """Text suitable for editor autocompletion insertion."""
        alias_part = f" {self.target_alias}" if self.target_alias else ""
        return f"{self.target_table}{alias_part} ON {self.on_clause}"


class JoinEngine:
    """Detects FK relationships and builds intelligent JOIN queries and completion items."""

    @classmethod
    def find_joins_for_table(
        cls,
        schema_model: DatabaseSchema,
        table_name: str,
        source_alias: str | None = None,
        source_schema: str | None = None,
    ) -> list[JoinRelationship]:
        """Find all direct (outbound) and reverse (inbound) foreign key joins for a table."""
        joins: list[JoinRelationship] = []
        target_table = schema_model.find_table(table_name, source_schema)
        if not target_table:
            return joins

        src_alias = source_alias or cls._suggest_alias(table_name)

        # 1. Outbound FKs (table_name -> parent_table)
        for fk in target_table.foreign_keys:
            tgt_alias = cls._suggest_alias(fk.target_table)
            if tgt_alias == src_alias:
                tgt_alias = f"{tgt_alias}2"

            pairs = [(m.source_column, m.target_column) for m in fk.column_mappings]
            joins.append(
                JoinRelationship(
                    target_table=fk.target_table,
                    target_schema=fk.target_schema,
                    target_alias=tgt_alias,
                    source_table=table_name,
                    source_alias=src_alias,
                    condition_pairs=pairs,
                    is_outbound=True,
                    relationship_name=fk.name,
                )
            )

        # 2. Inbound FKs (child_table -> table_name)
        for s in schema_model.schemas:
            for other_table in s.tables:
                if other_table.name.lower() == table_name.lower():
                    continue
                for fk in other_table.foreign_keys:
                    if fk.target_table.lower() == table_name.lower():
                        tgt_alias = cls._suggest_alias(other_table.name)
                        if tgt_alias == src_alias:
                            tgt_alias = f"{tgt_alias}2"

                        # In reverse: other_table has source_column matching table's target_column
                        pairs = [(m.target_column, m.source_column) for m in fk.column_mappings]
                        joins.append(
                            JoinRelationship(
                                target_table=other_table.name,
                                target_schema=s.name,
                                target_alias=tgt_alias,
                                source_table=table_name,
                                source_alias=src_alias,
                                condition_pairs=pairs,
                                is_outbound=False,
                                relationship_name=fk.name,
                            )
                        )

        return joins

    @classmethod
    def generate_select_with_joins(
        cls,
        schema_model: DatabaseSchema,
        table_name: str,
        schema_name: str = "public",
    ) -> str:
        """Generate a complete formatted SELECT query joining all related FK tables."""
        main_table = schema_model.find_table(table_name, schema_name)
        if not main_table:
            return f"SELECT * FROM {schema_name}.{table_name};"

        main_alias = cls._suggest_alias(table_name)
        joins = cls.find_joins_for_table(schema_model, table_name, source_alias=main_alias)

        select_cols: list[str] = []
        # Columns from main table
        for c in main_table.columns:
            select_cols.append(f"{main_alias}.{c.name}")

        # Columns from joined tables (e.g. name, code, title)
        join_clauses: list[str] = []
        used_aliases: set[str] = {main_alias}

        for j in joins:
            alias = j.target_alias or j.target_table
            if alias in used_aliases:
                alias = f"{alias}_{len(used_aliases)}"
            used_aliases.add(alias)

            # Find related table columns for descriptive projection
            rel_t = schema_model.find_table(j.target_table, j.target_schema)
            if rel_t:
                for c in rel_t.columns:
                    if c.name.lower() in (
                        "name",
                        "nombre",
                        "title",
                        "titulo",
                        "code",
                        "codigo",
                        "email",
                        "total",
                        "status",
                    ):
                        select_cols.append(f"{alias}.{c.name} AS {j.target_table}_{c.name}")

            join_type = "LEFT JOIN"
            qual_target = (
                f"{j.target_schema}.{j.target_table}"
                if j.target_schema != "public"
                else j.target_table
            )
            join_clauses.append(f"{join_type} {qual_target} {alias}\n    ON {j.on_clause}")

        cols_block = ",\n    ".join(select_cols)
        qual_source = f"{schema_name}.{table_name}" if schema_name != "public" else table_name
        from_block = f"FROM {qual_source} {main_alias}"

        if not join_clauses:
            return f"SELECT\n    {cols_block}\n{from_block};"

        joins_block = "\n".join(join_clauses)
        return f"SELECT\n    {cols_block}\n{from_block}\n{joins_block}\nLIMIT 100;"

    @classmethod
    def extract_context_table_and_alias(cls, sql_context: str) -> tuple[str | None, str | None]:
        """Extract the active table and optional alias from SQL preceding cursor.

        Examples:
            'SELECT * FROM reservations r JOIN ' -> ('reservations', 'r')
            'SELECT * FROM public.orders JOIN ' -> ('orders', None)
        """
        pattern = (
            r"\b(?:FROM|JOIN)\s+(?:[\w]+\.)?([a-zA-Z_][\w]*)(?:\s+(?:AS\s+)?([a-zA-Z_][\w]*))?"
        )
        matches = list(re.finditer(pattern, sql_context, re.IGNORECASE))
        if not matches:
            return None, None

        last_match = matches[-1]
        tbl = last_match.group(1)
        alias = last_match.group(2)

        # Discard keyword false positives in alias
        if alias and alias.upper() in (
            "WHERE",
            "JOIN",
            "LEFT",
            "RIGHT",
            "INNER",
            "CROSS",
            "FULL",
            "ON",
            "GROUP",
            "ORDER",
            "LIMIT",
            "SET",
        ):
            alias = None

        return tbl, alias

    @classmethod
    def _suggest_alias(cls, table_name: str) -> str:
        """Create a short SQL table alias (e.g. 'users' -> 'u', 'order_items' -> 'oi')."""
        clean = table_name.lower().strip()
        parts = clean.split("_")
        if len(parts) > 1:
            return "".join(p[0] for p in parts if p)
        return clean[0] if clean else "t"
