"""Unit and Integration tests for Phase 4 - Connection Profiles & Keyring Security."""

import os
import time
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit

from backend_ide.application.connection_service import ConnectionService
from backend_ide.domain.connection import ConnectionProfile, Environment
from backend_ide.infrastructure.storage.connection_repository import ConnectionRepository
from backend_ide.ui.components import ConnectionSelector
from backend_ide.ui.dialogs.connection_dialog import ConnectionDialog

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture
def temp_repo(tmp_path):
    """Fixture providing ConnectionRepository with temporary storage path."""
    json_path = tmp_path / "test_connections.json"
    repo = ConnectionRepository(json_path)

    # Mock keyring calls to avoid needing system D-Bus / SecretService in headless test
    keyring_store = {}

    def mock_set(service, username, password):
        keyring_store[f"{service}:{username}"] = password

    def mock_get(service, username):
        return keyring_store.get(f"{service}:{username}")

    def mock_delete(service, username):
        keyring_store.pop(f"{service}:{username}", None)

    with (
        patch("keyring.set_password", side_effect=mock_set),
        patch("keyring.get_password", side_effect=mock_get),
        patch("keyring.delete_password", side_effect=mock_delete),
    ):
        yield repo, keyring_store


def test_connection_profile_model():
    """Test ConnectionProfile model attributes and default values."""
    profile = ConnectionProfile(
        name="Production Database",
        engine="postgresql",
        host="prod.db.internal",
        port=5432,
        database="analytics",
        username="admin",
        environment=Environment.PRODUCTION,
        color="#f38ba8",
    )

    assert profile.name == "Production Database"
    assert profile.environment == Environment.PRODUCTION
    assert profile.color == "#f38ba8"
    assert profile.id is not None


def test_connection_repository_persistence(temp_repo):
    """Test saving profile metadata to JSON and credential securely to keyring."""
    repo, keyring_store = temp_repo

    profile = ConnectionProfile(
        name="Staging MySQL",
        engine="mysql",
        host="staging.db",
        port=3306,
        database="staging_db",
        username="app_user",
        environment=Environment.STAGING,
    )

    repo.save_profile(profile, password="SuperSecretPassword123!")

    # Verify JSON file exists and contains NO plain-text password
    content = repo.storage_path.read_text()
    assert "SuperSecretPassword123!" not in content
    assert "Staging MySQL" in content

    # Verify profile loaded correctly
    loaded_profiles = repo.load_all_profiles()
    assert len(loaded_profiles) == 1
    assert loaded_profiles[0].name == "Staging MySQL"

    # Verify password retrieved from keyring
    fetched_pwd = repo.get_password(profile.id)
    assert fetched_pwd == "SuperSecretPassword123!"

    # Delete profile
    deleted = repo.delete_profile(profile.id)
    assert deleted is True
    assert len(repo.load_all_profiles()) == 0
    assert repo.get_password(profile.id) is None


def test_connection_service_and_adapter(temp_repo):
    """Test ConnectionService orchestration and adapter building."""
    repo, _ = temp_repo
    service = ConnectionService(repo)

    profile = ConnectionProfile(
        name="Dev Postgres",
        engine="postgresql",
        host="localhost",
        port=5432,
        database="devdb",
        username="postgres",
    )

    service.save_profile(profile, "my_dev_password")

    profiles = service.list_profiles()
    assert len(profiles) == 1

    conn_adapter = service.build_connection(profile)
    assert conn_adapter is not None
    assert conn_adapter.config.password == "my_dev_password"


def test_connection_service_can_target_another_database_without_mutating_profile(temp_repo):
    """A database dropdown selection creates a transient adapter, not a duplicate profile."""
    repo, _ = temp_repo
    service = ConnectionService(repo)
    profile = ConnectionProfile(name="RDS", engine="postgresql", database="db_outlet")

    adapter = service.build_connection(profile, "secret", database_name="analytics")

    assert adapter.config.database == "analytics"
    assert profile.database == "db_outlet"


def test_connection_selector_can_select_profile_by_id(temp_repo, qtbot):
    """A newly saved profile can become the active toolbar selection."""
    repo, _ = temp_repo
    service = ConnectionService(repo)
    first = ConnectionProfile(name="First", engine="postgresql")
    second = ConnectionProfile(name="Second", engine="postgresql")
    service.save_profile(first)
    service.save_profile(second)
    selector = ConnectionSelector(service)
    qtbot.addWidget(selector)

    assert selector.select_profile(second.id)
    assert selector.get_selected_profile().id == second.id


