"""Enterprise Layout Algorithms for Entity-Relationship Diagrams.

Provides Grid, Hierarchical (Layered DAG with Sub-Columns), Force-Directed,
and Circular layouts optimized for schemas from 2 tables to 10,000+ tables
without coordinate overflow.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend_ide.ui.diagram.relationship_edge import ERRelationshipEdge
    from backend_ide.ui.diagram.table_node import ERTableNode


class ERLayoutEngine:
    """Calculates non-overlapping, balanced positions for ER Diagram table nodes."""

    @classmethod
    def layout_grid(
        cls,
        nodes: list[ERTableNode],
        col_width: float = 320.0,
        margin_x: float = 60.0,
        margin_y: float = 60.0,
        gap_y: float = 30.0,
        max_rows_per_col: int = 20,
    ) -> None:
        """Position nodes in a 16:9 balanced multi-column grid."""
        if not nodes:
            return

        num_nodes = len(nodes)
        # Compute optimal number of columns to prevent tall vertical towers
        ideal_cols = max(3, math.ceil(math.sqrt(num_nodes * 1.6)))
        min_cols_needed = math.ceil(num_nodes / max_rows_per_col)
        num_cols = max(ideal_cols, min_cols_needed)

        col_heights: list[float] = [margin_y for _ in range(num_cols)]

        for node in nodes:
            shortest_col = col_heights.index(min(col_heights))
            pos_x = margin_x + (shortest_col * col_width)
            pos_y = col_heights[shortest_col]

            node.setPos(pos_x, pos_y)
            col_heights[shortest_col] += node.node_height + gap_y

        cls._refresh_edges(nodes)

    @classmethod
    def layout_hierarchical(
        cls,
        nodes: list[ERTableNode],
        edges: list[ERRelationshipEdge],
        col_width: float = 320.0,
        layer_gap_x: float = 80.0,
        gap_y: float = 30.0,
        margin: float = 60.0,
        max_rows_per_col: int = 18,
    ) -> None:
        """Arrange nodes in DAG layers, wrapping large layers into sub-columns."""
        if not nodes:
            return

        # 1. Bounded topological layer assignment
        ranks: dict[str, int] = {n.table.name: 0 for n in nodes}
        max_depth = min(len(nodes), 20)

        for _ in range(max_depth):
            changed = False
            for edge in edges:
                src = edge.fk.source_table
                tgt = edge.fk.target_table
                if src in ranks and tgt in ranks and src != tgt:
                    if ranks[src] <= ranks[tgt]:
                        ranks[src] = min(ranks[tgt] + 1, 10)
                        changed = True
            if not changed:
                break

        # 2. Group nodes by rank
        max_rank = max(ranks.values()) if ranks else 0
        layers: list[list[ERTableNode]] = [[] for _ in range(max_rank + 1)]
        for n in nodes:
            r = ranks.get(n.table.name, 0)
            layers[r].append(n)

        # 3. Position each layer horizontally with multi-column wrapping
        current_x = margin

        for layer_nodes in layers:
            if not layer_nodes:
                continue

            num_sub_cols = max(1, math.ceil(len(layer_nodes) / max_rows_per_col))
            sub_col_heights = [margin for _ in range(num_sub_cols)]

            for node in layer_nodes:
                sub_col_idx = sub_col_heights.index(min(sub_col_heights))
                pos_x = current_x + (sub_col_idx * col_width)
                pos_y = sub_col_heights[sub_col_idx]

                node.setPos(pos_x, pos_y)
                sub_col_heights[sub_col_idx] += node.node_height + gap_y

            # Advance X past all sub-columns in this layer
            current_x += (num_sub_cols * col_width) + layer_gap_x

        cls._refresh_edges(nodes)

    @classmethod
    def layout_force_directed(
        cls,
        nodes: list[ERTableNode],
        edges: list[ERRelationshipEdge],
        iterations: int = 30,
        k: float = 280.0,
    ) -> None:
        """Arrange nodes using spring-electric physics simulation."""
        if not nodes:
            return

        # For very large schemas (> 150 tables), fallback to grid for speed
        if len(nodes) > 150:
            cls.layout_grid(nodes)
            return

        cls.layout_circular(nodes, radius=max(300.0, len(nodes) * 45.0))

        positions = {n: [n.pos().x(), n.pos().y()] for n in nodes}
        disp = {n: [0.0, 0.0] for n in nodes}

        temp = 120.0
        dt = temp / max(1, iterations)

        for _ in range(iterations):
            for i, v in enumerate(nodes):
                disp[v] = [0.0, 0.0]
                for j, u in enumerate(nodes):
                    if i != j:
                        dx = positions[v][0] - positions[u][0]
                        dy = positions[v][1] - positions[u][1]
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist > 0:
                            rep = (k * k) / dist
                            disp[v][0] += (dx / dist) * rep
                            disp[v][1] += (dy / dist) * rep

            for edge in edges:
                v = edge.source_node
                u = edge.target_node
                if v in positions and u in positions and v != u:
                    dx = positions[v][0] - positions[u][0]
                    dy = positions[v][1] - positions[u][1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > 0:
                        attr = (dist * dist) / k
                        disp[v][0] -= (dx / dist) * attr
                        disp[v][1] -= (dy / dist) * attr
                        disp[u][0] += (dx / dist) * attr
                        disp[u][1] += (dy / dist) * attr

            for node in nodes:
                dx, dy = disp[node]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0:
                    limited_dist = min(dist, temp)
                    positions[node][0] += (dx / dist) * limited_dist
                    positions[node][1] += (dy / dist) * limited_dist

            temp = max(1.0, temp - dt)

        min_x = min(p[0] for p in positions.values())
        min_y = min(p[1] for p in positions.values())

        for node, pos in positions.items():
            node.setPos(pos[0] - min_x + 60.0, pos[1] - min_y + 60.0)

        cls._refresh_edges(nodes)

    @classmethod
    def layout_circular(
        cls,
        nodes: list[ERTableNode],
        radius: float = 400.0,
        center_x: float = 600.0,
        center_y: float = 500.0,
    ) -> None:
        """Position nodes in a circle around the canvas center."""
        if not nodes:
            return

        # For very large schemas, use grid
        if len(nodes) > 150:
            cls.layout_grid(nodes)
            return

        count = len(nodes)
        angle_step = (2 * math.pi) / count

        for i, node in enumerate(nodes):
            angle = i * angle_step
            pos_x = center_x + radius * math.cos(angle) - (node.node_width / 2.0)
            pos_y = center_y + radius * math.sin(angle) - (node.node_height / 2.0)
            node.setPos(max(60.0, pos_x), max(60.0, pos_y))

        cls._refresh_edges(nodes)

    @classmethod
    def auto_layout(
        cls,
        nodes: list[ERTableNode],
        edges: list[ERRelationshipEdge] | None = None,
    ) -> None:
        """Default smart auto-layout."""
        if edges and len(edges) > 0 and len(nodes) <= 300:
            cls.layout_hierarchical(nodes, edges)
        else:
            cls.layout_grid(nodes)

    @staticmethod
    def _refresh_edges(nodes: list[ERTableNode]) -> None:
        """Trigger path updates on all registered edges for the nodes."""
        seen_edges = set()
        for node in nodes:
            for edge in node.edges:
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    edge.update_path()
