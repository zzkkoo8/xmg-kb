#!/usr/bin/env python3
"""Resolve official Phase 1 evidence into an immutable component lock.

Remote bytes are parsed only. The resolver never executes downloaded content,
pulls images, or starts containers. A component becomes RESOLVED only when all
required evidence layers close; otherwise its BLOCKED reason is derived from
the probes that were actually attempted.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


USER_AGENT = "xmg-kb-phase1-version-resolver/2"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_MODEL_AUX_FILES = 16
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "components-lock.schema.json"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MUTABLE_RE = re.compile(
    r"(?:^|[/._-])(?:latest|main|master|stable|develop|development|dev|nightly|snapshot)(?:$|[/._-])",
    re.IGNORECASE,
)
RFC3339_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
TRUSTED_SPDX_IDS = {
    "AGPL-3.0-only", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "BSL-1.1", "GPL-2.0-only", "GPL-3.0-only", "MIT", "MPL-2.0",
}
# Hugging Face model cards occasionally use the pre-3.0 SPDX short forms.
# Keep the accepted surface deliberately small and canonicalize those aliases
# before they reach the immutable lock schema.
SPDX_ALIASES = {
    "AGPL-3.0": "AGPL-3.0-only",
    "GPL-2.0": "GPL-2.0-only",
    "GPL-3.0": "GPL-3.0-only",
}


@dataclass(frozen=True)
class HttpResult:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    headers: dict[str, str]
    body: bytes


class Transport(Protocol):
    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResult: ...


class HttpTransport:
    """Bounded HTTPS transport that returns HTTP failures as inspectable data."""

    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResult:
        request_headers = {"User-Agent": USER_AGENT}
        request_headers.update(headers or {})
        request = Request(url, headers=request_headers, method="GET")
        try:
            with urlopen(request, timeout=8) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise RuntimeError(f"response exceeded {MAX_RESPONSE_BYTES} bytes")
                return HttpResult(
                    requested_url=url,
                    final_url=response.geturl(),
                    status=getattr(response, "status", 200),
                    content_type=response.headers.get_content_type(),
                    headers={key.lower(): value for key, value in response.headers.items()},
                    body=body,
                )
        except HTTPError as exc:
            body = exc.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise RuntimeError(f"error response exceeded {MAX_RESPONSE_BYTES} bytes")
            return HttpResult(
                requested_url=url,
                final_url=exc.geturl(),
                status=exc.code,
                content_type=exc.headers.get_content_type(),
                headers={key.lower(): value for key, value in exc.headers.items()},
                body=body,
            )


@dataclass(frozen=True)
class ComponentSpec:
    component: str
    gate_role: str
    deployment_mode: str
    release_url: str
    docs_url: str
    repository: str | None = None
    deployment_candidates: tuple[str, ...] = ()
    license_candidates: tuple[str, ...] = ("LICENSE", "LICENSE.md", "COPYING")
    model_urls: tuple[str, ...] = ()
    main_image_repositories: tuple[str, ...] = ()


SPECS = (
    ComponentSpec(
        "outline", "required", "compose",
        "https://api.github.com/repos/outline/outline/releases/latest",
        "https://docs.getoutline.com/s/hosting/doc/docker-7pfeLP5a8t",
        "outline/outline", ("docker-compose.yml", "docker-compose.yaml"),
        main_image_repositories=("outlinewiki/outline",),
    ),
    ComponentSpec(
        "prefect", "required", "compose",
        "https://api.github.com/repos/PrefectHQ/prefect/releases/latest",
        "https://docs.prefect.io/v3/how-to-guides/self-hosted/server/",
        "PrefectHQ/prefect", ("docker-compose.yml", "docker-compose.yaml"),
        main_image_repositories=("prefecthq/prefect",),
    ),
    ComponentSpec(
        "docling-serve", "required", "compose",
        "https://api.github.com/repos/docling-project/docling-serve/releases/latest",
        "https://github.com/docling-project/docling-serve",
        "docling-project/docling-serve", ("docker-compose.yml", "docker-compose.yaml"),
        model_urls=("https://huggingface.co/api/models/ibm-granite/granite-docling-258M?blobs=true",),
        main_image_repositories=("docling-project/docling-serve",),
    ),
    ComponentSpec(
        "mineru", "required", "container-cli",
        "https://api.github.com/repos/opendatalab/MinerU/releases/latest",
        "https://github.com/opendatalab/MinerU",
        "opendatalab/MinerU", ("docker-compose.yml", "docker-compose.yaml", "docker/compose.yaml", "Dockerfile"),
        model_urls=("https://huggingface.co/api/models/opendatalab/PDF-Extract-Kit-1.0?blobs=true",),
        main_image_repositories=("opendatalab/mineru", "mineru"),
    ),
    ComponentSpec(
        "ragflow", "required", "compose",
        "https://api.github.com/repos/infiniflow/ragflow/releases/latest",
        "https://docs.ragflow.io/",
        "infiniflow/ragflow", ("docker/docker-compose.yml", "docker/docker-compose.yaml"),
        main_image_repositories=("infiniflow/ragflow", "ragflow"),
    ),
    ComponentSpec(
        "langfuse", "required", "compose",
        "https://api.github.com/repos/langfuse/langfuse/releases/latest",
        "https://langfuse.com/self-hosting/deployment/docker-compose",
        "langfuse/langfuse", ("docker-compose.yml", "docker-compose.yaml"),
        main_image_repositories=("langfuse/langfuse",),
    ),
    ComponentSpec(
        "libreoffice", "required", "native-package",
        "https://www.libreoffice.org/download/download-libreoffice/",
        "https://www.libreoffice.org/get-help/install-howto/linux/",
    ),
    ComponentSpec(
        "clamav", "required", "compose",
        "https://api.github.com/repos/Cisco-Talos/clamav/releases/latest",
        "https://docs.clamav.net/manual/Installing/Docker.html",
        "Cisco-Talos/clamav", ("docker-compose.yml", "docker-compose.yaml", "Dockerfile"),
        main_image_repositories=("clamav/clamav",),
    ),
    ComponentSpec(
        "kag-poc", "optional", "compose",
        "https://api.github.com/repos/OpenSPG/KAG/releases/latest",
        "https://github.com/OpenSPG/KAG",
        "OpenSPG/KAG", ("docker-compose.yml", "docker-compose.yaml"),
        main_image_repositories=("openspg/kag", "kag"),
    ),
)


OFFICIAL_SOURCE_PREFIXES = {
    "outline": ("https://github.com/outline/outline/",),
    "prefect": ("https://github.com/PrefectHQ/prefect/",),
    "docling-serve": ("https://github.com/docling-project/docling-serve/",),
    "mineru": ("https://github.com/opendatalab/MinerU/",),
    "ragflow": ("https://github.com/infiniflow/ragflow/",),
    "langfuse": ("https://github.com/langfuse/langfuse/",),
    "libreoffice": ("https://packages.ubuntu.com/", "https://www.libreoffice.org/"),
    "clamav": ("https://github.com/Cisco-Talos/clamav/",),
    "kag-poc": ("https://github.com/OpenSPG/KAG/",),
}

OFFICIAL_DOC_PREFIXES = {
    "outline": ("https://docs.getoutline.com/",),
    "prefect": ("https://docs.prefect.io/",),
    "docling-serve": (
        "https://github.com/docling-project/docling-serve",
        "https://docling-project.github.io/",
    ),
    "mineru": (
        "https://github.com/opendatalab/MinerU",
        "https://mineru.net/",
        "https://docs.mineru.net/",
    ),
    "ragflow": ("https://docs.ragflow.io/",),
    "langfuse": ("https://langfuse.com/", "https://docs.langfuse.com/"),
    "libreoffice": ("https://www.libreoffice.org/",),
    "clamav": ("https://docs.clamav.net/",),
    "kag-poc": ("https://github.com/OpenSPG/KAG", "https://openspg.com/"),
}

ALLOWED_REGISTRIES = {
    "registry-1.docker.io",
    "ghcr.io",
    "quay.io",
    "docker.langfuse.com",
}

MAIN_IMAGE_IDENTITIES = {
    "outline": {("registry-1.docker.io", "outlinewiki/outline")},
    "prefect": {("registry-1.docker.io", "prefecthq/prefect")},
    "docling-serve": {("ghcr.io", "docling-project/docling-serve")},
    "mineru": {
        ("ghcr.io", "opendatalab/mineru"),
        ("registry-1.docker.io", "opendatalab/mineru"),
    },
    "ragflow": {("registry-1.docker.io", "infiniflow/ragflow")},
    "langfuse": {("docker.langfuse.com", "langfuse/langfuse")},
    "clamav": {("registry-1.docker.io", "clamav/clamav")},
    "kag-poc": {
        ("ghcr.io", "openspg/kag"),
        ("registry-1.docker.io", "openspg/kag"),
    },
}


@dataclass
class ProbeState:
    spec: ComponentSpec
    checked_at: str
    evidence: list[dict[str, str]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    tag: str | None = None
    release_page: str | None = None
    deployment_bytes: bytes | None = None
    deployment_path: str | None = None
    deployment_source_url: str | None = None
    deployment_images: list[str] = field(default_factory=list)
    deployment_services: dict[str, dict[str, Any]] = field(default_factory=dict)
    image_artifacts: list[dict[str, Any]] = field(default_factory=list)
    image_identities: dict[str, dict[str, Any]] = field(default_factory=dict)
    model_artifacts: list[dict[str, Any]] = field(default_factory=list)
    license: dict[str, str] | None = None
    package_artifact: dict[str, Any] | None = None
    # Immutable typed closure. Declared here (defaulting to None) so that
    # _finalize can consult them without raising AttributeError when a probe
    # never populated them.
    resources: dict[str, Any] | None = None
    runtime_identity: dict[str, Any] | None = None
    persistent_paths: list[dict[str, Any]] | None = None
    configuration: dict[str, Any] | None = None

    def record(self, source_url: str, finding: str) -> None:
        self.evidence.append({"source_url": source_url, "finding": finding})

    def miss(self, layer: str, detail: str) -> None:
        item = f"{layer}: {detail}"
        if item not in self.missing:
            self.missing.append(item)


class PackageProbe(Protocol):
    def probe(self) -> dict[str, str]: ...


class UnavailablePackageProbe:
    def probe(self) -> dict[str, str]:
        raise RuntimeError("native package probe disabled for injected transport")


class AptPackageProbe:
    """Read local Ubuntu apt metadata without installing or downloading packages."""

    def probe(self) -> dict[str, str]:
        policy = subprocess.run(
            ["apt-cache", "policy", "libreoffice"],
            text=True, capture_output=True, timeout=10, check=False,
        )
        def policy_value(label: str) -> str:
            match = re.search(rf"^\s*{label}:\s*(\S+)", policy.stdout, re.MULTILINE)
            return match.group(1) if match else ""

        if policy.returncode:
            raise RuntimeError("apt-cache could not read package policy")
        installed = policy_value("Installed")
        candidate = policy_value("Candidate")
        if not candidate or candidate == "(none)":
            raise RuntimeError("apt-cache policy has no candidate version")

        repository_url, repository_id = self._candidate_repository(
            policy.stdout, candidate
        )
        show = subprocess.run(
            ["apt-cache", "show", "--no-all-versions", f"libreoffice={candidate}"],
            text=True, capture_output=True, timeout=10, check=False,
        )
        if show.returncode:
            raise RuntimeError("apt-cache could not read exact candidate metadata")

        records: set[tuple[str, str, str]] = set()
        for paragraph in re.split(r"\n\s*\n", show.stdout.strip()):
            fields: dict[str, str] = {}
            for line in paragraph.splitlines():
                if ": " in line:
                    key, value = line.split(": ", 1)
                    if key in {"Version", "Filename", "SHA256"}:
                        fields[key] = value.strip()
            if fields.get("Version") == candidate:
                records.add((fields.get("Version", ""), fields.get("Filename", ""), fields.get("SHA256", "")))
        if len(records) != 1:
            raise RuntimeError("apt-cache candidate metadata is ambiguous or absent")
        metadata_version, package_filename, sha256 = records.pop()
        if (
            not package_filename
            or package_filename.startswith("/")
            or ".." in Path(package_filename).parts
            or not re.fullmatch(r"[0-9a-f]{64}", sha256)
        ):
            raise RuntimeError("apt-cache candidate filename/SHA256 is incomplete")
        return {
            "installed_version": installed,
            "candidate_version": candidate,
            "metadata_version": metadata_version,
            "package_filename": package_filename,
            "sha256": sha256,
            "repository_id": repository_id,
            "repository_url": repository_url,
        }

    @staticmethod
    def _candidate_repository(policy: str, candidate: str) -> tuple[str, str]:
        candidate_line = re.compile(
            rf"^\s*(?:\*\*\*\s+)?{re.escape(candidate)}\s+[0-9]+\s*$"
        )
        version_line = re.compile(r"^\s*(?:\*\*\*\s+)?\S+\s+[0-9]+\s*$")
        repository_line = re.compile(
            r"^\s*[0-9]+\s+(https://\S+)\s+(\S+)/(\S+)\s+(\S+)\s+Packages\s*$"
        )
        in_candidate = False
        candidates: set[tuple[str, str]] = set()
        for line in policy.splitlines():
            if candidate_line.fullmatch(line):
                in_candidate = True
                continue
            if in_candidate and version_line.fullmatch(line):
                break
            if not in_candidate:
                continue
            match = repository_line.fullmatch(line)
            if match is None:
                continue
            source_url, suite, component, architecture = match.groups()
            parsed = urlparse(source_url)
            if parsed.scheme != "https" or not parsed.hostname:
                continue
            normalized_source = source_url.rstrip("/") + "/"
            identity = (
                f"{parsed.netloc}{parsed.path.rstrip('/')} "
                f"{suite}/{component} {architecture}"
            )
            candidates.add((normalized_source, identity))
        if len(candidates) != 1:
            raise RuntimeError("apt-cache candidate repository source is ambiguous or absent")
        return candidates.pop()


def _format_checker() -> FormatChecker:
    checker = FormatChecker()

    @checker.checks("date-time", raises=(TypeError, ValueError))
    def is_datetime(value: object) -> bool:
        if not isinstance(value, str) or RFC3339_RE.fullmatch(value) is None:
            return False
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(normalized).tzinfo is not None

    return checker


def _validation_error(message: str) -> ValidationError:
    return ValidationError(message)


def _normal_ref(value: str) -> str:
    return value.removeprefix("refs/tags/").removeprefix("v").lower()


def _assert_immutable(value: str, label: str) -> None:
    if MUTABLE_RE.search(value):
        raise _validation_error(f"{label} contains mutable ref: {value}")


def _image_source_identity(source_url: str) -> tuple[str, str] | None:
    parsed = urlparse(source_url)
    try:
        port = parsed.port or 443
    except ValueError:
        return None
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or port != 443
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return None
    authority = parsed.hostname.lower()
    path = parsed.path.rstrip("/")
    if authority == "hub.docker.com":
        match = re.fullmatch(r"/r/([^/]+/[^/]+)", path)
        return ("registry-1.docker.io", match.group(1).lower()) if match else None
    match = re.fullmatch(r"/v2/(.+)/manifests/[^/]+", path)
    if match is None or any(part in {"", ".", ".."} for part in match.group(1).split("/")):
        return None
    return authority, match.group(1).lower()


def _license_identifier(content: bytes) -> str | None:
    text = content.decode("utf-8", errors="replace")
    explicit = re.search(
        r"(?im)^\s*(?:[#*/;-]+\s*)?SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+)\s*$",
        text,
    )
    if explicit:
        identifier = explicit.group(1)
        return identifier if identifier in TRUSTED_SPDX_IDS else None
    normalized = " ".join(text.lower().split())
    signatures = (
        ("business source license 1.1", "BSL-1.1"),
        ("gnu affero general public license version 3", "AGPL-3.0-only"),
        ("apache license version 2.0", "Apache-2.0"),
        ("mozilla public license version 2.0", "MPL-2.0"),
        ("gnu general public license version 3", "GPL-3.0-only"),
        ("gnu general public license version 2", "GPL-2.0-only"),
    )
    for signature, identifier in signatures:
        if signature in normalized:
            return identifier
    if "mit license" in normalized and "permission is hereby granted, free of charge" in normalized:
        return "MIT"
    return None


def _normalize_spdx_identifier(value: object) -> str | None:
    """Return a trusted canonical SPDX identifier, or ``None``.

    Model-card metadata is untrusted input.  We accept only the finite set
    represented by the lock schema, plus explicitly documented SPDX aliases;
    arbitrary ``LicenseRef-*`` and unknown strings must block the component.
    """
    if not isinstance(value, str):
        return None
    identifier = value.strip()
    if identifier in TRUSTED_SPDX_IDS:
        return identifier
    if identifier in SPDX_ALIASES:
        return SPDX_ALIASES[identifier]
    return None


def validate_lock_document(lock: dict[str, Any]) -> None:
    """Run structural JSON Schema and component-aware semantic validation."""
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator(schema, format_checker=_format_checker()).validate(lock)

    for component_id, component in lock["components"].items():
        if component["resolution_status"] == "BLOCKED":
            continue
        version = component["version"]
        upstream_ref = component["deployment"]["upstream_ref"]
        _assert_immutable(version, f"{component_id}.version")
        _assert_immutable(upstream_ref, f"{component_id}.deployment.upstream_ref")
        if _normal_ref(version) != _normal_ref(upstream_ref):
            raise _validation_error(f"{component_id} version and upstream ref differ")

        source_url = component["source_url"]
        if not source_url.startswith(OFFICIAL_SOURCE_PREFIXES[component_id]):
            raise _validation_error(f"{component_id} source owner/repository is not official")
        docs_url = component["docs_url"]
        if not docs_url.startswith(OFFICIAL_DOC_PREFIXES[component_id]):
            raise _validation_error(f"{component_id} docs URL is not component-official")
        if component_id != "libreoffice":
            repository = next(spec.repository for spec in SPECS if spec.component == component_id)
            release_url = f"https://github.com/{repository}/releases/tag/{upstream_ref}"
            if source_url != release_url:
                raise _validation_error(f"{component_id} source URL is not pinned to upstream ref")
            if component["upgrade_notes_url"] != release_url:
                raise _validation_error(f"{component_id} upgrade notes are not pinned to upstream ref")
        license_url = component["license"]["source_url"]
        if component_id != "libreoffice":
            license_prefix = f"https://github.com/{repository}/blob/{upstream_ref}/"
            if not license_url.startswith(license_prefix):
                raise _validation_error(f"{component_id} license URL is not pinned to its official repository/ref")

        artifacts = component["artifacts"]
        image_artifacts = [artifact for artifact in artifacts if artifact["kind"] == "image"]
        model_artifacts = [artifact for artifact in artifacts if artifact["kind"] == "model"]
        image_names = {artifact["name"] for artifact in image_artifacts}
        model_names = {artifact["name"] for artifact in model_artifacts}
        if len(image_names) != len(image_artifacts) or len(model_names) != len(model_artifacts):
            raise _validation_error(f"{component_id} artifact names must be unique within each kind")
        closure = component["closure"]
        if image_names != set(closure["deployment_images"]):
            raise _validation_error(f"{component_id} image artifacts do not close deployment image inventory")
        if model_names != set(closure["runtime_models"]):
            raise _validation_error(f"{component_id} model artifacts do not close runtime model inventory")
        for artifact in image_artifacts:
            _assert_immutable(artifact["tag_or_version"], f"{component_id} image tag")
            if artifact["digest_or_checksum"] != artifact["linux_amd64_digest"]:
                raise _validation_error(f"{component_id} install digest is not linux/amd64 digest")
            if artifact["role"] == "main" and component_id != "libreoffice":
                if _image_source_identity(artifact["source_url"]) not in MAIN_IMAGE_IDENTITIES[component_id]:
                    raise _validation_error(f"{component_id} main image source is not component-official")
        image_digests = {artifact["linux_amd64_digest"] for artifact in image_artifacts}
        for artifact in model_artifacts:
            if not artifact.get("embedded_in_image"):
                revision = artifact["revision"]
                _assert_immutable(revision, f"{component_id} model revision")
                license_prefix = artifact["source_url"].rstrip("/") + f"/blob/{revision}/"
                if not artifact["license"]["source_url"].startswith(license_prefix):
                    raise _validation_error(f"{component_id} model license is not pinned to its revision")
            if artifact.get("embedded_in_image"):
                if artifact["image_digest"] not in image_digests:
                    raise _validation_error(f"{component_id} embedded model references an unlocked image")
                if component_id != "libreoffice":
                    proof_prefix = f"https://github.com/{repository}/blob/{upstream_ref}/"
                    if not artifact["proving_source_url"].startswith(proof_prefix):
                        raise _validation_error(
                            f"{component_id} embedded model proof is not pinned to its official repository/ref"
                        )

        if component["deployment_mode"] in {"compose", "container-cli"}:
            if not image_artifacts or sum(a["role"] == "main" for a in image_artifacts) != 1:
                raise _validation_error(f"{component_id} requires exactly one main image")
        if component_id == "libreoffice":
            packages = [artifact for artifact in artifacts if artifact["kind"] == "native-package"]
            if len(packages) != 1:
                raise _validation_error("libreoffice requires exactly one native package artifact")
            package = packages[0]
            if not (
                package["installed_version"]
                == package["candidate_version"]
                == component["version"]
            ):
                raise _validation_error("libreoffice installed/candidate/lock versions differ")
            expected_package_url = (
                package["repository"]["source_url"].rstrip("/")
                + "/"
                + package["package_filename"]
            )
            if package["source_url"] != expected_package_url:
                raise _validation_error(
                    "libreoffice package source is not bound to repository and filename"
                )


def _safe_json(result: HttpResult) -> dict[str, Any] | None:
    try:
        payload = json.loads(result.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _same_https_authority(requested: str, final: str) -> bool:
    requested_url = urlparse(requested)
    final_url = urlparse(final)
    try:
        requested_port = requested_url.port or 443
        final_port = final_url.port or 443
    except ValueError:
        return False
    return (
        requested_url.scheme.lower() == "https"
        and final_url.scheme.lower() == "https"
        and requested_url.hostname is not None
        and requested_url.hostname == final_url.hostname
        and requested_port == final_port
    )


def _get(state: ProbeState, transport: Transport, url: str, layer: str, headers: dict[str, str] | None = None) -> HttpResult | None:
    try:
        result = transport.get(url, headers)
    except Exception as exc:  # per-layer isolation becomes structured BLOCKED evidence
        state.record(url, f"{layer} probe failed: {type(exc).__name__}: {exc}")
        state.miss(layer, "probe raised an exception")
        return None
    if not _same_https_authority(url, result.final_url):
        state.record(url, f"{layer} probe rejected final redirect {result.final_url}")
        state.miss(layer, "final redirect left the official HTTPS authority")
        return None
    if result.status != 200:
        state.record(url, f"{layer} probe returned HTTP {result.status}")
        return result
    state.record(url, f"{layer} probe returned HTTP 200 from verified final URL {result.final_url}")
    return result


def _github_content(state: ProbeState, transport: Transport, path: str, layer: str) -> tuple[bytes, str] | None:
    assert state.spec.repository and state.tag
    url = f"https://raw.githubusercontent.com/{state.spec.repository}/{quote(state.tag, safe='')}/{quote(path, safe='/')}"
    result = _get(state, transport, url, layer, {"Accept": "text/plain"})
    if result is None or result.status != 200:
        return None
    html_url = f"https://github.com/{state.spec.repository}/blob/{state.tag}/{path}"
    return result.body, html_url


def _parse_image_refs(content: bytes) -> tuple[list[str], list[str]]:
    text = content.decode("utf-8", errors="replace")
    refs = re.findall(r"(?mi)^\s*image:\s*[\"']?([^\s\"'#]+)", text)
    refs.extend(re.findall(r"(?mi)^\s*FROM\s+(?:--platform=\S+\s+)?([^\s]+)", text))
    refs = list(dict.fromkeys(refs))
    unresolved = [ref for ref in refs if "$" in ref or "{" in ref]
    literal = [ref for ref in refs if ref not in unresolved]
    return literal, unresolved


def _parse_compose_services(
    content: bytes,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Return services plus any construct that prevents image closure."""
    try:
        document = yaml.safe_load(content)
    except yaml.YAMLError:
        return {}, ["deployment is not valid structured YAML"]
    if not isinstance(document, dict) or not isinstance(document.get("services"), dict):
        return {}, ["deployment has no structured Compose services mapping"]
    services: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for name, service in document["services"].items():
        if not isinstance(name, str) or not isinstance(service, dict):
            errors.append(f"malformed Compose service: {name!r}")
            continue
        services[name] = service
        if "build" in service:
            errors.append(f"Compose service {name} uses unlocked build")
        if "image" not in service:
            errors.append(f"Compose service {name} has no locked image")
        elif not isinstance(service["image"], str):
            errors.append(f"Compose service {name} image is not a string")
    return services, errors


