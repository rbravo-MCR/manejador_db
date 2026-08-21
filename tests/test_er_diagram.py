"""Comprehensive Unit and Integration tests for Visual Entity-Relationship (ER) Diagram."""

from __future__ import annotations

import os
from pathlib import Path

from backend_ide.domain.diagram.exporters import (
    ERDbmLExporter,
    ERMermaidExporter,
    ERPlantUMLExporter,
)
from backend_ide.domain.schema import (
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    NormalizedDataType,
    PrimaryKey,
    Schema,
    Table,
)
from backend_ide.ui.diagram.diagram_widget import ERDiagramWidget
from backend_ide.ui.diagram.layout_engine import ERLayoutEngine
from backend_ide.ui.diagram.relationship_edge import EREdgeStyle, ERRelationshipEdge
from backend_ide.ui.diagram.table_node import (
    ERTableDisplayMode,
    ERTableNode,
)

os.environ["QT_QPA_PLATFORM"] = "offscreen"


def create_sample_er_schema() -> DatabaseSchema:
    """Helper creating multi-table schema with relationships."""
    users_table = Table(
        name="users",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="username",
                native_type="VARCHAR(50)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
            Column(
                name="email",
                native_type="VARCHAR(100)",
                normalized_type=NormalizedDataType.VARCHAR,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    orders_table = Table(
        name="orders",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
            ),
            Column(
                name="user_id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
            ),
            Column(
                name="total_amount",
                native_type="DECIMAL(10,2)",
                normalized_type=NormalizedDataType.DECIMAL,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
        foreign_keys=[
            ForeignKey(
                name="fk_orders_user",
                source_schema="public",
                source_table="orders",
                target_schema="public",
                target_table="users",
                column_mappings=[
                    ForeignKeyColumnMapping(source_column="user_id", target_column="id")
                ],
            )
        ],
    )

    return DatabaseSchema(
        engine_name="postgresql",
        database_name="shop_db",
        schemas=[Schema(name="public", tables=[users_table, orders_table])],
    )


def test_er_table_node_creation_and_display_modes():
    """Verify ERTableNode dimensions, column anchors, and display mode switches."""
    schema = create_sample_er_schema()
    users_table = schema.schemas[0].tables[0]

    node = ERTableNode(users_table, display_mode=ERTableDisplayMode.FULL)
    assert node.node_width >= 240.0
    assert node.node_height > node.header_height
    assert "users" in node.toolTip()

    # Verify column anchor
    anchor_y = node.get_column_anchor_y("username")
    assert anchor_y > node.scenePos().y()

    # Switch to compact
    node.set_display_mode(ERTableDisplayMode.COMPACT)
    assert node.node_width == 190.0

    # Switch to minimal
    node.set_display_mode(ERTableDisplayMode.MINIMAL)
    assert node.node_height == node.header_height


def test_er_relationship_edge_path_and_styles():
    """Verify ERRelationshipEdge connects column anchors with bezier and orthogonal styles."""
    schema = create_sample_er_schema()
    users_table = schema.schemas[0].tables[0]
    orders_table = schema.schemas[0].tables[1]

    node_users = ERTableNode(users_table)
    node_orders = ERTableNode(orders_table)

    node_users.setPos(0, 0)
    node_orders.setPos(400, 0)

    fk = orders_table.foreign_keys[0]
    edge = ERRelationshipEdge(fk, node_orders, node_users, style=EREdgeStyle.BEZIER)

    assert edge.source_node is node_orders
    assert edge.target_node is node_users
    assert not edge.path().isEmpty()
    assert "fk_orders_user" in edge.toolTip()

    # Switch style to orthogonal
    edge.set_edge_style(EREdgeStyle.ORTHOGONAL)
    assert edge.style == EREdgeStyle.ORTHOGONAL
    assert not edge.path().isEmpty()


def test_er_layout_engine_all_algorithms():
    """Verify Grid, Hierarchical, Force-Directed, and Circular layout algorithms."""
    schema = create_sample_er_schema()
    nodes = [ERTableNode(t) for t in schema.schemas[0].tables]
    edges = [ERRelationshipEdge(schema.schemas[0].tables[1].foreign_keys[0], nodes[1], nodes[0])]

    # 1. Grid layout
    ERLayoutEngine.layout_grid(nodes)
    assert nodes[0].pos() != nodes[1].pos()

    # 2. Hierarchical layout
    ERLayoutEngine.layout_hierarchical(nodes, edges)
    # Users is parent (rank 0, x=60), Orders is child (rank 1, x=60+340=400)
    assert nodes[0].pos().x() < nodes[1].pos().x()

    # 3. Force-directed layout
    ERLayoutEngine.layout_force_directed(nodes, edges, iterations=10)
    assert nodes[0].pos().x() >= 60.0

    # 4. Circular layout
    ERLayoutEngine.layout_circular(nodes)
    assert nodes[0].pos() != nodes[1].pos()


def test_er_text_exporters():
    """Verify Mermaid.js, DBML, and PlantUML exporters produce valid code."""
    schema = create_sample_er_schema()

    # Mermaid
    mermaid_code = ERMermaidExporter.export(schema)
    assert "erDiagram" in mermaid_code
    assert "users" in mermaid_code
    assert "orders" in mermaid_code
    assert "users ||--o{ orders" in mermaid_code

    # DBML
    dbml_code = ERDbmLExporter.export(schema)
    assert "Table users {" in dbml_code
    assert "Table orders {" in dbml_code
    assert "Ref: orders.user_id > users.id" in dbml_code

    # PlantUML
    puml_code = ERPlantUMLExporter.export(schema)
    assert "@startuml" in puml_code
    assert 'entity "users"' in puml_code
    assert "@enduml" in puml_code


def test_er_diagram_scene_and_widget(qtbot, tmp_path: Path):
    """Verify ERDiagramWidget full workflow: schema loading, search filter, minimap, and exports."""
    schema = create_sample_er_schema()
    widget = ERDiagramWidget(schema)
    qtbot.addWidget(widget)

    assert len(widget.scene.nodes) == 2
    assert len(widget.scene.edges) == 1
    assert "2 tablas" in widget.lbl_stats.text()

    # Test column search filter (searching 'username' should highlight 'users')
    widget.txt_search.setText("username")
    assert widget.scene.nodes["users"].opacity() == 1.0
    assert widget.scene.nodes["orders"].opacity() < 1.0

    widget.txt_search.setText("")
    assert widget.scene.nodes["orders"].opacity() == 1.0

    # Test detail mode changes
    widget.cmb_detail.setCurrentIndex(1)
    assert widget.scene.display_mode == ERTableDisplayMode.COMPACT

    widget.cmb_detail.setCurrentIndex(2)
    assert widget.scene.display_mode == ERTableDisplayMode.MINIMAL

    # Test minimap toggle
    assert widget.view.minimap.isHidden() is True
    widget.btn_minimap.setChecked(True)
    assert widget.view.minimap.isHidden() is False
    widget.btn_minimap.setChecked(False)
    assert widget.view.minimap.isHidden() is True

    # Test zoom actions
    widget.btn_zoom_in.click()
    widget.btn_zoom_out.click()
    widget.btn_zoom_reset.click()
    widget.btn_zoom_fit.click()

    # Test PNG image export with 1x and 2x resolution
    export_1x = tmp_path / "test_er_1x.png"
    assert widget.export_image(str(export_1x), scale=1.0) is True
    assert export_1x.exists()
    assert export_1x.stat().st_size > 0

    export_2x = tmp_path / "test_er_2x.png"
    assert widget.export_image(str(export_2x), scale=2.0) is True
    assert export_2x.exists()
    assert export_2x.stat().st_size > export_1x.stat().st_size
