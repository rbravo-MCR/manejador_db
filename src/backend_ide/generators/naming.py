"""Naming Conventions and String Transformation Utilities for Code Generators."""

from __future__ import annotations

import re

from backend_ide.generators.contracts import Language

# Language-specific reserved keywords (actual syntax keywords that cause SyntaxError)
RESERVED_KEYWORDS: dict[Language, set[str]] = {
    Language.PYTHON: {
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
        "None",
        "True",
        "False",
    },
    Language.TYPESCRIPT: {
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "debugger",
        "default",
        "delete",
        "do",
        "else",
        "enum",
        "export",
        "extends",
        "false",
        "finally",
        "for",
        "function",
        "if",
        "import",
        "in",
        "instanceof",
        "new",
        "null",
        "return",
        "super",
        "switch",
        "this",
        "throw",
        "true",
        "try",
        "typeof",
        "var",
        "void",
        "while",
        "with",
        "yield",
        "let",
        "static",
        "interface",
        "type",
    },
    Language.PHP: {
        "abstract",
        "and",
        "array",
        "as",
        "break",
        "callable",
        "case",
        "catch",
        "class",
        "clone",
        "const",
        "continue",
        "declare",
        "default",
        "die",
        "do",
        "echo",
        "else",
        "elseif",
        "empty",
        "enddeclare",
        "endfor",
        "endforeach",
        "endif",
        "endswitch",
        "endwhile",
        "eval",
        "exit",
        "extends",
        "final",
        "finally",
        "fn",
        "for",
        "foreach",
        "function",
        "global",
        "goto",
        "if",
        "implements",
        "include",
        "include_once",
        "instanceof",
        "insteadof",
        "interface",
        "isset",
        "list",
        "match",
        "namespace",
        "new",
        "or",
        "print",
        "private",
        "protected",
        "public",
        "readonly",
        "require",
        "require_once",
        "return",
        "static",
        "switch",
        "throw",
        "trait",
        "try",
        "unset",
        "use",
        "var",
        "while",
        "xor",
        "yield",
    },
    Language.CSHARP: {
        "abstract",
        "as",
        "base",
        "bool",
        "break",
        "byte",
        "case",
        "catch",
        "char",
        "checked",
        "class",
        "const",
        "continue",
        "decimal",
        "default",
        "delegate",
        "do",
        "double",
        "else",
        "enum",
        "event",
        "explicit",
        "extern",
        "false",
        "finally",
        "fixed",
        "float",
        "for",
        "foreach",
        "goto",
        "if",
        "implicit",
        "in",
        "int",
        "interface",
        "internal",
        "is",
        "lock",
        "long",
        "namespace",
        "new",
        "null",
        "object",
        "operator",
        "out",
        "override",
        "params",
        "private",
        "protected",
        "public",
        "readonly",
        "ref",
        "return",
        "sbyte",
        "sealed",
        "short",
        "sizeof",
        "stackalloc",
        "static",
        "string",
        "struct",
        "switch",
        "this",
        "throw",
        "true",
        "try",
        "typeof",
        "uint",
        "ulong",
        "unchecked",
        "unsafe",
        "ushort",
        "using",
        "virtual",
        "void",
        "volatile",
        "while",
    },
}


def to_snake_case(s: str) -> str:
    """Convert string to snake_case (e.g., 'UserProfile' or 'user-profile' -> 'user_profile')."""
    if not s:
        return ""
    # Replace non-alphanumeric separators with underscore
    s = re.sub(r"[\s\-]+", "_", s)
    # Insert underscore between camelCase boundaries (e.g. UserProfile -> User_Profile)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    # Lowercase everything and collapse multiple underscores
    s = re.sub(r"_+", "_", s.lower())
    return s.strip("_")


def to_pascal_case(s: str) -> str:
    """Convert string to PascalCase (e.g., 'user_profiles' -> 'UserProfiles')."""
    if not s:
        return ""
    words = re.split(r"[\s_\-]+", s)
    return "".join(w.capitalize() for w in words if w)


def to_camel_case(s: str) -> str:
    """Convert string to camelCase (e.g., 'user_profiles' -> 'userProfiles')."""
    pascal = to_pascal_case(s)
    if not pascal:
        return ""
    return pascal[0].lower() + pascal[1:]


def to_kebab_case(s: str) -> str:
    """Convert string to kebab-case (e.g., 'user_profiles' -> 'user-profiles')."""
    return to_snake_case(s).replace("_", "-")


def singularize(name: str) -> str:
    """Singularize an English noun heuristic."""
    s = name.strip()
    if not s:
        return ""

    lower = s.lower()
    # Irregular / special cases
    irregulars = {
        "people": "person",
        "children": "child",
        "men": "man",
        "women": "woman",
        "data": "datum",
        "matrices": "matrix",
        "indices": "index",
        "vertices": "vertex",
        "statuses": "status",
        "addresses": "address",
        "categories": "category",
        "companies": "company",
        "cities": "city",
        "countries": "country",
        "activities": "activity",
        "policies": "policy",
    }
    if lower in irregulars:
        res = irregulars[lower]
        return res.capitalize() if s[0].isupper() else res

    # Ends in 'ies' -> 'y' (e.g. categories -> category)
    if lower.endswith("ies") and len(lower) > 3 and lower[-4] not in "aeiou":
        res = s[:-3] + ("y" if s[-1].islower() else "Y")
        return res

    # Ends in 'es' where preceding is s, x, z, ch, sh (e.g. boxes -> box, watches -> watch)
    if lower.endswith("es"):
        for suffix in ("sses", "shes", "ches", "xes", "zes"):
            if lower.endswith(suffix):
                return s[:-2]

    # Ends in single 's' but not 'ss', 'us', 'is' (e.g. users -> user)
    if lower.endswith("s") and not lower.endswith(("ss", "us", "is")):
        return s[:-1]

    return s


def pluralize(name: str) -> str:
    """Pluralize an English noun heuristic."""
    s = name.strip()
    if not s:
        return ""

    lower = s.lower()
    irregulars = {
        "person": "people",
        "child": "children",
        "man": "men",
        "woman": "women",
        "datum": "data",
        "matrix": "matrices",
        "index": "indices",
        "status": "statuses",
        "address": "addresses",
        "category": "categories",
        "company": "companies",
        "city": "cities",
        "country": "countries",
        "activity": "activities",
        "policy": "policies",
    }
    if lower in irregulars:
        res = irregulars[lower]
        return res.capitalize() if s[0].isupper() else res

    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return s[:-1] + ("ies" if s[-1].islower() else "IES")

    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return s + ("es" if s[-1].islower() else "ES")

    return s + ("s" if s[-1].islower() else "S")


def sanitize_identifier(name: str, language: Language = Language.PYTHON) -> str:
    """Ensure an identifier is safe for syntax in the target language."""
    clean = to_snake_case(name)
    reserved = RESERVED_KEYWORDS.get(language, set())
    if clean in reserved:
        return f"{clean}_"
    # Ensure it doesn't start with a digit
    if clean and clean[0].isdigit():
        return f"col_{clean}"
    return clean or "field"


def table_to_class_name(table_name: str, singular: bool = True) -> str:
    """Convert database table name to language class name (e.g. 'users' -> 'User')."""
    cleaned = table_name
    if singular:
        cleaned = singularize(cleaned)
    return to_pascal_case(cleaned)
