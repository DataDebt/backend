import ast
from pathlib import Path


def _load_migration_module(tree: ast.Module) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            return node
    raise AssertionError("upgrade() function not found in migration")


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        func = node.func
        parts: list[str] = []
        while isinstance(func, ast.Attribute):
            parts.append(func.attr)
            func = func.value
        if isinstance(func, ast.Name):
            parts.append(func.id)
            return ".".join(reversed(parts))
    raise AssertionError(f"Unexpected call node: {ast.dump(node)}")


def _constant(node: ast.AST) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    raise AssertionError(f"Unexpected constant node: {ast.dump(node)}")


def _keyword_value(call: ast.Call, name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _column_names(create_table_call: ast.Call) -> set[str]:
    names: set[str] = set()
    for arg in create_table_call.args[1:]:
        if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute):
            if arg.func.attr == "Column" and arg.args:
                names.add(str(_constant(arg.args[0])))
    return names


def _find_call_nodes(tree: ast.Module, dotted_name: str) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) == dotted_name:
            calls.append(node)
    return calls


def test_alembic_entrypoints_and_initial_auth_migration_exist() -> None:
    project_root = Path(__file__).resolve().parents[2]
    alembic_dir = project_root / "alembic"
    versions_dir = alembic_dir / "versions"

    assert (project_root / "alembic.ini").is_file()
    assert (alembic_dir / "env.py").is_file()
    assert (alembic_dir / "script.py.mako").is_file()
    assert "sqlalchemy.url =" in (project_root / "alembic.ini").read_text(encoding="utf-8")
    assert "postgresql+asyncpg://user:pass@localhost:5432/app" not in (
        project_root / "alembic.ini"
    ).read_text(encoding="utf-8")
    env_text = (alembic_dir / "env.py").read_text(encoding="utf-8")
    assert "DATABASE_URL is required for Alembic migrations" in env_text
    assert "config.set_main_option(\"sqlalchemy.url\", database_url)" in env_text

    migration_files = sorted(versions_dir.glob("*_create_auth_tables.py"))
    assert len(migration_files) == 1

    migration_text = migration_files[0].read_text(encoding="utf-8")
    tree = ast.parse(migration_text)
    upgrade = _load_migration_module(tree)

    create_tables = {
        str(_constant(call.args[0]))
        for call in _find_call_nodes(ast.Module(body=upgrade.body, type_ignores=[]), "op.create_table")
    }
    assert create_tables == {
        "users",
        "email_verification_tokens",
        "refresh_tokens",
        "password_reset_tokens",
    }

    create_indexes = {
        str(_constant(call.args[0])): call
        for call in _find_call_nodes(ast.Module(body=upgrade.body, type_ignores=[]), "op.create_index")
    }
    assert "uq_users_email_lower" in create_indexes
    assert "ix_email_verification_tokens_token_hash" in create_indexes
    assert "ix_refresh_tokens_token_hash" in create_indexes
    assert "ix_password_reset_tokens_token_hash" in create_indexes

    lower_email_index = create_indexes["uq_users_email_lower"]
    assert _constant(_keyword_value(lower_email_index, "unique")) is True
    assert isinstance(lower_email_index.args[2], ast.List)
    assert _call_name(lower_email_index.args[2].elts[0]) == "sa.text"
    assert _constant(lower_email_index.args[2].elts[0].args[0]) == "lower(email)"

    token_index_names = {
        name
        for name, call in create_indexes.items()
        if _constant(_keyword_value(call, "unique")) is True
    }
    assert token_index_names.issuperset(
        {
            "ix_email_verification_tokens_token_hash",
            "ix_refresh_tokens_token_hash",
            "ix_password_reset_tokens_token_hash",
        }
    )

    table_calls = {
        str(_constant(call.args[0])): call
        for call in _find_call_nodes(ast.Module(body=upgrade.body, type_ignores=[]), "op.create_table")
    }
    for token_table in (
        "email_verification_tokens",
        "refresh_tokens",
        "password_reset_tokens",
    ):
        table_call = table_calls[token_table]
        assert "user_id" in _column_names(table_call)
        fk_constraints = [
            arg
            for arg in table_call.args[1:]
            if isinstance(arg, ast.Call)
            and isinstance(arg.func, ast.Attribute)
            and arg.func.attr == "ForeignKeyConstraint"
        ]
        assert len(fk_constraints) == 1
        ondelete = _keyword_value(fk_constraints[0], "ondelete")
        assert _constant(ondelete) == "CASCADE"

    users_table = table_calls["users"]
    assert _column_names(users_table) == {
        "id",
        "email",
        "username",
        "password_hash",
        "is_active",
        "is_verified",
        "created_at",
        "updated_at",
        "last_login_at",
    }