def _parse_image_ref(reference: str) -> tuple[str, str, str]:
    without_digest = reference.split("@", 1)[0]
    last = without_digest.rsplit("/", 1)[-1]
    if ":" not in last:
        raise ValueError("image has no explicit tag")
    image, tag = without_digest.rsplit(":", 1)
    first = image.split("/", 1)[0]
    if "." in first or ":" in first or first == "localhost":
        registry, repository = image.split("/", 1)
        if registry in {"docker.io", "index.docker.io"}:
            registry = "registry-1.docker.io"
            if "/" not in repository:
                repository = f"library/{repository}"
    else:
        registry, repository = "registry-1.docker.io", image
        if "/" not in repository:
            repository = f"library/{repository}"
    return registry, repository, tag


def _registry_artifact(state: ProbeState, transport: Transport, reference: str, role: str) -> dict[str, Any] | None:
    try:
        registry, repository, tag = _parse_image_ref(reference)
        _assert_immutable(tag, f"image {reference}")
    except (ValueError, ValidationError) as exc:
        state.miss("registry", str(exc))
        return None
    if registry not in ALLOWED_REGISTRIES:
        state.miss("registry", f"registry authority is not allowlisted: {registry}")
        return None

    headers = {
        "Accept": ", ".join(
            [
                "application/vnd.oci.image.index.v1+json",
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.docker.distribution.manifest.v2+json",
            ]
        )
    }
    if registry == "registry-1.docker.io":
        token_url = "https://auth.docker.io/token?" + urlencode(
            {"service": "registry.docker.io", "scope": f"repository:{repository}:pull"}
        )
        token_result = _get(
            state, transport, token_url, "registry token", {"Accept": "application/json"}
        )
        token_payload = (
            _safe_json(token_result)
            if token_result is not None and token_result.status == 200
            else None
        )
        token = token_payload.get("token") if token_payload else None
        if not isinstance(token, str) or not token:
            state.miss("registry", f"bearer token unavailable for {reference}")
            return None
        headers["Authorization"] = f"Bearer {token}"

    manifest_url = f"https://{registry}/v2/{repository}/manifests/{quote(tag)}"
    result = _get(state, transport, manifest_url, "registry manifest", headers)
    if result is None or result.status != 200:
        state.miss("registry", f"manifest unavailable for {reference}")
        return None
    payload = _safe_json(result)
    manifest_digest = result.headers.get("docker-content-digest", "")
    if payload is None or not SHA256_RE.fullmatch(manifest_digest):
        state.miss("registry", f"official manifest/digest invalid for {reference}")
        return None
    manifests = payload.get("manifests")
    if not isinstance(manifests, list):
        state.miss("registry", f"manifest list missing for {reference}")
        return None
    platform_digest = ""
    for manifest in manifests:
        if not isinstance(manifest, dict):
            continue
        platform = manifest.get("platform")
        if isinstance(platform, dict) and platform.get("os") == "linux" and platform.get("architecture") == "amd64":
            platform_digest = manifest.get("digest", "")
            break
    if not SHA256_RE.fullmatch(platform_digest):
        state.miss("registry", f"linux/amd64 child digest missing for {reference}")
        return None
    child_url = (
        f"https://{registry}/v2/{repository}/manifests/"
        f"{quote(platform_digest, safe=':')}"
    )
    child_result = _get(state, transport, child_url, "registry image manifest", headers)
    child_digest_header = (
        child_result.headers.get("docker-content-digest", "")
        if child_result is not None
        else ""
    )
    child_body_digest = (
        "sha256:" + hashlib.sha256(child_result.body).hexdigest()
        if child_result is not None and child_result.status == 200
        else ""
    )
    if (
        child_result is None
        or child_result.status != 200
        or child_digest_header != platform_digest
        or child_body_digest != platform_digest
    ):
        state.miss(
            "registry",
            f"linux/amd64 child manifest bytes/digest mismatch for {reference}",
        )
        return None
    child_payload = _safe_json(child_result)
    config_descriptor = child_payload.get("config") if child_payload else None
    config_digest = (
        config_descriptor.get("digest") if isinstance(config_descriptor, dict) else None
    )
    if isinstance(config_digest, str) and SHA256_RE.fullmatch(config_digest):
        config_url = (
            f"https://{registry}/v2/{repository}/blobs/"
            f"{quote(config_digest, safe=':')}"
        )
        config_result = _get(
            state,
            transport,
            config_url,
            "registry image config",
            {
                **headers,
                "Accept": "application/vnd.oci.image.config.v1+json",
            },
        )
        config_payload = (
            _safe_json(config_result)
            if config_result and config_result.status == 200
            else None
        )
        config = config_payload.get("config") if config_payload else None
        user = config.get("User") if isinstance(config, dict) else None
        config_hash = (
            "sha256:" + hashlib.sha256(config_result.body).hexdigest()
            if config_result is not None and config_result.status == 200
            else ""
        )
        if config_hash != config_digest:
            state.record(config_url, f"registry image config digest mismatch for {reference}")
        elif user == "":
            state.image_identities[reference] = {
                "uid": 0,
                "gid": 0,
                "allow_root": True,
            }
        elif isinstance(user, str) and re.fullmatch(r"[0-9]+:[0-9]+", user):
            uid_text, gid_text = user.split(":", 1)
            uid, gid = int(uid_text), int(gid_text)
            state.image_identities[reference] = {
                "uid": uid,
                "gid": gid,
                "allow_root": uid == 0,
            }
        else:
            state.record(
                config_url,
                f"registry image config User is not a closed numeric UID:GID for {reference}",
            )
    else:
        state.record(child_url, f"registry image config descriptor missing for {reference}")
    return {
        "kind": "image",
        "role": role,
        "name": repository,
        "tag_or_version": tag,
        "digest_or_checksum": platform_digest,
        "manifest_digest": manifest_digest,
        "linux_amd64_digest": platform_digest,
        "platform": "linux/amd64",
        "source_url": f"https://registry-1.docker.io/v2/{repository}/manifests/{quote(tag)}" if registry == "registry-1.docker.io" else manifest_url,
    }


