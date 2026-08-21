"""Unit and Architecture tests for the Code Generators Layer."""

from __future__ import annotations

import inspect

import pytest

from backend_ide.domain.schema.enums import ForeignKeyAction, NormalizedDataType
from backend_ide.domain.schema.models import (
    Column,
    DatabaseSchema,
    ForeignKey,
    ForeignKeyColumnMapping,
    PrimaryKey,
    Schema,
    Table,
)
from backend_ide.generators.contracts import (
    GenerationRequest,
    GenerationTarget,
    Language,
)
from backend_ide.generators.naming import (
    pluralize,
    sanitize_identifier,
    singularize,
    table_to_class_name,
    to_camel_case,
    to_pascal_case,
    to_snake_case,
)
from backend_ide.generators.registry import GeneratorRegistry


@pytest.fixture
def complex_database_schema() -> DatabaseSchema:
    """Fixture providing a multi-table database schema with PKs, FKs, and rich types."""
    roles_table = Table(
        name="roles",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_primary_key=True,
                is_auto_increment=True,
                is_nullable=False,
            ),
            Column(
                name="role_name",
                native_type="VARCHAR(50)",
                normalized_type=NormalizedDataType.VARCHAR,
                length=50,
                is_nullable=False,
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
    )

    users_table = Table(
        name="users",
        schema_name="public",
        columns=[
            Column(
                name="id",
                native_type="BIGINT",
                normalized_type=NormalizedDataType.BIGINT,
                is_primary_key=True,
                is_auto_increment=True,
                is_nullable=False,
            ),
            Column(
                name="email",
                native_type="VARCHAR(255)",
                normalized_type=NormalizedDataType.VARCHAR,
                length=255,
                is_nullable=False,
            ),
            Column(
                name="role_id",
                native_type="INT",
                normalized_type=NormalizedDataType.INTEGER,
                is_nullable=True,
            ),
            Column(
                name="balance",
                native_type="DECIMAL(12,2)",
                normalized_type=NormalizedDataType.DECIMAL,
                precision=12,
                scale=2,
                is_nullable=False,
                default_value="0.00",
            ),
            Column(
                name="is_active",
                native_type="BOOLEAN",
                normalized_type=NormalizedDataType.BOOLEAN,
                is_nullable=False,
                default_value="true",
            ),
            Column(
                name="metadata",
                native_type="JSONB",
                normalized_type=NormalizedDataType.JSONB,
                is_nullable=True,
            ),
            Column(
                name="created_at",
                native_type="TIMESTAMP WITH TIME ZONE",
                normalized_type=NormalizedDataType.TIMESTAMPTZ,
                is_nullable=False,
                default_value="NOW()",
            ),
        ],
        primary_key=PrimaryKey(column_names=["id"]),
        foreign_keys=[
            ForeignKey(
                name="fk_users_role",
                source_table="users",
                target_table="roles",
                column_mappings=[
                    ForeignKeyColumnMapping(source_column="role_id", target_column="id")
                ],
                on_delete=ForeignKeyAction.SET_NULL,
            )
        ],
    )

    return DatabaseSchema(
        engine_name="postgresql",
        database_name="app_db",
        schemas=[Schema(name="public", tables=[roles_table, users_table])],
    )


def test_naming_transformations():
    """Verify string transformation algorithms for identifiers and classes."""
    assert to_snake_case("UserProfile") == "user_profile"
    assert to_snake_case("user-profile") == "user_profile"
    assert to_pascal_case("user_accounts") == "UserAccounts"
    assert to_camel_case("created_at") == "createdAt"
    assert table_to_class_name("users") == "User"
    assert table_to_class_name("order_items") == "OrderItem"
    assert singularize("categories") == "category"
    assert singularize("users") == "user"
    assert pluralize("user") == "users"
    assert pluralize("category") == "categories"

    assert sanitize_identifier("class", Language.PYTHON) == "class_"
    assert sanitize_identifier("type", Language.TYPESCRIPT) == "type_"


def test_registry_contains_all_targets():
    """Registry should register all standard ORM and Non-ORM targets."""
    registry = GeneratorRegistry.get_instance()
    all_targets = [g.target for g in registry.list_all()]

    expected = [
        GenerationTarget.SQLALCHEMY,
        GenerationTarget.SQLMODEL,
        GenerationTarget.DJANGO,
        GenerationTarget.PRISMA,
        GenerationTarget.DRIZZLE,
        GenerationTarget.ELOQUENT,
        GenerationTarget.EF_CORE,
        GenerationTarget.PYTHON_RAW,
        GenerationTarget.DAPPER,
        GenerationTarget.TS_RAW,
        GenerationTarget.PHP_PDO,
    ]

    for t in expected:
        assert t in all_targets
        gen = registry.get(t)
        assert gen is not None
        assert gen.target == t