def test_connection_dialog_gui(temp_repo, qtbot):
    """Test PySide6 ConnectionDialog profile editing and saving."""
    repo, _ = temp_repo
    service = ConnectionService(repo)

    profile = ConnectionProfile(name="Initial Profile", engine="postgresql")
    dialog = ConnectionDialog(profile=profile, connection_service=service)
    qtbot.addWidget(dialog)

    # Edit fields
    dialog.txt_name.setText("Updated Production DB")
    dialog.txt_host.setText("10.0.0.5")
    dialog.txt_password.setText("SecretPassword!")

    # Mock test connection
    with patch.object(service, "test_connection", return_value=True):
        qtbot.mouseClick(dialog.btn_test, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: dialog.btn_test.isEnabled(), timeout=1000)
        assert "Exitosa" in dialog.lbl_status.text()

    # Save dialog
    qtbot.mouseClick(dialog.btn_save, Qt.MouseButton.LeftButton)
    assert dialog.result() == ConnectionDialog.DialogCode.Accepted

    # Verify saved to repo
    saved_profiles = service.list_profiles()
    assert len(saved_profiles) == 1
    assert saved_profiles[0].name == "Updated Production DB"
    assert service.get_password(saved_profiles[0].id) == "SecretPassword!"


def test_password_visibility_action_toggles_protected_text(temp_repo, qtbot):
    """Keep passwords protected by default and reveal them only on explicit request."""
    repo, _ = temp_repo
    dialog = ConnectionDialog(connection_service=ConnectionService(repo))
    qtbot.addWidget(dialog)
    dialog.txt_password.setText("SecretPassword!")

    assert dialog.txt_password.echoMode() == QLineEdit.EchoMode.Password
    assert not dialog.password_visibility_action.icon().isNull()
    assert dialog.password_visibility_action.toolTip() == "Mostrar contraseña"

    dialog.password_visibility_action.trigger()

    assert dialog.txt_password.echoMode() == QLineEdit.EchoMode.Normal
    assert not dialog.password_visibility_action.icon().isNull()
    assert dialog.password_visibility_action.toolTip() == "Ocultar contraseña"

    dialog.password_visibility_action.trigger()

    assert dialog.txt_password.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.password_visibility_action.toolTip() == "Mostrar contraseña"


def test_connection_test_runs_without_blocking_or_closing_dialog(temp_repo, qtbot):
    """A slow network attempt must not freeze or close the connection dialog."""
    repo, _ = temp_repo
    service = ConnectionService(repo)
    dialog = ConnectionDialog(connection_service=service)
    qtbot.addWidget(dialog)
    dialog.show()

    def slow_failure(*_args):
        time.sleep(0.2)
        return False

    with patch.object(service, "test_connection", side_effect=slow_failure):
        started_at = time.perf_counter()
        qtbot.mouseClick(dialog.btn_test, Qt.MouseButton.LeftButton)
        click_elapsed = time.perf_counter() - started_at

        assert click_elapsed < 0.1
        assert not dialog.btn_test.isEnabled()
        assert "Probando" in dialog.lbl_status.text()
        assert dialog.isVisible()

        qtbot.waitUntil(lambda: dialog.btn_test.isEnabled(), timeout=1500)

    assert "Error" in dialog.lbl_status.text()
    assert dialog.isVisible()


def test_connection_dialog_exposes_and_preserves_ssl_mode(temp_repo, qtbot):
    """The PostgreSQL SSL requirement must be selectable and copied to the profile."""
    repo, _ = temp_repo
    profile = ConnectionProfile(name="RDS", engine="postgresql", ssl_mode="require")
    dialog = ConnectionDialog(profile=profile, connection_service=ConnectionService(repo))
    qtbot.addWidget(dialog)

    assert dialog.cmb_ssl.currentData() == "require"

    none_index = dialog.cmb_ssl.findData("disable")
    dialog.cmb_ssl.setCurrentIndex(none_index)

    assert dialog._extract_profile_data().ssl_mode == "disable"


def test_connection_dialog_marks_missing_required_fields_before_testing(temp_repo, qtbot):
    """Missing connection data must be identified before starting a network attempt."""
    repo, _ = temp_repo
    service = ConnectionService(repo)
    dialog = ConnectionDialog(connection_service=service)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.txt_host.clear()
    dialog.txt_database.clear()

    with patch.object(service, "test_connection") as test_connection:
        qtbot.mouseClick(dialog.btn_test, Qt.MouseButton.LeftButton)
        dialog._thread_pool.waitForDone(1000)

        test_connection.assert_not_called()
    assert "Host / Servidor" in dialog.lbl_status.text()
    assert "Base de Datos" in dialog.lbl_status.text()
    assert "border" in dialog.txt_host.styleSheet()
    assert "border" in dialog.txt_database.styleSheet()
    assert dialog.isVisible()