def _probe_model(state: ProbeState, transport: Transport, url: str) -> None:
    result = _get(state, transport, url, "model metadata", {"Accept": "application/json"})
    if result is None or result.status != 200:
        state.miss("model", f"metadata unavailable at {url}")
        return
    payload = _safe_json(result)
    if payload is None:
        state.miss("model", f"metadata was not an object at {url}")
        return
    revision = payload.get("sha")
    card_data = payload.get("cardData")
    siblings = payload.get("siblings")
    raw_license_id = card_data.get("license") if isinstance(card_data, dict) else None
    license_id = _normalize_spdx_identifier(raw_license_id)
    if (
        not isinstance(revision, str)
        or not re.fullmatch(r"[0-9a-f]{40,64}", revision)
        or not isinstance(siblings, list)
    ):
        state.miss("model", f"revision/file inventory closure incomplete at {url}")
        return
    model_id = urlparse(url).path.split("/api/models/", 1)[-1]
    model_page = f"https://huggingface.co/{model_id}"
    checksums: list[str] = []
    material_files = 0
    missing_checksums: list[str] = []
    license_filename: str | None = None
    if isinstance(siblings, list):
        for sibling in siblings:
            filename = sibling.get("rfilename") if isinstance(sibling, dict) else None
            if not isinstance(filename, str) or not filename:
                continue
            if Path(filename).name.upper() in {"LICENSE", "LICENSE.MD", "COPYING"}:
                license_filename = filename
            if Path(filename).suffix.lower() not in {
                ".bin", ".json", ".model", ".onnx", ".pt", ".pth", ".safetensors", ".txt",
            }:
                continue
            material_files += 1
            lfs = sibling.get("lfs") if isinstance(sibling, dict) else None
            checksum = lfs.get("sha256") if isinstance(lfs, dict) else None
            if isinstance(checksum, str) and re.fullmatch(r"[0-9a-f]{64}", checksum):
                checksums.append(f"{filename}:{checksum}")
            else:
                missing_checksums.append(filename)
    if len(missing_checksums) > MAX_MODEL_AUX_FILES:
        state.miss(
            "model",
            f"bounded auxiliary model-file checksum probe limit exceeded "
            f"({len(missing_checksums)} > {MAX_MODEL_AUX_FILES}) at {url}",
        )
        return
    unresolved_checksums: list[str] = []
    for filename in missing_checksums:
        file_url = (
            model_page
            + f"/resolve/{quote(revision, safe='')}/{quote(filename, safe='/')}"
        )
        file_result = _get(
            state,
            transport,
            file_url,
            "model file checksum",
            {"Accept": "application/octet-stream"},
        )
        if file_result is None or file_result.status != 200:
            unresolved_checksums.append(filename)
            continue
        checksums.append(f"{filename}:{hashlib.sha256(file_result.body).hexdigest()}")
    if unresolved_checksums:
        state.miss(
            "model",
            f"model-file checksums missing for {', '.join(unresolved_checksums)} at {url}",
        )
        return
    if material_files == 0 or len(checksums) != material_files or not license_filename:
        state.miss("model", f"revision/checksum/license closure incomplete at {url}")
        return
    if license_id is None:
        state.miss(
            "model",
            f"model card license is not a trusted SPDX identifier: {raw_license_id!r} at {url}",
        )
        return
    aggregate = hashlib.sha256("\n".join(sorted(checksums)).encode()).hexdigest()
    state.model_artifacts.append(
        {
            "kind": "model",
            "role": "runtime-model",
            "name": model_id,
            "revision": revision,
            "checksum": f"sha256:{aggregate}",
            "source_url": model_page,
            "license": {
                "id": license_id,
                "source_url": model_page + f"/blob/{revision}/{quote(license_filename, safe='/')}",
            },
        }
    )


