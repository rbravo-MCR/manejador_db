"""Breadcrumb Bar Component displaying active database hierarchy context."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class BreadcrumbWidget(QWidget):
    """Displays active breadcrumb path: Connection > Database > Schema > Table."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("breadcrumb_bar")
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        self.lbl_conn = QLabel("Local PostgreSQL (Dev)")
        self.lbl_conn.setObjectName("breadcrumb_conn")

        self.lbl_sep1 = QLabel("›")
        self.lbl_sep1.setObjectName("breadcrumb_sep")

        self.lbl_db = QLabel("postgres")
        self.lbl_db.setObjectName("breadcrumb_db")

        self.lbl_sep2 = QLabel("›")
        self.lbl_sep2.setObjectName("breadcrumb_sep")

        self.lbl_schema = QLabel("public")
        self.lbl_schema.setObjectName("breadcrumb_schema")

        layout.addWidget(self.lbl_conn)
        layout.addWidget(self.lbl_sep1)
        layout.addWidget(self.lbl_db)
        layout.addWidget(self.lbl_sep2)
        layout.addWidget(self.lbl_schema)
        layout.addStretch()

    def set_path(
        self,
        connection_name: str = "Local PostgreSQL",
        db_name: str = "postgres",
        schema_name: str = "public",
        table_name: str | None = None,
    ) -> None:
        """Update breadcrumb path components."""
        self.lbl_conn.setText(connection_name)
        self.lbl_db.setText(db_name)
        self.lbl_schema.setText(schema_name)
