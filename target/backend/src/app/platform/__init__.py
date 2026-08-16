"""Company platform / DLL compatibility boundary.

This package is the sole namespace for host/platform integration *behavior*
in the target backend: host communication, process management, DLL/assembly
loading, host-specific callbacks. It is scoped to behavior, not to every
host-shaped data type — a host-agnostic, protocol-typed request dependency
declared in ``app.api`` (e.g. a ``Protocol`` describing "the caller's
identity/session", satisfied via FastAPI's ``app.dependency_overrides`` at
the composition root in ``app.main``) is not a violation of the sole-
namespace rule, because the route stays unaware of *which* platform
implementation is bound. See ADR-0005 amendment (post-review) for the
scoping rationale.

Per the design rule in docs/04-dll-integration-boundary.md ("Platform-specific
integration must remain outside core business logic") and RULEBOOK
Platform/DLL #1-#2, ``app.api``, ``app.services``, ``app.repositories`` and
``app.domain`` must never import this package; the enforced guard lives in
pyproject.toml ([tool.importlinter], both the layers contract with
``app.platform`` on top and the dedicated forbidden contract). The reverse
direction is allowed but constrained: an adapter here may call into
``app.services`` and ``app.domain``, but not reach directly into
``app.repositories`` (separate forbidden contract) — the adapter is a caller
of business/application APIs like any other caller, not a shortcut around
the service layer.

The actual DLL/host contract is not confirmed yet (OQ-001..OQ-009 are OPEN),
and whether a compatibility DLL is adopted at all is unresolved (RULEBOOK
Platform/DLL #3). Therefore this package intentionally contains no
implementation beyond the marker port below: no host communication, no
process management, no DLL or assembly loading, no host-specific callbacks.
Code lands here only after the host contract is confirmed (ADR-0005).

Note: this package's name shadows the stdlib ``platform`` module. Harmless
under Python 3 absolute imports, but avoid ``import platform`` for the
stdlib module from inside this package without an explicit alias.
"""

import abc


class PlatformPort(abc.ABC):  # noqa: B024  # deliberately no abstract methods until the host contract is confirmed (ADR-0005, OQ-001..009)
    """Marker for the future platform adapter port (extension point only).

    Deliberately empty: the host contract is unknown (OQ-001..OQ-009 OPEN),
    so declaring a method surface now would be inference, not evidence.
    Extend only from confirmed host-contract evidence, never by guessing.
    """