def _numeric_gib(text: str, label: str) -> int | float | None:
    match = re.search(
        rf"(?im)^\s*minimum(?:\s+available|\s+free)?\s+{label}\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s+gib\s*$",
        text,
    )
    if not match:
        return None
    value = float(match.group(1))
    return int(value) if value.is_integer() else value


def _compose_volume_source(volume: object) -> str | None:
    if isinstance(volume, str):
        source, separator, _ = volume.partition(":")
        return source if separator else None
    if isinstance(volume, dict) and volume.get("type", "volume") == "bind":
        source = volume.get("source")
        return source if isinstance(source, str) else None
    return None


def _compose_environment(service: dict[str, Any]) -> dict[str, str | None]:
    environment = service.get("environment")
    if isinstance(environment, dict):
        return {
            key: value if isinstance(value, str) else None
            for key, value in environment.items()
            if isinstance(key, str)
        }
    if isinstance(environment, list):
        parsed: dict[str, str | None] = {}
        for item in environment:
            if not isinstance(item, str):
                continue
            key, separator, value = item.partition("=")
            if key:
                parsed[key] = value if separator else None
        return parsed
    return {}


def _extract_operational_layers(
    state: ProbeState, docs_result: HttpResult | None
) -> None:
    """Close typed fields only from retrieved docs, Compose, and image config."""
    docs_text = (
        docs_result.body.decode("utf-8", errors="replace")
        if docs_result is not None and docs_result.status == 200
        else ""
    )

    ram = _numeric_gib(docs_text, "ram")
    disk = _numeric_gib(docs_text, "disk")
    vm_match = re.search(
        r"(?im)^\s*vm\.max_map_count\s*:\s*([0-9]+|not\s+required)\s*$",
        docs_text,
    )
    missing_resource_fields = []
    if ram is None:
        missing_resource_fields.append("min_available_ram_gib")
    if disk is None:
        missing_resource_fields.append("min_free_disk_gib")
    if vm_match is None:
        missing_resource_fields.append("vm_max_map_count")
    if not missing_resource_fields:
        vm_text = vm_match.group(1).lower()
        state.resources = {
            "min_available_ram_gib": ram,
            "min_free_disk_gib": disk,
            "vm_max_map_count": None if vm_text.startswith("not") else int(vm_text),
        }
        state.record(
            state.spec.docs_url,
            f"resources parsed from {len(docs_result.body)} official documentation bytes",
        )
    else:
        state.miss(
            "resources",
            "official documentation did not close fields: "
            + ", ".join(missing_resource_fields),
        )

    main_services: list[dict[str, Any]] = []
    for service in state.deployment_services.values():
        reference = service.get("image")
        if not isinstance(reference, str):
            continue
        try:
            _, repository, _ = _parse_image_ref(reference)
        except ValueError:
            continue
        if repository.lower() in state.spec.main_image_repositories:
            main_services.append(service)
    if len(main_services) == 1:
        main_reference = main_services[0].get("image")
        state.runtime_identity = state.image_identities.get(main_reference)
    if state.runtime_identity is None:
        state.miss(
            "runtime",
            "main image config did not provide a verified numeric UID:GID/root policy",
        )

    persistent_paths: list[dict[str, Any]] = []
    persistence_errors: list[str] = []
    for service in state.deployment_services.values():
        reference = service.get("image")
        volumes = service.get("volumes", [])
        if not isinstance(volumes, list):
            persistence_errors.append("service volumes is not a list")
            continue
        for volume in volumes:
            source = _compose_volume_source(volume)
            if source is None:
                persistence_errors.append("named or unstructured volume has no host path")
                continue
            if not source.startswith("runtime/"):
                persistence_errors.append(f"host path is outside runtime/: {source}")
                continue
            identity = (
                state.image_identities.get(reference)
                if isinstance(reference, str)
                else None
            )
            mode_match = re.search(
                rf"(?im)^\s*persistent\s+path\s+{re.escape(source)}\s+mode\s+"
                r"(0[0-7]{3})\s*$",
                docs_text,
            )
            if identity is None:
                persistence_errors.append(f"image UID:GID missing for {source}")
            elif mode_match is None:
                persistence_errors.append(f"documented mode missing for {source}")
            else:
                persistent_paths.append(
                    {
                        "path": source,
                        "owner_uid": identity["uid"],
                        "owner_gid": identity["gid"],
                        "mode": mode_match.group(1),
                    }
                )
    if state.deployment_services and not persistence_errors:
        state.persistent_paths = persistent_paths
    else:
        state.miss(
            "persistence",
            "; ".join(persistence_errors)
            if persistence_errors
            else "structured deployment services unavailable",
        )

    if len(main_services) == 1:
        environment = _compose_environment(main_services[0])
        required_keys = [
            key
            for key, value in environment.items()
            if isinstance(value, str)
            and re.search(rf"\$\{{{re.escape(key)}(?:\?|:\?)", value)
        ]
        invalid_keys = [
            key for key in required_keys if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key)
        ]
        if invalid_keys:
            state.miss(
                "configuration",
                "required secret identifier is not schema-valid: "
                + ", ".join(invalid_keys),
            )
        elif required_keys:
            state.configuration = {"secret_keys": required_keys}
        elif re.search(r"(?im)^\s*no\s+secrets\s+required\s*:\s*true\s*$", docs_text):
            state.configuration = {
                "secret_keys": [],
                "no_secrets_required": True,
            }
    if state.configuration is None:
        state.miss(
            "configuration",
            "main service deployment did not close required secret keys",
        )


