"""Code Generator Registry for Dynamic Dispatch and Plugin Discovery."""

from __future__ import annotations

from backend_ide.domain.schema.models import DatabaseSchema
from backend_ide.generators.contracts import (
    CodeGenerator,
    GeneratedProject,
    GenerationRequest,
    GenerationTarget,
    GeneratorCategory,
    Language,
)
from backend_ide.generators.non_orm.dapper_gen import DapperGenerator
from backend_ide.generators.non_orm.php_pdo_gen import PHPPdoGenerator
from backend_ide.generators.non_orm.python_raw_gen import PythonRawGenerator
from backend_ide.generators.non_orm.ts_raw_gen import TSRawGenerator
from backend_ide.generators.orm.django_gen import DjangoModelGenerator
from backend_ide.generators.orm.drizzle_gen import DrizzleGenerator
from backend_ide.generators.orm.ef_core_gen import EFCoreGenerator
from backend_ide.generators.orm.eloquent_gen import EloquentGenerator
from backend_ide.generators.orm.fastapi_scaffold_gen import FastAPIScaffoldGenerator
from backend_ide.generators.orm.go_gen import GoGenerator
from backend_ide.generators.orm.prisma_gen import PrismaGenerator
from backend_ide.generators.orm.sqlalchemy_gen import SQLAlchemyGenerator
from backend_ide.generators.orm.sqlmodel_gen import SQLModelGenerator


class GeneratorRegistry:
    """Central registry of all available code generator implementations."""

    _instance: GeneratorRegistry | None = None

    def __init__(self) -> None:
        self._generators: dict[GenerationTarget, CodeGenerator] = {}
        self._register_default_generators()

    @classmethod
    def get_instance(cls) -> GeneratorRegistry:
        """Get singleton instance of the registry."""
        if cls._instance is None:
            cls._instance = GeneratorRegistry()
        return cls._instance

    def register(self, generator: CodeGenerator) -> None:
        """Register a new CodeGenerator implementation."""
        self._generators[generator.target] = generator

    def get(self, target: GenerationTarget | str) -> CodeGenerator | None:
        """Find generator by target enum or string identifier."""
        if isinstance(target, str):
            try:
                target = GenerationTarget(target)
            except ValueError:
                return None
        return self._generators.get(target)

    def list_all(self) -> list[CodeGenerator]:
        """Return list of all registered generators."""
        return list(self._generators.values())

    def list_by_language(self, language: Language) -> list[CodeGenerator]:
        """Filter registered generators by programming language."""
        return [g for g in self._generators.values() if g.language == language]

    def list_by_category(self, category: GeneratorCategory) -> list[CodeGenerator]:
        """Filter registered generators by category (ORM, Non-ORM, Scaffold)."""
        return [g for g in self._generators.values() if g.category == category]

    def generate(self, schema: DatabaseSchema, request: GenerationRequest) -> GeneratedProject:
        """Dispatch a generation request to the appropriate generator."""
        generator = self.get(request.target)
        if not generator:
            raise ValueError(f"No generator registered for target: '{request.target}'")
        return generator.generate(schema, request)

    def _register_default_generators(self) -> None:
        """Instantiate and register all built-in generators."""
        defaults: list[CodeGenerator] = [
            # ORM / Model Generators
            SQLAlchemyGenerator(),
            SQLModelGenerator(),
            FastAPIScaffoldGenerator(),
            DjangoModelGenerator(),
            PrismaGenerator(),
            DrizzleGenerator(),
            EloquentGenerator(),
            EFCoreGenerator(),
            GoGenerator(),
            # Non-ORM / Raw Data Access Generators
            PythonRawGenerator(),
            DapperGenerator(),
            TSRawGenerator(),
            PHPPdoGenerator(),
        ]
        for gen in defaults:
            self.register(gen)
