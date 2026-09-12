"""Pure admission and one-shot control-plane primitives for CORE-1E-B2-B.

The caller owns the closed-world control specification and all scientific
meaning.  This module only admits committed control blobs, guards the Git
checkout, and consumes one injected operation exactly once.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping


_ACTIVATION_SCHEMA = "lily_core_1e_b2b_r1_activation_v1"
_MARKER_SCHEMA = "lily_core_1e_b2b_r1_one_shot_marker_v1"
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_COMMIT = re.compile(r"[0-9a-fA-F]{40}\Z")


class ControlPlaneError(RuntimeError):
    """Base error for a refused or unfinishable control-plane transition."""


class AdmissionRefused(ControlPlaneError):
    """The checkout or committed provenance did not satisfy the spec."""


class ActivationRefused(AdmissionRefused):
    """The committed activation or its provenance is not admissible."""


class DirtyCheckoutRefused(AdmissionRefused):
    """The checkout contains a path outside the exact untracked allowlist."""


class SecondInvocationRefused(ControlPlaneError):
    """The one-shot marker already exists."""


def _normalise_relpath(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("relative path must be a non-empty string")
    if "\\" in value or ":" in value or value.startswith("/"):
        raise ValueError("path must use a safe repository-relative form")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("path must not contain traversal or empty components")
    normalised = path.as_posix()
    if normalised != value:
        raise ValueError("path must be canonically slash-separated")
    return normalised


def _normalise_hash(value: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError("expected a SHA-256 hex digest")
    return value.lower()


def _normalise_commit(value: str) -> str:
    if not isinstance(value, str) or _COMMIT.fullmatch(value) is None:
        raise ValueError("expected a full Git commit hex object ID")
    return value.lower()


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("closed-world control spec must be JSON data") from exc


@dataclass(frozen=True)
class ControlSpec:
    """Caller-supplied paths, hashes, and opaque closed-world control data."""

    repo_root: Path | str
    activation_path: str
    expected_activation_sha256: str
    source_commit: str
    gate_path: str
    expected_gate_sha256: str
    runtime_paths: tuple[str, ...]
    expected_runtime_sha256: tuple[str, ...]
    marker_path: str
    allowed_untracked_paths: tuple[str, ...] = ()
    closed_world: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "repo_root", Path(self.repo_root))
        activation = _normalise_relpath(self.activation_path)
        gate = _normalise_relpath(self.gate_path)
        marker = _normalise_relpath(self.marker_path)
        runtime = tuple(_normalise_relpath(path) for path in self.runtime_paths)
        allowed = tuple(_normalise_relpath(path) for path in self.allowed_untracked_paths)
        if len(set(runtime)) != len(runtime):
            raise ValueError("runtime paths must be unique")
        if len(set(allowed)) != len(allowed):
            raise ValueError("allowlisted paths must be unique")
        if len(runtime) != len(self.expected_runtime_sha256):
            raise ValueError("runtime paths and hashes must have equal length")
        control_paths = {activation, gate, marker, *runtime}
        if control_paths.intersection(allowed):
            raise ValueError("allowlisted paths must not be control paths")
        object.__setattr__(self, "activation_path", activation)
        object.__setattr__(self, "gate_path", gate)
        object.__setattr__(self, "marker_path", marker)
        object.__setattr__(self, "runtime_paths", runtime)
        object.__setattr__(self, "allowed_untracked_paths", allowed)
        object.__setattr__(
            self,
            "expected_activation_sha256",
            _normalise_hash(self.expected_activation_sha256),
        )
        object.__setattr__(self, "source_commit", _normalise_commit(self.source_commit))
        object.__setattr__(self, "expected_gate_sha256", _normalise_hash(self.expected_gate_sha256))
        runtime_hashes = tuple(_normalise_hash(value) for value in self.expected_runtime_sha256)
        object.__setattr__(self, "expected_runtime_sha256", runtime_hashes)
        if not isinstance(self.closed_world, Mapping):
            raise ValueError("closed_world must be a JSON object")
        encoded = _canonical_json(dict(self.closed_world))
        object.__setattr__(self, "closed_world", json.loads(encoded.decode("utf-8")))


@dataclass(frozen=True)
class Admission:
    """Verified control-plane provenance handed to injected callbacks."""

    repo_root: Path
    activation_path: Path
    gate_path: str
    runtime_paths: tuple[str, ...]
    marker_path: Path
    source_commit: str
    activation_sha256: str
    gate_sha256: str
    runtime_sha256: tuple[str, ...]
    closed_world: Mapping[str, Any]


def _git_run(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ("git", "-C", os.fspath(repo), *args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise AdmissionRefused("Git is unavailable for control-plane admission") from exc


def _git_blob(repo: Path, revision: str, path: str) -> bytes:
    object_name = f"{revision}:{path}"
    kind = _git_run(repo, "cat-file", "-t", object_name)
    if kind.returncode != 0 or kind.stdout.strip() != b"blob":
        raise ActivationRefused("required committed control blob is absent or not a blob")
    blob = _git_run(repo, "show", object_name)
    if blob.returncode != 0:
        raise ActivationRefused("required committed control blob cannot be read")
    return blob.stdout


def _head(repo: Path) -> str:
    result = _git_run(repo, "rev-parse", "--verify", "HEAD^{commit}")
    if result.returncode != 0:
        raise AdmissionRefused("repository HEAD is unavailable")
    try:
        value = result.stdout.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise AdmissionRefused("repository HEAD is not valid ASCII") from exc
    try:
        return _normalise_commit(value)
    except ValueError as exc:
        raise AdmissionRefused("repository HEAD is not a full commit ID") from exc


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = _git_run(repo, "merge-base", "--is-ancestor", ancestor, descendant)
    if result.returncode not in (0, 1):
        raise AdmissionRefused("provenance commit cannot be verified")
    return result.returncode == 0


def _parse_json(raw: bytes) -> Any:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"invalid JSON constant: {value}")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=no_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise ActivationRefused("activation is not unambiguous UTF-8 JSON") from exc


def _worktree_control_bytes(repo: Path, path: str) -> bytes:
    target = repo.joinpath(*path.split("/"))
    parent = repo
    for component in path.split("/")[:-1]:
        if parent.is_symlink():
            raise ActivationRefused("activation path has a symlinked parent")
        parent /= component
    if parent.is_symlink() or target.is_symlink():
        raise ActivationRefused("activation path must not traverse a symlink")
    try:
        return target.read_bytes()
    except OSError as exc:
        raise ActivationRefused("committed activation is absent from the worktree") from exc


def _check_activation_payload(payload: Any, spec: ControlSpec) -> None:
    expected_keys = {"schema", "activation_id", "source_commit", "gate", "runtime", "control_spec"}
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ActivationRefused("activation fields are outside the closed control contract")
    if payload["schema"] != _ACTIVATION_SCHEMA:
        raise ActivationRefused("activation schema does not match CP1")
    if not isinstance(payload["activation_id"], str) or not payload["activation_id"]:
        raise ActivationRefused("activation ID is missing")
    try:
        source_commit = _normalise_commit(payload["source_commit"])
    except ValueError as exc:
        raise ActivationRefused("activation source commit is invalid") from exc
    if source_commit != spec.source_commit:
        raise ActivationRefused("activation source commit differs from the caller spec")
    gate = payload["gate"]
    if not isinstance(gate, dict) or set(gate) != {"path", "sha256"}:
        raise ActivationRefused("activation gate binding is not closed-world")
    try:
        gate_path = _normalise_relpath(gate["path"])
        gate_hash = _normalise_hash(gate["sha256"])
    except ValueError as exc:
        raise ActivationRefused("activation gate binding is invalid") from exc
    if gate_path != spec.gate_path or gate_hash != spec.expected_gate_sha256:
        raise ActivationRefused("activation gate provenance differs from the caller spec")
    runtime = payload["runtime"]
    if not isinstance(runtime, list) or len(runtime) != len(spec.runtime_paths):
        raise ActivationRefused("activation runtime binding has the wrong shape")
    for entry, expected_path, expected_hash in zip(
        runtime, spec.runtime_paths, spec.expected_runtime_sha256
    ):
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ActivationRefused("activation runtime binding is not closed-world")
        try:
            runtime_path = _normalise_relpath(entry["path"])
            runtime_hash = _normalise_hash(entry["sha256"])
        except ValueError as exc:
            raise ActivationRefused("activation runtime binding is invalid") from exc
        if runtime_path != expected_path or runtime_hash != expected_hash:
            raise ActivationRefused("activation runtime provenance differs from the caller spec")
    control_spec = payload["control_spec"]
    if not isinstance(control_spec, dict):
        raise ActivationRefused("activation closed-world spec is not an object")
    if _canonical_json(control_spec) != _canonical_json(dict(spec.closed_world)):
        raise ActivationRefused("activation closed-world spec differs from the caller spec")


def _status_paths(repo: Path) -> list[tuple[str, str]]:
    result = _git_run(
        repo,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if result.returncode != 0:
        raise AdmissionRefused("Git worktree status cannot be obtained")
    entries: list[tuple[str, str]] = []
    for token in result.stdout.split(b"\0"):
        if not token:
            continue
        if len(token) < 4 or token[2:3] != b" ":
            raise DirtyCheckoutRefused("Git status contains an unsupported path record")
        try:
            code = token[:2].decode("ascii")
            path = token[3:].decode("utf-8", "surrogateescape")
        except UnicodeDecodeError as exc:
            raise DirtyCheckoutRefused("Git status contains a non-UTF-8 path") from exc
        try:
            path = _normalise_relpath(path)
        except ValueError as exc:
            raise DirtyCheckoutRefused("Git status contains an unsafe path") from exc
        entries.append((code, path))
    ignored = _git_run(repo, "ls-files", "--others", "--ignored", "--exclude-standard", "-z")
    if ignored.returncode != 0:
        raise AdmissionRefused("Git ignored-path status cannot be obtained")
    for token in ignored.stdout.split(b"\0"):
        if not token:
            continue
        try:
            path = _normalise_relpath(token.decode("utf-8", "surrogateescape"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise DirtyCheckoutRefused("Git ignored-path status contains an unsafe path") from exc
        entries.append(("!!", path))
    return entries


def _guard_clean_checkout(spec: ControlSpec) -> None:
    allowed = set(spec.allowed_untracked_paths)
    allowed.add(spec.marker_path)
    for code, path in _status_paths(spec.repo_root):
        if code in ("??", "!!") and path in allowed:
            continue
        raise DirtyCheckoutRefused(f"checkout path is not allowlisted: {code} {path}")


def _marker_must_be_untracked(spec: ControlSpec) -> None:
    result = _git_run(spec.repo_root, "ls-files", "--error-unmatch", "--", spec.marker_path)
    if result.returncode == 0 and result.stdout.strip():
        raise ActivationRefused("one-shot marker path must not be tracked")


def admit(spec: ControlSpec) -> Admission:
    """Admit a committed activation and exact control provenance, without callbacks."""

    if not isinstance(spec, ControlSpec):
        raise TypeError("spec must be a ControlSpec")
    repo = spec.repo_root
    head = _head(repo)
    if not _is_ancestor(repo, spec.source_commit, head):
        raise ActivationRefused("activation source commit is not an ancestor of HEAD")
    activation_blob = _git_blob(repo, "HEAD", spec.activation_path)
    if hashlib.sha256(activation_blob).hexdigest() != spec.expected_activation_sha256:
        raise ActivationRefused("committed activation hash differs from the caller spec")
    if _worktree_control_bytes(repo, spec.activation_path) != activation_blob:
        raise ActivationRefused("worktree activation differs from its committed bytes")
    _check_activation_payload(_parse_json(activation_blob), spec)
    for revision in (spec.source_commit, "HEAD"):
        gate_blob = _git_blob(repo, revision, spec.gate_path)
        if hashlib.sha256(gate_blob).hexdigest() != spec.expected_gate_sha256:
            raise ActivationRefused("gate blob differs from exact provenance")
        for path, expected_hash in zip(spec.runtime_paths, spec.expected_runtime_sha256):
            runtime_blob = _git_blob(repo, revision, path)
            if hashlib.sha256(runtime_blob).hexdigest() != expected_hash:
                raise ActivationRefused("runtime blob differs from exact provenance")
    _guard_clean_checkout(spec)
    _marker_must_be_untracked(spec)
    return Admission(
        repo_root=repo,
        activation_path=repo.joinpath(*spec.activation_path.split("/")),
        gate_path=spec.gate_path,
        runtime_paths=spec.runtime_paths,
        marker_path=repo.joinpath(*spec.marker_path.split("/")),
        source_commit=spec.source_commit,
        activation_sha256=spec.expected_activation_sha256,
        gate_sha256=spec.expected_gate_sha256,
        runtime_sha256=spec.expected_runtime_sha256,
        closed_world=spec.closed_world,
    )


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short marker write")
        view = view[written:]


def _marker_bytes(payload: Mapping[str, Any]) -> bytes:
    return _canonical_json(dict(payload))


def _claim_marker(admission: Admission) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": _MARKER_SCHEMA,
        "state": "claimed",
        "completion_count": 0,
        "activation_sha256": admission.activation_sha256,
        "source_commit": admission.source_commit,
        "gate_sha256": admission.gate_sha256,
        "runtime": [
            {"path": path, "sha256": digest}
            for path, digest in zip(admission.runtime_paths, admission.runtime_sha256)
        ],
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        fd = os.open(os.fspath(admission.marker_path), flags, 0o600)
    except FileExistsError as exc:
        raise SecondInvocationRefused("one-shot marker already exists") from exc
    except OSError as exc:
        raise ControlPlaneError("one-shot marker could not be claimed") from exc
    try:
        _write_all(fd, _marker_bytes(payload))
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_directory(os.fspath(admission.marker_path.parent))
    return payload


def _fsync_directory(directory: str) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _replace_marker(admission: Admission, payload: Mapping[str, Any]) -> None:
    directory = os.fspath(admission.marker_path.parent)
    fd: int | None = None
    temporary: str | None = None
    try:
        fd, temporary = tempfile.mkstemp(
            prefix=f".{admission.marker_path.name}.",
            suffix=".tmp",
            dir=directory,
        )
        if hasattr(os, "O_BINARY"):
            # mkstemp is already binary on supported platforms; this branch is documentary.
            pass
        _write_all(fd, _marker_bytes(payload))
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.replace(temporary, os.fspath(admission.marker_path))
        temporary = None
        _fsync_directory(directory)
    except OSError as exc:
        raise ControlPlaneError("terminal marker state could not be persisted") from exc
    finally:
        if fd is not None:
            os.close(fd)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _terminal_payload(
    claimed: Mapping[str, Any], state: str, error: BaseException | None = None
) -> dict[str, Any]:
    payload = dict(claimed)
    payload["state"] = state
    payload["completion_count"] = 1
    if error is not None:
        payload["error_type"] = type(error).__name__
    return payload


def execute_once(
    spec: ControlSpec,
    resolver: Callable[[Admission], Any],
    operation: Callable[[Any], Any],
) -> Any:
    """Admit, atomically claim, then run one injected operation exactly once."""

    if not callable(resolver) or not callable(operation):
        raise TypeError("resolver and operation must be callable")
    admission = admit(spec)
    claimed = _claim_marker(admission)
    try:
        resolved = resolver(admission)
        result = operation(resolved)
    except BaseException as error:
        _replace_marker(admission, _terminal_payload(claimed, "failed", error))
        raise
    try:
        _replace_marker(admission, _terminal_payload(claimed, "completed"))
    except BaseException as error:
        try:
            _replace_marker(admission, _terminal_payload(claimed, "failed", error))
        except BaseException:
            pass
        raise
    return result
