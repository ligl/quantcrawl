from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from quantcrawl.challenge import build_solver_providers


def _write_provider_module(tmp_path: Path, module_name: str, body: str) -> str:
    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(textwrap.dedent(body), encoding="utf-8")
    return module_name


def test_build_solver_providers_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = _write_provider_module(
        tmp_path,
        "good_provider_mod",
        """
        class DemoProvider:
            name = "demo"

            def __init__(self, api_key: str) -> None:
                self.api_key = api_key

            def solve(self, event) -> bool:
                return bool(self.api_key and event)
        """,
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    providers = build_solver_providers(
        registry={"demo": f"{module_name}.DemoProvider"},
        configs={"demo": {"api_key": "secret"}},
    )

    assert "demo" in providers
    assert providers["demo"].api_key == "secret"  # type: ignore[attr-defined]


def test_build_solver_providers_raises_on_import_error() -> None:
    with pytest.raises(ValueError, match="Failed to import provider module"):
        build_solver_providers(
            registry={"demo": "not_exists.module.DemoProvider"},
            configs={},
        )


def test_build_solver_providers_raises_on_constructor_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = _write_provider_module(
        tmp_path,
        "ctor_provider_mod",
        """
        class DemoProvider:
            name = "demo"

            def __init__(self, required_token: str) -> None:
                self.required_token = required_token

            def solve(self, event) -> bool:
                return True
        """,
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    with pytest.raises(ValueError, match="Failed to initialize challenge provider"):
        build_solver_providers(
            registry={"demo": f"{module_name}.DemoProvider"},
            configs={"demo": {}},
        )


def test_build_solver_providers_raises_when_protocol_not_implemented(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = _write_provider_module(
        tmp_path,
        "bad_provider_mod",
        """
        class DemoProvider:
            name = "demo"
        """,
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    with pytest.raises(ValueError, match="does not implement SolverProvider.solve"):
        build_solver_providers(
            registry={"demo": f"{module_name}.DemoProvider"},
            configs={"demo": {}},
        )


def test_build_solver_providers_raises_when_optional_method_is_not_callable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = _write_provider_module(
        tmp_path,
        "bad_optional_provider_mod",
        """
        class DemoProvider:
            name = "demo"
            is_available = True

            def solve(self, event) -> bool:
                return bool(event)
        """,
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    with pytest.raises(ValueError, match="non-callable is_available"):
        build_solver_providers(
            registry={"demo": f"{module_name}.DemoProvider"},
            configs={"demo": {}},
        )
