from __future__ import annotations

from importlib import import_module

from .provider import SolverProvider


def _load_provider_class(provider_path: str, provider_ref: str) -> type[object]:
    if "." not in provider_path:
        raise ValueError(
            "Invalid provider class path for "
            f"{provider_ref!r}: {provider_path!r}. Expected 'pkg.module.ClassName'.",
        )

    module_path, class_name = provider_path.rsplit(".", 1)
    try:
        module = import_module(module_path)
    except Exception as exc:  # pragma: no cover - import errors are environment-dependent.
        raise ValueError(
            f"Failed to import provider module for {provider_ref!r}: {module_path!r}",
        ) from exc

    try:
        provider_class = getattr(module, class_name)
    except AttributeError as exc:
        raise ValueError(
            "Provider class not found for "
            f"{provider_ref!r}: {provider_path!r}",
        ) from exc

    if not isinstance(provider_class, type):
        raise ValueError(
            f"Provider target must be a class for {provider_ref!r}: {provider_path!r}",
        )

    return provider_class


def _validate_optional_method(
    instance: object,
    provider_ref: str,
    provider_path: str,
    method_name: str,
) -> None:
    method = getattr(instance, method_name, None)
    if method is not None and not callable(method):
        raise ValueError(
            f"Provider {provider_ref!r}: {provider_path!r} has non-callable {method_name}().",
        )


def _validate_solver_protocol(instance: object, provider_ref: str, provider_path: str) -> None:
    solve_fn = getattr(instance, "solve", None)
    if not callable(solve_fn):
        raise ValueError(
            "Provider does not implement SolverProvider.solve(event) for "
            f"{provider_ref!r}: {provider_path!r}",
        )
    _validate_optional_method(
        instance=instance,
        provider_ref=provider_ref,
        provider_path=provider_path,
        method_name="is_available",
    )
    _validate_optional_method(
        instance=instance,
        provider_ref=provider_ref,
        provider_path=provider_path,
        method_name="healthcheck",
    )


def build_solver_providers(
    registry: dict[str, str],
    configs: dict[str, dict[str, object]],
) -> dict[str, SolverProvider]:
    providers: dict[str, SolverProvider] = {}

    for provider_ref, provider_path in registry.items():
        provider_class = _load_provider_class(
            provider_path=provider_path,
            provider_ref=provider_ref,
        )
        kwargs = configs.get(provider_ref, {})
        try:
            instance = provider_class(**kwargs)
        except Exception as exc:  # pragma: no cover - provider-specific constructors.
            raise ValueError(
                "Failed to initialize challenge provider "
                f"{provider_ref!r} with class {provider_path!r}",
            ) from exc

        _validate_solver_protocol(
            instance=instance,
            provider_ref=provider_ref,
            provider_path=provider_path,
        )
        providers[provider_ref] = instance

    return providers