def test_sqlalchemy_generator(complex_database_schema):
    """SQLAlchemy 2.0 generator must produce valid Mapped declarations with types and FKs."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.SQLALCHEMY)
    project = registry.generate(complex_database_schema, request)

    assert len(project.files) == 1
    content = project.primary_file_content

    assert "class User(Base):" in content
    assert '__tablename__ = "users"' in content
    assert "id: Mapped[int] = mapped_column(BigInteger(), primary_key=True" in content
    assert "email: Mapped[str] = mapped_column(String(255), nullable=False)" in content
    assert 'ForeignKey("roles.id")' in content
    assert "balance: Mapped[Decimal] = mapped_column(Numeric(12, 2)" in content
    assert "created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)" in content


def test_sqlmodel_generator(complex_database_schema):
    """SQLModel generator must output Pydantic-compatible SQLModel definitions."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.SQLMODEL)
    project = registry.generate(complex_database_schema, request)

    content = project.primary_file_content
    assert "class User(SQLModel, table=True):" in content
    assert 'foreign_key="roles.id"' in content
    assert "id: int | None = Field(primary_key=True, default=None)" in content
    assert "email: str = Field(max_length=255)" in content


def test_django_generator(complex_database_schema):
    """Django generator must produce models.Model classes."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.DJANGO)
    project = registry.generate(complex_database_schema, request)

    content = project.primary_file_content
    assert "class User(models.Model):" in content
    assert "email = models.CharField(max_length=255" in content
    assert "role = models.ForeignKey('Role', on_delete=models.CASCADE" in content
    assert "db_table = 'users'" in content


def test_prisma_generator(complex_database_schema):
    """Prisma generator must produce a clean schema.prisma."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.PRISMA)
    project = registry.generate(complex_database_schema, request)

    content = project.primary_file_content
    assert "model User {" in content
    assert "id               BigInt @id @default(autoincrement())" in content
    assert "email            String" in content
    assert "balance          Decimal" in content
    assert 'createdAt        DateTime @default(now()) @map("created_at")' in content
    assert "role             Role @relation(fields: [roleId], references: [id])" in content
    assert '@@map("users")' in content


def test_drizzle_generator(complex_database_schema):
    """Drizzle generator must produce TypeScript pgTable schemas and inferred types."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.DRIZZLE)
    project = registry.generate(complex_database_schema, request)

    content = project.primary_file_content
    assert 'export const users = pgTable("users", {' in content
    assert 'id: bigserial("id", { mode: "number" }).primaryKey()' in content
    assert 'email: varchar("email", { length: 255 }).notNull()' in content
    assert 'balance: decimal("balance", { precision: 12, scale: 2 }).notNull()' in content
    assert "export type User = typeof users.$inferSelect;" in content
    assert "export type NewUser = typeof users.$inferInsert;" in content


def test_eloquent_generator(complex_database_schema):
    """Eloquent generator must produce PHP Model classes with fillable and casts."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.ELOQUENT)
    project = registry.generate(complex_database_schema, request)

    assert len(project.files) == 2
    user_file = next(f for f in project.files if f.path == "app/Models/User.php")
    content = user_file.content

    assert "class User extends Model" in content
    assert "protected $table = 'users';" in content
    assert "'email'," in content
    assert "'created_at' => 'datetime'," in content
    assert "public function role(): BelongsTo" in content


def test_ef_core_generator(complex_database_schema):
    """EF Core generator must produce C# POCOs and ApplicationDbContext."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.EF_CORE)
    project = registry.generate(complex_database_schema, request)

    user_file = next(f for f in project.files if f.path == "Entities/User.cs")
    assert "public class User" in user_file.content
    assert '[Table("users", Schema = "public")]' in user_file.content
    assert "[Key]" in user_file.content
    assert "public long Id { get; set; }" in user_file.content
    assert "public string Email { get; set; } = string.Empty;" in user_file.content

    db_context = next(f for f in project.files if f.path == "Data/ApplicationDbContext.cs")
    assert "public DbSet<User> Users { get; set; }" in db_context.content


def test_python_raw_generator(complex_database_schema):
    """Python direct SQL generator must produce dataclasses and async parameterized repos."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.PYTHON_RAW)
    project = registry.generate(complex_database_schema, request)

    content = project.primary_file_content
    assert "@dataclass(frozen=True)" in content
    assert "class User:" in content
    assert "class UserRepository:" in content
    assert "async def get_by_id(self, id: int) -> Optional[User]:" in content
    assert "INSERT INTO public.users" in content
    assert "%(email)s" in content