def _extract_native_operational_layers(
    state: ProbeState, docs_result: HttpResult | None
) -> None:
    text = (
        docs_result.body.decode("utf-8", errors="replace")
        if docs_result is not None and docs_result.status == 200
        else ""
    )
    ram = _numeric_gib(text, "ram")
    disk = _numeric_gib(text, "disk")
    vm_match = re.search(
        r"(?im)^\s*vm\.max_map_count\s*:\s*([0-9]+|not\s+required)\s*$",
        text,
    )
    missing_resources = []
    if ram is None:
        missing_resources.append("min_available_ram_gib")
    if disk is None:
        missing_resources.append("min_free_disk_gib")
    if vm_match is None:
        missing_resources.append("vm_max_map_count")
    if missing_resources:
        state.miss(
            "resources",
            "official documentation did not close fields: "
            + ", ".join(missing_resources),
        )
    else:
        vm_text = vm_match.group(1).lower()
        state.resources = {
            "min_available_ram_gib": ram,
            "min_free_disk_gib": disk,
            "vm_max_map_count": None if vm_text.startswith("not") else int(vm_text),
        }

    uid_match = re.search(r"(?im)^\s*runtime\s+uid\s*:\s*([0-9]+)\s*$", text)
    gid_match = re.search(r"(?im)^\s*runtime\s+gid\s*:\s*([0-9]+)\s*$", text)
    root_match = re.search(
        r"(?im)^\s*allow\s+root\s*:\s*(true|false)\s*$", text
    )
    if uid_match and gid_match and root_match:
        state.runtime_identity = {
            "uid": int(uid_match.group(1)),
            "gid": int(gid_match.group(1)),
            "allow_root": root_match.group(1).lower() == "true",
        }
    else:
        state.miss(
            "runtime",
            "official documentation did not close runtime UID/GID/root policy",
        )

    if re.search(
        r"(?im)^\s*no\s+persistent\s+paths\s+required\s*:\s*true\s*$",
        text,
    ):
        state.persistent_paths = []
    else:
        state.miss(
            "persistence",
            "official documentation did not explicitly close persistent paths",
        )
    if re.search(r"(?im)^\s*no\s+secrets\s+required\s*:\s*true\s*$", text):
        state.configuration = {"secret_keys": [], "no_secrets_required": True}
    else:
        state.miss(
            "configuration",
            "official documentation did not explicitly close required secrets",
        )


