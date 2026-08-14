"""Breadcrumb Bar Component displaying active database hierarchy context."""

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

        self.lbl_conn = QLabel("🔌 Local PostgreSQL (Dev)")
        self.lbl_sep1 = QLabel("›")
        self.lbl_db = QLabel("🗄️ postgres")
        self.lbl_sep2 = QLabel("›")
        self.lbl_schema = QLabel("📦 public")

        for lbl in (self.lbl_sep1, self.lbl_sep2):
            lbl.setStyleSheet("color: #6c7086; font-size: 14px; font-weight: bold;")

        self.lbl_conn.setStyleSheet("font-weight: 500;")
        self.lbl_db.setStyleSheet("font-weight: 500;")
        self.lbl_schema.setStyleSheet("font-weight: bold; color: #89b4fa;")

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
        self.lbl_conn.setText(f"🔌 {connection_name}")
        self.lbl_db.setText(f"🗄️ {db_name}")
        self.lbl_schema.setText(f"📦 {schema_name}")