def test_dapper_generator(complex_database_schema):
    """Dapper generator must produce C# records and async repositories with IDbConnection."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.DAPPER)
    project = registry.generate(complex_database_schema, request)

    user_repo = next(f for f in project.files if f.path == "Repositories/UserRepository.cs")
    content = user_repo.content

    assert "public record User" in content
    assert "public class UserRepository" in content
    assert "public async Task<User?> GetByIdAsync(long id)" in content
    assert "await _db.QuerySingleOrDefaultAsync<User>" in content


def test_ts_raw_generator(complex_database_schema):
    """TypeScript direct SQL generator must produce interfaces and pg repositories."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.TS_RAW)
    project = registry.generate(complex_database_schema, request)

    content = project.primary_file_content
    assert "export interface User {" in content
    assert "export class UserRepository {" in content
    assert "async getById(id: number): Promise<User | null>" in content
    assert "INSERT INTO public.users" in content


def test_php_pdo_generator(complex_database_schema):
    """PHP PDO generator must produce DTOs and prepared statement repositories."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.PHP_PDO)
    project = registry.generate(complex_database_schema, request)

    user_repo = next(f for f in project.files if f.path == "Repositories/UserRepository.php")
    content = user_repo.content

    assert "readonly class UserDTO" in content
    assert "class UserRepository" in content
    assert "public function findById(int $id): ?UserDTO" in content
    assert "$stmt->bindValue" in content


def test_go_generator(complex_database_schema):
    """Go generator must produce structs and repository interfaces."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.GO_STRUCTS)
    project = registry.generate(complex_database_schema, request)

    user_model = next(f for f in project.files if f.path == "users.go")
    assert "type User struct {" in user_model.content
    assert 'json:"email"' in user_model.content
    assert 'db:"email"' in user_model.content

    user_repo = next(f for f in project.files if f.path == "repository/users_repo.go")
    assert "type UserRepository interface {" in user_repo.content
    assert "GetByID(ctx context.Context, id int64) (*models.User, error)" in user_repo.content


def test_fastapi_scaffold_generator(complex_database_schema):
    """FastAPI scaffold generator must produce Pydantic schemas, routers, and main.py."""
    registry = GeneratorRegistry.get_instance()
    request = GenerationRequest(target=GenerationTarget.FASTAPI_SCAFFOLD)
    project = registry.generate(complex_database_schema, request)

    schema_file = next(f for f in project.files if f.path == "schemas/users.py")
    assert "class UserBase(BaseModel):" in schema_file.content
    assert "class UserCreate(UserBase):" in schema_file.content
    assert "class UserRead(UserBase):" in schema_file.content

    router_file = next(f for f in project.files if f.path == "routers/users_router.py")
    assert 'router = APIRouter(prefix="/users", tags=["Users"])' in router_file.content
    assert "async def list_users(" in router_file.content
    assert "async def create_user(" in router_file.content

    main_file = next(f for f in project.files if f.path == "main.py")
    assert "from fastapi import FastAPI" in main_file.content
    assert "app.include_router(users_router)" in main_file.content


def test_generators_have_no_gui_or_db_driver_dependencies():
    """Verify that the generators layer is completely decoupled from UI and database drivers."""
    source_modules = [
        "backend_ide.generators.contracts",
        "backend_ide.generators.naming",
        "backend_ide.generators.registry",
        "backend_ide.generators.orm.sqlalchemy_gen",
        "backend_ide.generators.orm.sqlmodel_gen",
        "backend_ide.generators.orm.fastapi_scaffold_gen",
        "backend_ide.generators.orm.django_gen",
        "backend_ide.generators.orm.prisma_gen",
        "backend_ide.generators.orm.drizzle_gen",
        "backend_ide.generators.orm.eloquent_gen",
        "backend_ide.generators.orm.ef_core_gen",
        "backend_ide.generators.orm.go_gen",
        "backend_ide.generators.non_orm.python_raw_gen",
        "backend_ide.generators.non_orm.dapper_gen",
        "backend_ide.generators.non_orm.ts_raw_gen",
        "backend_ide.generators.non_orm.php_pdo_gen",
    ]

    forbidden_imports = ["PySide6", "psycopg", "pymysql", "pyodbc", "sqlite3"]

    for mod_name in source_modules:
        mod = __import__(mod_name, fromlist=["*"])
        source = inspect.getsource(mod)
        for forbidden in forbidden_imports:
            err_msg = f"Module {mod_name} imports forbidden {forbidden}"
            assert f"import {forbidden}" not in source, err_msg
            assert f"from {forbidden}" not in source, err_msg