def _probe_libreoffice(state: ProbeState, transport: Transport, package_probe: PackageProbe) -> None:
    pages: dict[str, HttpResult | None] = {}
    for url, layer in ((state.spec.release_url, "release page"), (state.spec.docs_url, "docs"), ("https://www.libreoffice.org/about-us/licenses/", "license")):
        result = _get(state, transport, url, layer, {"Accept": "text/html"})
        pages[layer] = result
        if result is None or result.status != 200:
            state.miss(layer, "official page unavailable")
    try:
        package = package_probe.probe()
        state.record(
            "https://packages.ubuntu.com/noble-updates/libreoffice",
            "native package probe read installed/candidate/version/filename/SHA256 from local apt metadata",
        )
    except Exception as exc:
        state.record(
            "https://packages.ubuntu.com/noble-updates/libreoffice",
            f"native package probe failed: {type(exc).__name__}: {exc}",
        )
        state.miss("native-package", "local apt metadata probe failed")
        return
    required = ("installed_version", "candidate_version", "metadata_version", "package_filename", "sha256", "repository_id", "repository_url")
    if any(not package.get(field) or package[field] == "(none)" for field in required):
        state.miss("native-package", "installed/candidate/repository/filename/checksum closure is incomplete")
        return
    if not package["installed_version"] == package["candidate_version"] == package["metadata_version"]:
        state.miss("native-package", "installed, candidate, and apt metadata versions differ")
        return
    state.tag = package["candidate_version"]
    state.release_page = "https://packages.ubuntu.com/noble-updates/libreoffice"
    state.license = {"id": "MPL-2.0", "source_url": "https://www.libreoffice.org/about-us/licenses/"}
    state.package_artifact = {
        "kind": "native-package",
        "name": "libreoffice",
        "installed_version": package["installed_version"],
        "candidate_version": package["candidate_version"],
        "package_filename": package["package_filename"],
        "digest_or_checksum": f"sha256:{package['sha256']}",
        "source_url": package["repository_url"].rstrip("/") + "/" + package["package_filename"],
        "repository": {"id": package["repository_id"], "source_url": package["repository_url"]},
    }
    _extract_native_operational_layers(state, pages.get("docs"))


def _finish_probe(
    state: ProbeState,
    deployment_payloads: dict[str, bytes] | None,
) -> dict[str, Any]:
    component = _finalize(state)
    if component["resolution_status"] == "RESOLVED" and deployment_payloads is not None:
        payload = _deployment_payload(state)
        if payload is None:
            raise RuntimeError("RESOLVED component has no deployment payload")
        deployment_payloads[component["deployment"]["path"]] = payload
    return component


def _probe_component(
    spec: ComponentSpec,
    checked_at: str,
    transport: Transport,
    package_probe: PackageProbe,
    deployment_payloads: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    state = ProbeState(spec=spec, checked_at=checked_at)
    if spec.component == "libreoffice":
        _probe_libreoffice(state, transport, package_probe)
        return _finish_probe(state, deployment_payloads)

    release = _get(state, transport, spec.release_url, "release", {"Accept": "application/vnd.github+json"})
    if release is None or release.status != 200:
        state.miss("release", "official release metadata unavailable")
        return _finish_probe(state, deployment_payloads)
    payload = _safe_json(release)
    if payload is None:
        state.record(spec.release_url, "release response was not a JSON object")
        state.miss("release", "official release response was malformed")
        return _finish_probe(state, deployment_payloads)
    tag = payload.get("tag_name")
    page = payload.get("html_url")
    if not isinstance(tag, str) or not tag or not isinstance(page, str):
        state.miss("release", "tag_name/html_url missing from official response")
        return _finish_probe(state, deployment_payloads)
    try:
        _assert_immutable(tag, f"{spec.component} release")
    except ValidationError as exc:
        state.miss("release", str(exc))
        return _finish_probe(state, deployment_payloads)
    expected_release_page = (
        f"https://github.com/{spec.repository}/releases/tag/{tag}"
    )
    if page != expected_release_page:
        state.miss(
            "release",
            "release html_url is not exactly bound to the official repository/tag "
            f"({expected_release_page})",
        )
        return _finish_probe(state, deployment_payloads)
    state.tag, state.release_page = tag, page
    state.record(spec.release_url, f"parsed pinned official release tag {tag}")

    docs = _get(state, transport, spec.docs_url, "docs", {"Accept": "text/html"})
    if docs is None or docs.status != 200:
        state.miss("docs", "official docs URL unavailable")

    for license_path in spec.license_candidates:
        license_content = _github_content(state, transport, license_path, "license")
        if license_content:
            license_bytes, license_url = license_content
            identifier = _license_identifier(license_bytes)
            if identifier is not None:
                state.license = {"id": identifier, "source_url": license_url}
                state.record(license_url, f"mapped pinned official license bytes to {identifier}")
                break
            state.record(
                license_url,
                "pinned official license bytes did not map to a trusted SPDX identifier",
            )
    if state.license is None:
        state.miss("license", "no pinned official license file mapped to a trusted identifier")

    for deployment_path in spec.deployment_candidates:
        deployment = _github_content(state, transport, deployment_path, "deployment")
        if deployment:
            state.deployment_bytes, state.deployment_source_url = deployment
            state.deployment_path = deployment_path
            break
    if state.deployment_bytes is None:
        state.miss("deployment", "no pinned official deployment candidate found")
    else:
        state.deployment_services, compose_errors = _parse_compose_services(
            state.deployment_bytes
        )
        if compose_errors and state.deployment_services:
            state.miss("dependency-images", "; ".join(compose_errors))
        if state.deployment_services:
            structured_refs = [
                service.get("image")
                for service in state.deployment_services.values()
                if isinstance(service.get("image"), str)
            ]
            unresolved_images = [
                reference
                for reference in structured_refs
                if "$" in reference or "{" in reference
            ]
            literal_images = [
                reference
                for reference in structured_refs
                if reference not in unresolved_images
            ]
            literal_images = list(dict.fromkeys(literal_images))
        else:
            literal_images, unresolved_images = _parse_image_refs(state.deployment_bytes)
        state.deployment_images = literal_images
        if unresolved_images:
            state.miss("dependency-images", f"unresolved image expressions: {', '.join(unresolved_images)}")
        if not literal_images:
            state.miss("dependency-images", "pinned deployment yielded no literal image inventory")
        roles: list[str] = []
        for reference in literal_images:
            try:
                _, repository, _ = _parse_image_ref(reference)
            except ValueError:
                repository = ""
            role = "main" if repository.lower() in spec.main_image_repositories else "dependency"
            roles.append(role)
            artifact = _registry_artifact(state, transport, reference, role)
            if artifact:
                state.image_artifacts.append(artifact)
        if roles.count("main") != 1:
            state.miss("dependency-images", "official deployment did not identify exactly one component main image")
        if len(state.image_artifacts) != len(literal_images):
            state.miss("registry", "not every deployment image has manifest-list and linux/amd64 digests")

    for model_url in spec.model_urls:
        _probe_model(state, transport, model_url)
    if spec.component in {"docling-serve", "mineru", "ragflow", "kag-poc"}:
        if not spec.model_urls:
            state.miss("model", "official deployment does not close the runtime model inventory")
        elif len(state.model_artifacts) != len(spec.model_urls):
            state.miss("model", "not every expected model has revision/checksum/license closure")

    _extract_operational_layers(state, docs)
    return _finish_probe(state, deployment_payloads)


def _deployment_payload(state: ProbeState) -> bytes | None:
    if state.spec.deployment_mode == "compose":
        return state.deployment_bytes
    if state.spec.deployment_mode == "container-cli":
        if (
            state.deployment_bytes is None
            or state.deployment_source_url is None
            or state.tag is None
        ):
            return None
        source_sha256 = hashlib.sha256(state.deployment_bytes).hexdigest()
        return (
            "# Upstream container CLI deployment\n\n"
            f"- Component: `{state.spec.component}`\n"
            f"- Upstream ref: `{state.tag}`\n"
            f"- Provenance: `{state.deployment_source_url}`\n"
            f"- Retrieved source SHA-256: `{source_sha256}`\n"
        ).encode("utf-8")
    if state.spec.deployment_mode == "native-package":
        if state.package_artifact is None or state.tag is None:
            return None
        package = state.package_artifact
        return (
            "# Upstream native package deployment\n\n"
            f"- Component: `{state.spec.component}`\n"
            f"- Upstream ref: `{state.tag}`\n"
            f"- Repository: `{package['repository']['source_url']}`\n"
            f"- Package: `{package['source_url']}`\n"
            f"- Package checksum: `{package['digest_or_checksum']}`\n"
        ).encode("utf-8")
    return None


def _finalize(state: ProbeState) -> dict[str, Any]:
    if state.missing:
        return {
            "gate_role": state.spec.gate_role,
            "resolution_status": "BLOCKED",
            "blocker": "Evidence closure failed after attempting: " + "; ".join(state.missing),
            "evidence": state.evidence or [
                {"source_url": state.spec.release_url, "finding": "resolver produced no evidence before closure failure"}
            ],
            "checked_at": state.checked_at,
        }

    # Immutable typed closure must be complete before a component may be
    # reported RESOLVED; otherwise it degrades to a structured BLOCKED entry.
    typed_closure = {
        "resources": state.resources,
        "runtime_identity": state.runtime_identity,
        "persistent_paths": state.persistent_paths,
        "configuration": state.configuration,
    }
    incomplete = sorted(name for name, value in typed_closure.items() if value is None)
    if incomplete:
        return {
            "gate_role": state.spec.gate_role,
            "resolution_status": "BLOCKED",
            "blocker": (
                "Component evidence resolved but immutable typed closure incomplete: "
                "missing " + ", ".join(incomplete)
            ),
            "evidence": state.evidence or [
                {
                    "source_url": state.spec.release_url,
                    "finding": "resolver produced no evidence before typed closure failure",
                }
            ],
            "checked_at": state.checked_at,
        }

    if (
        not state.deployment_images
        or len(state.image_artifacts) != len(state.deployment_images)
        or sum(artifact.get("role") == "main" for artifact in state.image_artifacts) != 1
    ) and state.spec.deployment_mode != "native-package":
        return {
            "gate_role": state.spec.gate_role,
            "resolution_status": "BLOCKED",
            "blocker": "Component evidence resolved but deployment image inventory closure is incomplete",
            "evidence": state.evidence or [
                {
                    "source_url": state.spec.release_url,
                    "finding": "resolver produced no evidence before deployment image inventory failure",
                }
            ],
            "checked_at": state.checked_at,
        }

    # This path is reachable only when every probe above produced complete data.
    artifacts = state.image_artifacts + state.model_artifacts
    if state.package_artifact:
        artifacts.append(state.package_artifact)
    deployment_name = (
        "compose.upstream.yaml"
        if state.spec.deployment_mode == "compose"
        else "deployment.md"
    )
    deployment_bytes = _deployment_payload(state)
    if deployment_bytes is None:
        return {
            "gate_role": state.spec.gate_role,
            "resolution_status": "BLOCKED",
            "blocker": "Component evidence resolved but deployment publication payload is incomplete",
            "evidence": state.evidence or [
                {
                    "source_url": state.spec.release_url,
                    "finding": "resolver produced no evidence before deployment payload failure",
                }
            ],
            "checked_at": state.checked_at,
        }
    # Canonicalize legacy SPDX aliases at the lock boundary.  Some upstream
    # metadata still reports ``AGPL-3.0`` while the immutable lock schema uses
    # the current SPDX identifier ``AGPL-3.0-only``.
    license_info = dict(state.license)
    if license_info.get("id") == "AGPL-3.0":
        license_info["id"] = "AGPL-3.0-only"

    return {
        "gate_role": state.spec.gate_role,
        "resolution_status": "RESOLVED",
        "version": state.tag,
        "source_url": state.release_page,
        "docs_url": state.spec.docs_url,
        "license": license_info,
        "upgrade_notes_url": state.release_page,
        "artifacts": artifacts,
        "closure": {
            "deployment_images": [artifact["name"] for artifact in state.image_artifacts],
            "runtime_models": [artifact["name"] for artifact in state.model_artifacts],
        },
        "deployment": {
            "upstream_ref": state.tag,
            "upstream_sha256": hashlib.sha256(deployment_bytes).hexdigest(),
            "path": f"runtime/{state.spec.component}/{deployment_name}",
        },
        "deployment_mode": state.spec.deployment_mode,
        "resources": state.resources,
        "runtime_identity": state.runtime_identity,
        "persistent_paths": state.persistent_paths,
        "configuration": state.configuration,
    }


def resolve_lock(
    checked_at: str,
    transport: Transport,
    package_probe: PackageProbe,
    deployment_payloads: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    components: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                _probe_component,
                spec,
                checked_at,
                transport,
                package_probe,
                deployment_payloads,
            ): spec
            for spec in SPECS
        }
        for future in as_completed(futures):
            spec = futures[future]
            try:
                components[spec.component] = future.result()
            except Exception as exc:
                components[spec.component] = {
                    "gate_role": spec.gate_role,
                    "resolution_status": "BLOCKED",
                    "blocker": "Evidence closure failed after attempting: resolver task exception",
                    "evidence": [
                        {
                            "source_url": spec.release_url,
                            "finding": f"component resolver isolated {type(exc).__name__}: {exc}",
                        }
                    ],
                    "checked_at": checked_at,
                }
    return {"components": {spec.component: components[spec.component] for spec in SPECS}}


def render_report(checked_at: str, lock: dict[str, Any]) -> str:
    lines = [
        "# Phase 1 official version resolution", "", f"Checked at: `{checked_at}`", "",
        "## Method", "",
        "The resolver attempted official release, pinned deployment, dependency-image, Registry v2 manifest-list/linux-amd64 digest, license, model/native-package, runtime identity, persistence, resource, and configuration evidence layers. Remote bytes were parsed only and never executed.",
        "", "## Official source checks", "",
        "| Component | Role | Mode | Attempts | Status |", "|---|---|---|---:|---|",
    ]
    by_id = {spec.component: spec for spec in SPECS}
    for component_id, component in lock["components"].items():
        spec = by_id[component_id]
        lines.append(
            f"| `{component_id}` | {component['gate_role']} | `{spec.deployment_mode}` | {len(component.get('evidence', []))} | `{component['resolution_status']}` |"
        )
    lines.extend(["", "## Resolution details", ""])
    for component_id, component in lock["components"].items():
        lines.extend([f"### {component_id}: {component['resolution_status']}", ""])
        if component["resolution_status"] == "BLOCKED":
            lines.append(f"- Blocker: {component['blocker']}")
            for item in component["evidence"]:
                lines.append(f"- Attempt: {item['source_url']} — {item['finding']}")
            lines.append("- Deployment artifact saved: no (BLOCKED entries forbid installable fields)")
        else:
            lines.append(f"- Version: `{component['version']}`")
            lines.append(f"- Deployment: `{component['deployment']['path']}`")
        lines.append("")
    lines.extend(
        [
            "## Safety evidence", "",
            "- Container pull/start/run/up operations: **none**.",
            "- Remote scripts executed: **none**.",
            "- Required BLOCKED entries force the Phase 1 Gate to **BLOCKED**.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_report_consistency(lock: dict[str, Any], report: str) -> None:
    for component_id, component in lock["components"].items():
        heading = f"### {component_id}: {component['resolution_status']}"
        if report.count(heading) != 1:
            raise _validation_error(f"report is inconsistent for {component_id}")


def _stage(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as temporary:
        temporary.write(content)
        return Path(temporary.name)


def _stage_bytes(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as temporary:
        temporary.write(content)
        return Path(temporary.name)


def _restore(path: Path, original: bytes | None) -> None:
    if original is None:
        if path.exists():
            path.unlink()
        return
    staged = _stage(path, original.decode("utf-8"))
    os.replace(staged, path)


def _restore_bytes(path: Path, original: bytes | None) -> None:
    if original is None:
        if path.exists():
            path.unlink()
        return
    staged = _stage_bytes(path, original)
    os.replace(staged, path)


def _publish_bundle(publications: dict[Path, bytes]) -> None:
    staged: dict[Path, Path] = {}
    originals = {
        path: path.read_bytes() if path.exists() else None
        for path in publications
    }
    try:
        for path, content in publications.items():
            staged[path] = _stage_bytes(path, content)
        for path in publications:
            os.replace(staged[path], path)
    except Exception:
        for path, original in originals.items():
            _restore_bytes(path, original)
        raise
    finally:
        for staged_path in staged.values():
            if staged_path.exists():
                staged_path.unlink()


def _publish_pair(output: Path, lock_text: str, report_path: Path, report_text: str) -> None:
    _publish_bundle(
        {
            output: lock_text.encode("utf-8"),
            report_path: report_text.encode("utf-8"),
        }
    )


def _publication_root(output: Path, report_path: Path) -> Path:
    if output.parent.name == "config" and output.parent.parent.name == "platform":
        repository = output.parents[2]
        if report_path.is_relative_to(repository):
            return repository
    return Path(os.path.commonpath((output.parent, report_path.parent)))


def resolve_to_files(
    output: Path,
    report_path: Path,
    *,
    transport: Transport | None = None,
    package_probe: PackageProbe | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    output = output.resolve()
    report_path = report_path.resolve()
    if output == report_path:
        raise ValueError("--output and --report must be different paths")
    transport = transport or HttpTransport()
    package_probe = package_probe or (
        AptPackageProbe() if isinstance(transport, HttpTransport) else UnavailablePackageProbe()
    )
    checked_at = checked_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    deployment_payloads: dict[str, bytes] = {}
    lock = resolve_lock(
        checked_at,
        transport,
        package_probe,
        deployment_payloads=deployment_payloads,
    )
    validate_lock_document(lock)
    report = render_report(checked_at, lock)
    validate_report_consistency(lock, report)
    lock_text = yaml.safe_dump(lock, sort_keys=False, allow_unicode=True)
    resolved_deployments = {
        component["deployment"]["path"]: component
        for component in lock["components"].values()
        if component["resolution_status"] == "RESOLVED"
    }
    if set(resolved_deployments) != set(deployment_payloads):
        raise _validation_error("deployment payload inventory does not match RESOLVED lock entries")
    repository = _publication_root(output, report_path)
    publications = {
        output: lock_text.encode("utf-8"),
        report_path: report.encode("utf-8"),
    }
    for relative_path, payload in deployment_payloads.items():
        target = (repository / relative_path).resolve()
        if not target.is_relative_to(repository):
            raise _validation_error(f"deployment path escapes repository: {relative_path}")
        expected_sha256 = resolved_deployments[relative_path]["deployment"][
            "upstream_sha256"
        ]
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise _validation_error(f"deployment payload hash mismatch: {relative_path}")
        publications[target] = payload
    _publish_bundle(publications)
    return lock


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="lock YAML path")
    parser.add_argument("--report", required=True, type=Path, help="Markdown report path")
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    transport: Transport | None = None,
    package_probe: PackageProbe | None = None,
) -> int:
    args = parse_args(argv)
    resolve_to_files(args.output, args.report, transport=transport, package_probe=package_probe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
