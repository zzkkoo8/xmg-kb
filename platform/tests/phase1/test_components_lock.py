import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from tests.support.io import load_yaml
from tests.support.schema import validate
from tools import resolve_components as resolver


ROOT = Path(__file__).resolve().parents[3]
RESOLVER = ROOT / "platform" / "tools" / "resolve_components.py"
LOCK = ROOT / "platform" / "config" / "components.lock.yaml"


CANONICAL_ROLES = {
    "outline": "required",
    "prefect": "required",
    "docling-serve": "required",
    "mineru": "required",
    "ragflow": "required",
    "langfuse": "required",
    "libreoffice": "required",
    "clamav": "required",
    "kag-poc": "optional",
}


def blocked_component(role: str) -> dict:
    return {
        "gate_role": role,
        "resolution_status": "BLOCKED",
        "blocker": "The official evidence set does not prove an immutable deployment.",
        "evidence": [
            {
                "source_url": "https://api.github.com/repos/outline/outline/releases/latest",
                "finding": "Official release metadata alone does not prove all image digests.",
            }
        ],
        "checked_at": "2026-08-31T12:00:00Z",
    }


def lock_fixture() -> dict:
    return {
        "components": {
            component: blocked_component(role)
            for component, role in CANONICAL_ROLES.items()
        }
    }


def resolved_outline() -> dict:
    model_revision = "1" * 40
    return {
        "gate_role": "required",
        "resolution_status": "RESOLVED",
        "version": "v1.7.1",
        "source_url": "https://github.com/outline/outline/releases/tag/v1.7.1",
        "docs_url": "https://docs.getoutline.com/s/hosting/doc/docker-7pfeLP5a8t",
        "license": {
            "id": "BSL-1.1",
            "source_url": "https://github.com/outline/outline/blob/v1.7.1/LICENSE",
        },
        "upgrade_notes_url": "https://github.com/outline/outline/releases/tag/v1.7.1",
        "artifacts": [
            {
                "kind": "image",
                "role": "main",
                "name": "outline",
                "tag_or_version": "1.7.1",
                "digest_or_checksum": "sha256:" + "a" * 64,
                "manifest_digest": "sha256:" + "e" * 64,
                "linux_amd64_digest": "sha256:" + "a" * 64,
                "platform": "linux/amd64",
                "source_url": "https://hub.docker.com/r/outlinewiki/outline",
            },
            {
                "kind": "image",
                "role": "dependency",
                "name": "postgres",
                "tag_or_version": "16.4-alpine",
                "digest_or_checksum": "sha256:" + "c" * 64,
                "manifest_digest": "sha256:" + "f" * 64,
                "linux_amd64_digest": "sha256:" + "c" * 64,
                "platform": "linux/amd64",
                "source_url": "https://hub.docker.com/_/postgres",
            },
            {
                "kind": "model",
                "role": "runtime-model",
                "name": "synthetic-runtime-model",
                "revision": model_revision,
                "checksum": "sha256:" + "d" * 64,
                "source_url": "https://huggingface.co/ibm-granite/granite-docling-258M",
                "license": {
                    "id": "Apache-2.0",
                    "source_url": f"https://huggingface.co/ibm-granite/granite-docling-258M/blob/{model_revision}/LICENSE",
                },
            },
        ],
        "closure": {
            "deployment_images": ["outline", "postgres"],
            "runtime_models": ["synthetic-runtime-model"],
        },
        "deployment": {
            "upstream_ref": "v1.7.1",
            "upstream_sha256": "b" * 64,
            "path": "runtime/outline/compose.upstream.yaml",
        },
        "deployment_mode": "compose",
        "resources": {
            "min_available_ram_gib": 2,
            "min_free_disk_gib": 140,
            "vm_max_map_count": None,
        },
        "runtime_identity": {"uid": 1000, "gid": 1000, "allow_root": False},
        "persistent_paths": [
            {
                "path": "runtime/outline/data/postgres",
                "owner_uid": 999,
                "owner_gid": 999,
                "mode": "0700",
            }
        ],
        "configuration": {"secret_keys": ["SECRET_KEY", "UTILS_SECRET"]},
    }


def test_resolved_component_requires_complete_immutable_evidence():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    resolver.validate_lock_document(fixture)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda component: component.pop("docs_url"),
        lambda component: component.pop("deployment"),
        lambda component: component.pop("runtime_identity"),
        lambda component: component.pop("persistent_paths"),
        lambda component: component.pop("configuration"),
        lambda component: component["artifacts"][1].pop("digest_or_checksum"),
        lambda component: component["artifacts"][2].pop("revision"),
        lambda component: component["artifacts"][2].pop("checksum"),
    ],
)
def test_resolved_component_rejects_missing_contract_fields(mutation):
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    mutation(fixture["components"]["outline"])

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")


def test_blocked_component_requires_nonempty_evidence():
    fixture = lock_fixture()
    fixture["components"]["outline"].pop("evidence")

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")


@pytest.mark.parametrize("field", ["version", "artifacts", "deployment", "license"])
def test_blocked_component_rejects_installable_or_resolved_fields(field):
    fixture = lock_fixture()
    fixture["components"]["outline"][field] = copy.deepcopy(resolved_outline()[field])

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")


@pytest.mark.parametrize(
    "mutable_ref", ["latest", "LATEST", "main", "Main", "master", "nightly", "dev"]
)
def test_resolved_component_rejects_mutable_refs(mutable_ref):
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["deployment"]["upstream_ref"] = mutable_ref

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")


@pytest.mark.parametrize(
    "field,value",
    [
        ("deployment_mode", "native-package"),
        ("deployment.path", "runtime/prefect/compose.upstream.yaml"),
    ],
)
def test_resolved_component_rejects_wrong_component_deployment(field, value):
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    if field == "deployment.path":
        fixture["components"]["outline"]["deployment"]["path"] = value
    else:
        fixture["components"]["outline"][field] = value

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_url", "http://github.com/outline/outline/releases/tag/v1.7.1"),
        ("docs_url", "https://example.com/outline/install"),
        ("upgrade_notes_url", "https://unofficial.invalid/outline/v1.7.1"),
    ],
)
def test_resolved_component_rejects_non_https_or_unofficial_sources(field, value):
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"][field] = value

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")


def test_resolved_component_rejects_absent_license():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"].pop("license")

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")


def test_resolved_component_rejects_unresolved_license_placeholder():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["license"]["id"] = "SEE-OFFICIAL-LICENSE"

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")


def test_resolved_component_rejects_untrusted_license_identifier():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["license"]["id"] = "LicenseRef-Guess"

    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


def test_image_tag_without_digest_is_rejected():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["artifacts"][0].pop("digest_or_checksum")

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")


def test_secret_keys_are_explicit_and_only_empty_for_components_without_secrets():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["configuration"]["secret_keys"] = []

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")

    no_secret = resolved_outline()
    no_secret["configuration"]["secret_keys"] = []
    no_secret["configuration"]["no_secrets_required"] = True
    fixture["components"]["outline"] = no_secret
    validate(fixture, "components-lock")


def test_checked_in_lock_is_valid_and_resolver_exposes_required_cli():
    validate(load_yaml(LOCK), "components-lock")
    source = RESOLVER.read_text()
    assert 'parser.add_argument("--output", required=True' in source
    assert 'parser.add_argument("--report", required=True' in source


def resolved_libreoffice() -> dict:
    return {
        "gate_role": "required",
        "resolution_status": "RESOLVED",
        "version": "24.2.7-0ubuntu0.24.04.4",
        "source_url": "https://packages.ubuntu.com/noble-updates/libreoffice",
        "docs_url": "https://www.libreoffice.org/get-help/install-howto/linux/",
        "license": {
            "id": "MPL-2.0",
            "source_url": "https://www.libreoffice.org/about-us/licenses/",
        },
        "upgrade_notes_url": "https://packages.ubuntu.com/noble-updates/libreoffice",
        "artifacts": [
            {
                "kind": "native-package",
                "name": "libreoffice",
                "installed_version": "24.2.7-0ubuntu0.24.04.4",
                "candidate_version": "24.2.7-0ubuntu0.24.04.4",
                "package_filename": "pool/main/libr/libreoffice/libreoffice_24.2.7_amd64.deb",
                "digest_or_checksum": "sha256:" + "9" * 64,
                "source_url": "https://archive.ubuntu.com/ubuntu/pool/main/libr/libreoffice/libreoffice_24.2.7_amd64.deb",
                "repository": {
                    "id": "ubuntu-noble-updates-main",
                    "source_url": "https://archive.ubuntu.com/ubuntu/",
                },
            }
        ],
        "closure": {"deployment_images": [], "runtime_models": []},
        "deployment": {
            "upstream_ref": "24.2.7-0ubuntu0.24.04.4",
            "upstream_sha256": "8" * 64,
            "path": "runtime/libreoffice/deployment.md",
        },
        "deployment_mode": "native-package",
        "resources": {
            "min_available_ram_gib": 1,
            "min_free_disk_gib": 140,
            "vm_max_map_count": None,
        },
        "runtime_identity": {"uid": 0, "gid": 0, "allow_root": True},
        "persistent_paths": [],
        "configuration": {"secret_keys": [], "no_secrets_required": True},
    }


@pytest.mark.parametrize(
    "mutable_ref",
    ["stable", "develop", "refs/heads/main", "v1.7.1-SNAPSHOT", "release-nightly"],
)
def test_semantic_validator_rejects_composite_mutable_refs(mutable_ref):
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["deployment"]["upstream_ref"] = mutable_ref

    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


def test_semantic_validator_rejects_wrong_owner_and_version_ref_mismatch():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["source_url"] = (
        "https://github.com/unofficial/outline/releases/tag/v1.7.1"
    )

    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


@pytest.mark.parametrize(
    "field,value",
    [
        ("docs_url", "https://docs.prefect.io/v3/get-started"),
        (
            "upgrade_notes_url",
            "https://github.com/outline/outline/releases/tag/v1.7.2",
        ),
        (
            "license.source_url",
            "https://github.com/PrefectHQ/prefect/blob/v1.7.1/LICENSE",
        ),
    ],
)
def test_semantic_validator_binds_component_provenance_and_ref(field, value):
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    if field == "license.source_url":
        fixture["components"]["outline"]["license"]["source_url"] = value
    else:
        fixture["components"]["outline"][field] = value

    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


@pytest.mark.parametrize(
    "artifact_index,field,value",
    [
        (0, "tag_or_version", "v1.7.1-latest"),
        (2, "revision", "refs/heads/main"),
    ],
)
def test_semantic_validator_rejects_mutable_artifact_refs(
    artifact_index, field, value
):
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["artifacts"][artifact_index][field] = value

    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)

    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["deployment"]["upstream_ref"] = "v1.7.2"
    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


def test_semantic_validator_enforces_artifact_and_model_closure():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["artifacts"].pop(1)
    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)

    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    duplicate = copy.deepcopy(fixture["components"]["outline"]["artifacts"][1])
    fixture["components"]["outline"]["artifacts"].append(duplicate)
    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)

    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["artifacts"].pop(2)
    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


def test_embedded_model_digest_must_reference_a_locked_image():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["artifacts"][2] = {
        "kind": "model",
        "role": "runtime-model",
        "name": "synthetic-runtime-model",
        "embedded_in_image": True,
        "image_digest": "sha256:" + "7" * 64,
        "proving_source_url": "https://github.com/outline/outline/blob/v1.7.1/Dockerfile",
        "license": {
            "id": "Apache-2.0",
            "source_url": "https://github.com/outline/outline/blob/v1.7.1/LICENSE",
        },
    }

    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


def test_embedded_model_proof_must_match_component_repository_and_ref():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["artifacts"][2] = {
        "kind": "model",
        "role": "runtime-model",
        "name": "synthetic-runtime-model",
        "embedded_in_image": True,
        "image_digest": "sha256:" + "a" * 64,
        "proving_source_url": "https://github.com/PrefectHQ/prefect/blob/v1.7.1/Dockerfile",
        "license": {
            "id": "Apache-2.0",
            "source_url": "https://github.com/outline/outline/blob/v1.7.1/LICENSE",
        },
    }

    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


def test_main_image_provenance_must_match_component_identity():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["artifacts"][0]["source_url"] = (
        "https://hub.docker.com/_/postgres"
    )

    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


def test_main_image_provenance_rejects_repository_prefix_attacker():
    fixture = lock_fixture()
    fixture["components"]["outline"] = resolved_outline()
    fixture["components"]["outline"]["artifacts"][0]["source_url"] = (
        "https://hub.docker.com/r/outlinewiki/outline-attacker"
    )

    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


def test_libreoffice_requires_explicit_native_package_closure():
    fixture = lock_fixture()
    fixture["components"]["libreoffice"] = resolved_libreoffice()
    resolver.validate_lock_document(fixture)

    for field in (
        "installed_version",
        "candidate_version",
        "package_filename",
        "repository",
        "digest_or_checksum",
    ):
        invalid = copy.deepcopy(fixture)
        invalid["components"]["libreoffice"]["artifacts"][0].pop(field)
        with pytest.raises(ValidationError):
            resolver.validate_lock_document(invalid)


class MalformedTransport:
    def __init__(self, exploding_component: str | None = None, redirect_host: str | None = None):
        self.exploding_component = exploding_component
        self.redirect_host = redirect_host
        self.urls: list[str] = []

    def get(self, url: str, headers: dict[str, str] | None = None):
        self.urls.append(url)
        if self.exploding_component and self.exploding_component.lower() in url.lower():
            raise RuntimeError("synthetic transport failure")
        final_url = url
        if self.redirect_host and "outline/outline" in url:
            final_url = f"https://{self.redirect_host}/redirected"
        return resolver.HttpResult(
            requested_url=url,
            final_url=final_url,
            status=200,
            content_type="application/json",
            headers={},
            body=b"[]",
        )


class LayeredOutlineTransport:
    """Official-response fixture that exercises each immutable evidence layer."""

    def __init__(self):
        self.urls: list[str] = []
        self.request_headers: dict[str, dict[str, str]] = {}
        self.compose_bytes = (
            b"services:\n"
            b"  db:\n"
            b"    image: postgres:16.4-alpine\n"
            b"    volumes:\n"
            b"      - runtime/outline/data/postgres:/var/lib/postgresql/data\n"
            b"  app:\n"
            b"    image: outlinewiki/outline:1.7.1\n"
            b"    environment:\n"
            b"      SECRET_KEY: ${SECRET_KEY:?required}\n"
            b"      UTILS_SECRET: ${UTILS_SECRET:?required}\n"
        )
        self.docs_bytes = (
            b"Minimum available RAM: 3 GiB\n"
            b"Minimum free disk: 17 GiB\n"
            b"vm.max_map_count: 262144\n"
            b"Persistent path runtime/outline/data/postgres mode 0750\n"
        )
        self.config_bytes = {
            "outlinewiki/outline": b'{"config":{"User":"1200:1300"}}',
            "library/postgres": b'{"config":{"User":"999:998"}}',
        }
        self.config_digests = {
            repository: "sha256:" + hashlib.sha256(body).hexdigest()
            for repository, body in self.config_bytes.items()
        }
        self.child_manifest_bytes = {
            repository: json.dumps(
                {"config": {"digest": self.config_digests[repository]}}
            ).encode()
            for repository in self.config_bytes
        }
        self.child_manifest_digests = {
            repository: "sha256:" + hashlib.sha256(body).hexdigest()
            for repository, body in self.child_manifest_bytes.items()
        }

    def get(self, url: str, headers: dict[str, str] | None = None):
        self.urls.append(url)
        self.request_headers[url] = dict(headers or {})
        response_headers: dict[str, str] = {}
        body = self.docs_bytes
        if url.endswith("/releases/latest"):
            body = json.dumps(
                {
                    "tag_name": "v1.7.1",
                    "html_url": "https://github.com/outline/outline/releases/tag/v1.7.1",
                }
            ).encode()
        elif url.startswith("https://auth.docker.io/token?"):
            body = b'{"token":"fixture-token"}'
        elif url.endswith("/LICENSE"):
            body = b"SPDX-License-Identifier: BSL-1.1\n"
        elif "/blobs/" in url:
            repository = (
                "outlinewiki/outline"
                if "outlinewiki/outline" in url
                else "library/postgres"
            )
            body = self.config_bytes[repository]
        elif "/manifests/sha256:" in url:
            repository = (
                "outlinewiki/outline"
                if "outlinewiki/outline" in url
                else "library/postgres"
            )
            response_headers["docker-content-digest"] = url.rsplit("/", 1)[-1]
            body = self.child_manifest_bytes[repository]
        elif "/manifests/" in url:
            digest = "e" if "outlinewiki/outline" in url else "f"
            repository = (
                "outlinewiki/outline"
                if "outlinewiki/outline" in url
                else "library/postgres"
            )
            response_headers["docker-content-digest"] = "sha256:" + digest * 64
            body = json.dumps(
                {
                    "manifests": [
                        {
                            "digest": self.child_manifest_digests[repository],
                            "platform": {"os": "linux", "architecture": "amd64"},
                        }
                    ]
                }
            ).encode()
        elif url.endswith("/docker-compose.yml"):
            # Main-image classification must not depend on compose order.
            body = self.compose_bytes
        return resolver.HttpResult(url, url, 200, "application/json", response_headers, body)


class CompleteLibreOfficeTransport:
    def get(self, url: str, headers: dict[str, str] | None = None):
        body = (
            b"Minimum available RAM: 1 GiB\n"
            b"Minimum free disk: 8 GiB\n"
            b"vm.max_map_count: not required\n"
            b"Runtime UID: 1000\n"
            b"Runtime GID: 1000\n"
            b"Allow root: false\n"
            b"No persistent paths required: true\n"
            b"No secrets required: true\n"
        )
        return resolver.HttpResult(url, url, 200, "text/plain", {}, body)


class CompleteLibreOfficePackageProbe:
    def probe(self):
        return {
            "installed_version": "24.2.7-0ubuntu0.24.04.4",
            "candidate_version": "24.2.7-0ubuntu0.24.04.4",
            "metadata_version": "24.2.7-0ubuntu0.24.04.4",
            "package_filename": (
                "pool/main/libr/libreoffice/"
                "libreoffice_24.2.7-0ubuntu0.24.04.4_amd64.deb"
            ),
            "sha256": "9" * 64,
            "repository_id": "ubuntu-noble-updates-main",
            "repository_url": "https://archive.ubuntu.com/ubuntu/",
        }


def test_libreoffice_complete_native_evidence_reaches_resolved():
    spec = next(spec for spec in resolver.SPECS if spec.component == "libreoffice")

    component = resolver._probe_component(
        spec,
        "2026-08-31T12:00:00Z",
        CompleteLibreOfficeTransport(),
        CompleteLibreOfficePackageProbe(),
    )

    assert component["resolution_status"] == "RESOLVED"
    assert component["deployment"]["path"] == "runtime/libreoffice/deployment.md"
    assert component["resources"] == {
        "min_available_ram_gib": 1,
        "min_free_disk_gib": 8,
        "vm_max_map_count": None,
    }
    assert component["runtime_identity"] == {
        "uid": 1000,
        "gid": 1000,
        "allow_root": False,
    }
    assert component["persistent_paths"] == []
    assert component["configuration"] == {
        "secret_keys": [],
        "no_secrets_required": True,
    }


def test_cli_isolates_malformed_json_and_future_exceptions(tmp_path: Path):
    output = tmp_path / "components.lock.yaml"
    report = tmp_path / "version-resolution.md"
    transport = MalformedTransport(exploding_component="PrefectHQ")

    assert resolver.main(
        ["--output", str(output), "--report", str(report)], transport=transport
    ) == 0
    lock = load_yaml(output)
    resolver.validate_lock_document(lock)
    assert all(
        component["resolution_status"] == "BLOCKED"
        for component in lock["components"].values()
    )
    assert "synthetic transport failure" in json.dumps(lock["components"]["prefect"])
    resolver.validate_report_consistency(lock, report.read_text())


def test_cli_rejects_unofficial_final_redirect(tmp_path: Path):
    output = tmp_path / "components.lock.yaml"
    report = tmp_path / "version-resolution.md"
    transport = MalformedTransport(redirect_host="unofficial.invalid")

    resolver.main(["--output", str(output), "--report", str(report)], transport=transport)
    lock = load_yaml(output)
    assert lock["components"]["outline"]["resolution_status"] == "BLOCKED"
    assert "redirect" in json.dumps(lock["components"]["outline"]).lower()


@pytest.mark.parametrize(
    "release_url",
    [
        "https://github.com/outline/outline/releases/tag/v9.9.9",
        "https://github.com/outline/outline/releases/tag/v1.7.1/",
        "https://github.com/outline/outline/releases/latest",
        "https://github.com/outline/other/releases/tag/v1.7.1",
    ],
)
def test_release_html_url_must_exactly_bind_repository_and_tag(release_url):
    class MismatchedReleaseTransport(LayeredOutlineTransport):
        def get(self, url: str, headers: dict[str, str] | None = None):
            result = super().get(url, headers)
            if url.endswith("/releases/latest"):
                payload = json.loads(result.body)
                payload["html_url"] = release_url
                result = resolver.HttpResult(
                    result.requested_url,
                    result.final_url,
                    result.status,
                    result.content_type,
                    result.headers,
                    json.dumps(payload).encode(),
                )
            return result

    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    component = resolver._probe_component(
        spec,
        "2026-08-31T12:00:00Z",
        MismatchedReleaseTransport(),
        resolver.UnavailablePackageProbe(),
    )

    assert component["resolution_status"] == "BLOCKED"
    assert "exactly bound" in component["blocker"]


def test_resolver_attempts_evidence_layers_before_deriving_blocker(tmp_path: Path):
    output = tmp_path / "components.lock.yaml"
    report = tmp_path / "version-resolution.md"
    transport = MalformedTransport()
    resolver.main(["--output", str(output), "--report", str(report)], transport=transport)

    lock = load_yaml(output)
    for component in lock["components"].values():
        assert component["evidence"]
        assert component["blocker"].startswith("Evidence closure failed after attempting:")
    assert any("releases/latest" in url for url in transport.urls)


def test_outline_probe_walks_real_layers_and_classifies_main_image_by_identity():
    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    transport = LayeredOutlineTransport()

    component = resolver._probe_component(
        spec,
        "2026-08-31T12:00:00Z",
        transport,
        resolver.UnavailablePackageProbe(),
    )

    assert component["resolution_status"] == "RESOLVED"
    assert component["license"]["id"] == "BSL-1.1"
    assert any(url.endswith("/v1.7.1/LICENSE") for url in transport.urls)
    assert any(url.endswith("/v1.7.1/docker-compose.yml") for url in transport.urls)
    assert any("/v2/library/postgres/manifests/16.4-alpine" in url for url in transport.urls)
    assert any("/v2/outlinewiki/outline/manifests/1.7.1" in url for url in transport.urls)
    assert any("/v2/outlinewiki/outline/blobs/sha256:" in url for url in transport.urls)
    assert component["resources"] == {
        "min_available_ram_gib": 3,
        "min_free_disk_gib": 17,
        "vm_max_map_count": 262144,
    }
    assert component["runtime_identity"] == {
        "uid": 1200,
        "gid": 1300,
        "allow_root": False,
    }
    assert component["persistent_paths"] == [
        {
            "path": "runtime/outline/data/postgres",
            "owner_uid": 999,
            "owner_gid": 998,
            "mode": "0750",
        }
    ]
    assert component["configuration"] == {
        "secret_keys": ["SECRET_KEY", "UTILS_SECRET"]
    }


def test_registry_config_blob_keeps_registry_bearer_authorization():
    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    transport = LayeredOutlineTransport()

    component = resolver._probe_component(
        spec,
        "2026-08-31T12:00:00Z",
        transport,
        resolver.UnavailablePackageProbe(),
    )

    assert component["resolution_status"] == "RESOLVED"
    blob_urls = [url for url in transport.urls if "/blobs/" in url]
    assert blob_urls
    assert all(
        transport.request_headers[url].get("Authorization") == "Bearer fixture-token"
        for url in blob_urls
    )


def test_compose_build_service_blocks_image_inventory_closure():
    class BuildServiceTransport(LayeredOutlineTransport):
        def __init__(self):
            super().__init__()
            self.compose_bytes += b"  worker:\n    build: .\n"

    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    component = resolver._probe_component(
        spec,
        "2026-08-31T12:00:00Z",
        BuildServiceTransport(),
        resolver.UnavailablePackageProbe(),
    )

    assert component["resolution_status"] == "BLOCKED"
    assert "build" in component["blocker"]


def test_container_cli_compose_candidate_also_blocks_unlocked_build():
    class MinerUBuildTransport(LayeredOutlineTransport):
        def __init__(self):
            super().__init__()
            self.compose_bytes += b"  worker:\n    build: .\n"

        def get(self, url: str, headers: dict[str, str] | None = None):
            if "opendatalab/MinerU/releases/latest" in url:
                self.urls.append(url)
                self.request_headers[url] = dict(headers or {})
                body = json.dumps(
                    {
                        "tag_name": "mineru-3.4.5-released",
                        "html_url": (
                            "https://github.com/opendatalab/MinerU/releases/tag/"
                            "mineru-3.4.5-released"
                        ),
                    }
                ).encode()
                return resolver.HttpResult(url, url, 200, "application/json", {}, body)
            return super().get(url, headers)

    spec = next(spec for spec in resolver.SPECS if spec.component == "mineru")
    component = resolver._probe_component(
        spec,
        "2026-08-31T12:00:00Z",
        MinerUBuildTransport(),
        resolver.UnavailablePackageProbe(),
    )

    assert component["resolution_status"] == "BLOCKED"
    assert "Compose service worker uses unlocked build" in component["blocker"]


def test_registry_rejects_child_manifest_bytes_that_do_not_match_locked_digest():
    class MismatchedChildTransport(LayeredOutlineTransport):
        def get(self, url: str, headers: dict[str, str] | None = None):
            result = super().get(url, headers)
            if "/manifests/sha256:" in url:
                return resolver.HttpResult(
                    result.requested_url,
                    result.final_url,
                    result.status,
                    result.content_type,
                    result.headers,
                    result.body + b" ",
                )
            return result

    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    component = resolver._probe_component(
        spec,
        "2026-08-31T12:00:00Z",
        MismatchedChildTransport(),
        resolver.UnavailablePackageProbe(),
    )

    assert component["resolution_status"] == "BLOCKED"
    assert "child manifest" in component["blocker"]


def test_invalid_secret_identifier_becomes_component_blocker():
    class InvalidSecretTransport(LayeredOutlineTransport):
        def __init__(self):
            super().__init__()
            self.compose_bytes = self.compose_bytes.replace(
                b"SECRET_KEY: ${SECRET_KEY:?required}",
                b"secret-key: ${secret-key:?required}",
            )

    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    component = resolver._probe_component(
        spec,
        "2026-08-31T12:00:00Z",
        InvalidSecretTransport(),
        resolver.UnavailablePackageProbe(),
    )

    assert component["resolution_status"] == "BLOCKED"
    assert "secret identifier" in component["blocker"]


def test_cli_publishes_schema_valid_resolved_compose_with_exact_upstream_bytes(
    tmp_path: Path,
):
    repository = tmp_path / "repo"
    output = repository / "platform/config/components.lock.yaml"
    report = repository / "reports/01-version-resolution.md"
    transport = LayeredOutlineTransport()

    assert resolver.main(
        ["--output", str(output), "--report", str(report)], transport=transport
    ) == 0

    lock = load_yaml(output)
    resolver.validate_lock_document(lock)
    outline = lock["components"]["outline"]
    deployment = repository / outline["deployment"]["path"]
    assert outline["resolution_status"] == "RESOLVED"
    assert outline["deployment"]["upstream_ref"] == "v1.7.1"
    assert outline["source_url"].endswith("/releases/tag/v1.7.1")
    assert outline["deployment"]["upstream_sha256"] == hashlib.sha256(
        transport.compose_bytes
    ).hexdigest()
    assert deployment.read_bytes() == transport.compose_bytes
    assert "### outline: RESOLVED" in report.read_text()
    assert any(
        url.endswith("/outline/outline/v1.7.1/docker-compose.yml")
        for url in transport.urls
    )


def test_cli_publishes_native_package_deployment_markdown(tmp_path: Path):
    repository = tmp_path / "repo"
    output = repository / "platform/config/components.lock.yaml"
    report = repository / "reports/01-version-resolution.md"

    resolver.main(
        ["--output", str(output), "--report", str(report)],
        transport=CompleteLibreOfficeTransport(),
        package_probe=CompleteLibreOfficePackageProbe(),
    )

    lock = load_yaml(output)
    resolver.validate_lock_document(lock)
    component = lock["components"]["libreoffice"]
    deployment = repository / "runtime/libreoffice/deployment.md"
    deployment_bytes = deployment.read_bytes()
    assert component["resolution_status"] == "RESOLVED"
    assert component["deployment"]["path"] == "runtime/libreoffice/deployment.md"
    assert component["deployment"]["upstream_sha256"] == hashlib.sha256(
        deployment_bytes
    ).hexdigest()
    assert component["deployment"]["upstream_ref"].encode() in deployment_bytes
    assert component["artifacts"][0]["source_url"].encode() in deployment_bytes


def test_blocked_cli_does_not_create_any_deployment(tmp_path: Path):
    repository = tmp_path / "repo"
    output = repository / "platform/config/components.lock.yaml"
    report = repository / "reports/01-version-resolution.md"

    resolver.main(
        ["--output", str(output), "--report", str(report)],
        transport=MalformedTransport(),
    )

    lock = load_yaml(output)
    assert all(
        component["resolution_status"] == "BLOCKED"
        for component in lock["components"].values()
    )
    assert not (repository / "runtime").exists()


def test_registry_probe_refuses_unknown_authority_before_network_access():
    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    transport = LayeredOutlineTransport()

    assert resolver._registry_artifact(
        state, transport, "unofficial.invalid/outline:1.7.1", "main"
    ) is None
    assert transport.urls == []
    assert "registry authority" in "; ".join(state.missing)


def test_registry_token_redirect_must_preserve_https_effective_authority():
    class RedirectedTokenTransport(LayeredOutlineTransport):
        def get(self, url: str, headers: dict[str, str] | None = None):
            result = super().get(url, headers)
            if url.startswith("https://auth.docker.io/token?"):
                return resolver.HttpResult(
                    result.requested_url,
                    "https://auth.docker.io:444/token",
                    200,
                    result.content_type,
                    result.headers,
                    result.body,
                )
            return result

    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    transport = RedirectedTokenTransport()

    assert resolver._registry_artifact(
        state, transport, "outlinewiki/outline:1.7.1", "main"
    ) is None
    assert not any("/manifests/" in url for url in transport.urls)
    assert "redirect" in "; ".join(state.missing)


@pytest.mark.parametrize(
    "requested,final,expected",
    [
        ("https://example.com/a", "https://EXAMPLE.com:443/b", True),
        ("https://example.com/a", "https://example.com:444/b", False),
        ("https://example.com/a", "http://example.com/a", False),
    ],
)
def test_redirect_authority_uses_scheme_host_and_effective_port(
    requested, final, expected
):
    assert resolver._same_https_authority(requested, final) is expected


def test_apt_package_probe_derives_candidate_repository_and_exact_show_version(
    monkeypatch,
):
    calls: list[list[str]] = []
    policy = """libreoffice:
  Installed: 4:24.2.7-0ubuntu0.24.04.4
  Candidate: 4:24.2.7-0ubuntu0.24.04.4
  Version table:
 *** 4:24.2.7-0ubuntu0.24.04.4 500
        500 https://mirror.example/ubuntu noble-updates/universe amd64 Packages
        100 /var/lib/dpkg/status
     4:24.2.1-0ubuntu1 500
        500 https://mirror.example/ubuntu noble/universe amd64 Packages
"""
    show = """Package: libreoffice
Version: 4:24.2.7-0ubuntu0.24.04.4
Filename: pool/universe/libr/libreoffice/libreoffice_24.2.7_amd64.deb
SHA256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
"""

    def fake_run(command, **_kwargs):
        calls.append(command)
        output = policy if command[1] == "policy" else show
        return type("Result", (), {"returncode": 0, "stdout": output})()

    monkeypatch.setattr(resolver.subprocess, "run", fake_run)
    package = resolver.AptPackageProbe().probe()

    assert calls[1] == [
        "apt-cache",
        "show",
        "--no-all-versions",
        "libreoffice=4:24.2.7-0ubuntu0.24.04.4",
    ]
    assert package["metadata_version"] == package["candidate_version"]
    assert package["repository_id"] == (
        "mirror.example/ubuntu noble-updates/universe amd64"
    )
    assert package["repository_url"] == "https://mirror.example/ubuntu/"


def test_apt_package_probe_blocks_candidate_without_repository_source(monkeypatch):
    policy = """libreoffice:
  Installed: 4:24.2.7-0ubuntu0.24.04.4
  Candidate: 4:24.2.7-0ubuntu0.24.04.4
  Version table:
 *** 4:24.2.7-0ubuntu0.24.04.4 100
        100 /var/lib/dpkg/status
"""
    show = """Package: libreoffice
Version: 4:24.2.7-0ubuntu0.24.04.4
Filename: pool/universe/libr/libreoffice/libreoffice_24.2.7_amd64.deb
SHA256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
"""

    def fake_run(command, **_kwargs):
        output = policy if command[1] == "policy" else show
        return type("Result", (), {"returncode": 0, "stdout": output})()

    monkeypatch.setattr(resolver.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="candidate repository"):
        resolver.AptPackageProbe().probe()


def test_resolver_rejects_identical_output_and_report_paths(tmp_path: Path):
    same_path = tmp_path / "same"
    with pytest.raises(ValueError):
        resolver.resolve_to_files(
            same_path,
            same_path,
            transport=MalformedTransport(),
            checked_at="2026-08-31T12:00:00Z",
        )


def test_resolver_validates_before_replacing_existing_pair(tmp_path: Path, monkeypatch):
    output = tmp_path / "components.lock.yaml"
    report = tmp_path / "version-resolution.md"
    output.write_text("old lock")
    report.write_text("old report")

    def reject(_lock):
        raise ValidationError("synthetic validation failure")

    monkeypatch.setattr(resolver, "validate_lock_document", reject)
    with pytest.raises(ValidationError):
        resolver.resolve_to_files(
            output,
            report,
            transport=MalformedTransport(),
            checked_at="2026-08-31T12:00:00Z",
        )

    assert output.read_text() == "old lock"
    assert report.read_text() == "old report"


def test_pair_publication_rolls_back_both_outputs_on_second_replace_failure(
    tmp_path: Path, monkeypatch
):
    output = tmp_path / "components.lock.yaml"
    report = tmp_path / "version-resolution.md"
    output.write_text("old lock")
    report.write_text("old report")
    real_replace = resolver.os.replace
    calls = 0

    def fail_second_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic second publication failure")
        real_replace(source, destination)

    monkeypatch.setattr(resolver.os, "replace", fail_second_replace)
    with pytest.raises(OSError, match="second publication"):
        resolver._publish_pair(output, "new lock", report, "new report")

    assert output.read_text() == "old lock"
    assert report.read_text() == "old report"


def test_publication_failure_restores_lock_report_and_deployment(
    tmp_path: Path, monkeypatch
):
    repository = tmp_path / "repo"
    output = repository / "platform/config/components.lock.yaml"
    report = repository / "reports/01-version-resolution.md"
    deployment = repository / "runtime/outline/compose.upstream.yaml"
    output.parent.mkdir(parents=True)
    report.parent.mkdir(parents=True)
    deployment.parent.mkdir(parents=True)
    output.write_bytes(b"old lock")
    report.write_bytes(b"old report")
    deployment.write_bytes(b"old deployment")
    real_replace = resolver.os.replace
    calls = 0

    def fail_deployment_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("synthetic deployment publication failure")
        real_replace(source, destination)

    monkeypatch.setattr(resolver.os, "replace", fail_deployment_replace)
    with pytest.raises(OSError, match="deployment publication"):
        resolver.resolve_to_files(
            output,
            report,
            transport=LayeredOutlineTransport(),
            checked_at="2026-08-31T12:00:00Z",
        )

    assert output.read_bytes() == b"old lock"
    assert report.read_bytes() == b"old report"
    assert deployment.read_bytes() == b"old deployment"


def test_docker_hub_alias_is_normalized_to_registry_v2_authority():
    registry, repository, tag = resolver._parse_image_ref("docker.io/redis:7")
    assert (registry, repository, tag) == ("registry-1.docker.io", "library/redis", "7")


def test_blocked_evidence_accepts_known_vendor_registry_url():
    fixture = lock_fixture()
    fixture["components"]["langfuse"]["evidence"][0]["source_url"] = (
        "https://docker.langfuse.com/v2/langfuse/langfuse/manifests/4"
    )
    validate(fixture, "components-lock")


def test_pinned_github_content_uses_official_raw_bytes():
    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    state.tag = "v1.7.1"

    class RawTransport:
        def __init__(self):
            self.urls = []

        def get(self, url, headers=None):
            self.urls.append(url)
            return resolver.HttpResult(url, url, 200, "text/plain", {}, b"services: {}")

    transport = RawTransport()
    content, html_url = resolver._github_content(
        state, transport, "docker-compose.yml", "deployment"
    )
    assert content == b"services: {}"
    assert transport.urls == [
        "https://raw.githubusercontent.com/outline/outline/v1.7.1/docker-compose.yml"
    ]
    assert html_url == (
        "https://github.com/outline/outline/blob/v1.7.1/docker-compose.yml"
    )


def test_model_metadata_probe_requests_blob_checksums():
    model_urls = [url for spec in resolver.SPECS for url in spec.model_urls]
    assert model_urls
    assert all(url.endswith("?blobs=true") for url in model_urls)


def test_finalize_turns_missing_typed_closure_into_structured_blocked():
    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    state.tag = "v1.7.1"
    state.release_page = "https://github.com/outline/outline/releases/tag/v1.7.1"
    state.license = {
        "id": "BSL-1.1",
        "source_url": "https://github.com/outline/outline/blob/v1.7.1/LICENSE",
    }
    state.deployment_bytes = b"services: {}"

    component = resolver._finalize(state)
    assert component["resolution_status"] == "BLOCKED"
    assert "typed" in component["blocker"]


def test_finalize_emits_resolved_only_for_complete_typed_closure():
    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    state.tag = "v1.7.1"
    state.release_page = "https://github.com/outline/outline/releases/tag/v1.7.1"
    state.license = {
        "id": "BSL-1.1",
        "source_url": "https://github.com/outline/outline/blob/v1.7.1/LICENSE",
    }
    state.deployment_bytes = b"services: {}"
    state.deployment_images = ["outlinewiki/outline:1.7.1", "postgres:16.4-alpine"]
    state.image_artifacts = resolved_outline()["artifacts"][:2]
    state.model_artifacts = resolved_outline()["artifacts"][2:]
    state.resources = resolved_outline()["resources"]
    state.runtime_identity = resolved_outline()["runtime_identity"]
    state.persistent_paths = resolved_outline()["persistent_paths"]
    state.configuration = resolved_outline()["configuration"]

    component = resolver._finalize(state)
    fixture = lock_fixture()
    fixture["components"]["outline"] = component
    resolver.validate_lock_document(fixture)
    assert component["resolution_status"] == "RESOLVED"


def test_finalize_rejects_artifacts_without_discovered_deployment_inventory():
    spec = next(spec for spec in resolver.SPECS if spec.component == "outline")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    state.tag = "v1.7.1"
    state.release_page = "https://github.com/outline/outline/releases/tag/v1.7.1"
    state.license = resolved_outline()["license"]
    state.deployment_bytes = b"services: {}"
    state.image_artifacts = resolved_outline()["artifacts"][:2]
    state.model_artifacts = resolved_outline()["artifacts"][2:]
    state.resources = resolved_outline()["resources"]
    state.runtime_identity = resolved_outline()["runtime_identity"]
    state.persistent_paths = resolved_outline()["persistent_paths"]
    state.configuration = resolved_outline()["configuration"]

    component = resolver._finalize(state)
    assert component["resolution_status"] == "BLOCKED"
    assert "deployment image inventory" in component["blocker"]


def test_mineru_container_cli_uses_deployment_markdown_path():
    spec = next(spec for spec in resolver.SPECS if spec.component == "mineru")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    state.tag = "mineru-3.4.5-released"
    state.release_page = (
        "https://github.com/opendatalab/MinerU/releases/tag/mineru-3.4.5-released"
    )
    state.license = {
        "id": "AGPL-3.0",
        "source_url": (
            "https://github.com/opendatalab/MinerU/blob/"
            "mineru-3.4.5-released/LICENSE.md"
        ),
    }
    state.deployment_bytes = b"FROM opendatalab/mineru:3.4.5\n"
    state.deployment_path = "Dockerfile"
    state.deployment_source_url = (
        "https://github.com/opendatalab/MinerU/blob/"
        "mineru-3.4.5-released/Dockerfile"
    )
    state.deployment_images = ["opendatalab/mineru:3.4.5"]
    state.image_artifacts = [
        {
            "kind": "image",
            "role": "main",
            "name": "opendatalab/mineru",
            "tag_or_version": "3.4.5",
            "digest_or_checksum": "sha256:" + "a" * 64,
            "manifest_digest": "sha256:" + "e" * 64,
            "linux_amd64_digest": "sha256:" + "a" * 64,
            "platform": "linux/amd64",
            "source_url": "https://ghcr.io/v2/opendatalab/mineru/manifests/3.4.5",
        }
    ]
    state.resources = {
        "min_available_ram_gib": 4,
        "min_free_disk_gib": 20,
        "vm_max_map_count": None,
    }
    state.runtime_identity = {"uid": 1000, "gid": 1000, "allow_root": False}
    state.persistent_paths = []
    state.configuration = {"secret_keys": [], "no_secrets_required": True}

    component = resolver._finalize(state)

    assert component["resolution_status"] == "RESOLVED"
    assert component["deployment_mode"] == "container-cli"
    assert component["deployment"]["path"] == "runtime/mineru/deployment.md"


def test_resolve_to_files_publishes_container_cli_markdown(
    tmp_path: Path, monkeypatch
):
    spec = next(spec for spec in resolver.SPECS if spec.component == "mineru")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    state.tag = "mineru-3.4.5-released"
    state.release_page = (
        "https://github.com/opendatalab/MinerU/releases/tag/mineru-3.4.5-released"
    )
    state.license = {
        "id": "AGPL-3.0",
        "source_url": (
            "https://github.com/opendatalab/MinerU/blob/"
            "mineru-3.4.5-released/LICENSE.md"
        ),
    }
    state.deployment_bytes = b"FROM opendatalab/mineru:3.4.5\n"
    state.deployment_path = "Dockerfile"
    state.deployment_source_url = (
        "https://github.com/opendatalab/MinerU/blob/"
        "mineru-3.4.5-released/Dockerfile"
    )
    state.deployment_images = ["opendatalab/mineru:3.4.5"]
    state.image_artifacts = [
        {
            "kind": "image",
            "role": "main",
            "name": "opendatalab/mineru",
            "tag_or_version": "3.4.5",
            "digest_or_checksum": "sha256:" + "a" * 64,
            "manifest_digest": "sha256:" + "e" * 64,
            "linux_amd64_digest": "sha256:" + "a" * 64,
            "platform": "linux/amd64",
            "source_url": "https://ghcr.io/v2/opendatalab/mineru/manifests/3.4.5",
        }
    ]
    state.resources = {
        "min_available_ram_gib": 4,
        "min_free_disk_gib": 20,
        "vm_max_map_count": None,
    }
    state.runtime_identity = {"uid": 1000, "gid": 1000, "allow_root": False}
    state.persistent_paths = []
    state.configuration = {"secret_keys": [], "no_secrets_required": True}
    component = resolver._finalize(state)
    payload = resolver._deployment_payload(state)
    fixture = lock_fixture()
    fixture["components"]["mineru"] = component

    def fake_resolve_lock(
        checked_at, transport, package_probe, deployment_payloads=None
    ):
        deployment_payloads[component["deployment"]["path"]] = payload
        return fixture

    monkeypatch.setattr(resolver, "resolve_lock", fake_resolve_lock)
    repository = tmp_path / "repo"
    output = repository / "platform/config/components.lock.yaml"
    report = repository / "reports/01-version-resolution.md"

    resolver.resolve_to_files(
        output,
        report,
        transport=MalformedTransport(),
        checked_at="2026-08-31T12:00:00Z",
    )

    deployment = repository / "runtime/mineru/deployment.md"
    assert deployment.read_bytes() == payload
    assert b"Upstream ref: `mineru-3.4.5-released`" in payload
    assert state.deployment_source_url.encode() in payload
    assert component["deployment"]["upstream_sha256"] == hashlib.sha256(
        payload
    ).hexdigest()


def test_finalize_canonicalizes_agpl_30_license_alias():
    spec = next(spec for spec in resolver.SPECS if spec.component == "mineru")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    state.tag = "mineru-3.4.5-released"
    state.release_page = (
        "https://github.com/opendatalab/MinerU/releases/tag/mineru-3.4.5-released"
    )
    state.license = {
        "id": "AGPL-3.0",
        "source_url": (
            "https://github.com/opendatalab/MinerU/blob/"
            "mineru-3.4.5-released/LICENSE.md"
        ),
    }
    state.deployment_bytes = b"FROM opendatalab/mineru:3.4.5\n"
    state.deployment_source_url = (
        "https://github.com/opendatalab/MinerU/blob/"
        "mineru-3.4.5-released/Dockerfile"
    )
    state.deployment_images = ["opendatalab/mineru:3.4.5"]
    state.image_artifacts = [
        {
            "kind": "image",
            "role": "main",
            "name": "opendatalab/mineru",
            "tag_or_version": "3.4.5",
            "digest_or_checksum": "sha256:" + "a" * 64,
            "manifest_digest": "sha256:" + "e" * 64,
            "linux_amd64_digest": "sha256:" + "a" * 64,
            "platform": "linux/amd64",
            "source_url": "https://ghcr.io/v2/opendatalab/mineru/manifests/3.4.5",
        }
    ]
    state.resources = {
        "min_available_ram_gib": 4,
        "min_free_disk_gib": 20,
        "vm_max_map_count": None,
    }
    state.runtime_identity = {"uid": 1000, "gid": 1000, "allow_root": False}
    state.persistent_paths = []
    state.configuration = {"secret_keys": [], "no_secrets_required": True}

    component = resolver._finalize(state)

    assert component["license"]["id"] == "AGPL-3.0-only"


def test_model_probe_requires_checksum_and_pinned_license_for_every_model_file():
    spec = next(spec for spec in resolver.SPECS if spec.component == "docling-serve")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    model_url = spec.model_urls[0]

    class IncompleteModelTransport:
        def __init__(self):
            self.urls = []

        def get(self, url, headers=None):
            self.urls.append(url)
            if "/resolve/" in url:
                return resolver.HttpResult(url, url, 404, "text/plain", {}, b"missing")
            payload = {
                "sha": "1" * 40,
                "cardData": {"license": "Apache-2.0"},
                "siblings": [
                    {"rfilename": "model.safetensors", "lfs": {"sha256": "2" * 64}},
                    {"rfilename": "config.json"},
                    {"rfilename": "LICENSE"},
                ],
            }
            return resolver.HttpResult(
                url, url, 200, "application/json", {}, json.dumps(payload).encode()
            )

    transport = IncompleteModelTransport()
    resolver._probe_model(state, transport, model_url)

    assert state.model_artifacts == []
    assert "model-file checksums" in "; ".join(state.missing)
    assert any("/resolve/" + "1" * 40 + "/config.json" in url for url in transport.urls)


def test_model_probe_hashes_pinned_non_lfs_files_and_closes_license():
    spec = next(spec for spec in resolver.SPECS if spec.component == "docling-serve")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    model_url = spec.model_urls[0]
    revision = "1" * 40

    class CompleteModelTransport:
        def get(self, url, headers=None):
            if "/resolve/" in url:
                return resolver.HttpResult(url, url, 200, "application/octet-stream", {}, b"{}")
            payload = {
                "sha": revision,
                "cardData": {"license": "Apache-2.0"},
                "siblings": [
                    {"rfilename": "model.safetensors", "lfs": {"sha256": "2" * 64}},
                    {"rfilename": "config.json"},
                    {"rfilename": "LICENSE"},
                ],
            }
            return resolver.HttpResult(
                url, url, 200, "application/json", {}, json.dumps(payload).encode()
            )

    resolver._probe_model(state, CompleteModelTransport(), model_url)

    assert state.missing == []
    [artifact] = state.model_artifacts
    assert artifact["revision"] == revision
    assert artifact["checksum"].startswith("sha256:")
    assert artifact["license"]["source_url"].endswith(f"/blob/{revision}/LICENSE")


@pytest.mark.parametrize("card_license", ["LicenseRef-internal", "Unknown-1.0", "AGPL-3.0-or-later"])
def test_model_probe_blocks_unknown_license_identifier(card_license):
    spec = next(spec for spec in resolver.SPECS if spec.component == "docling-serve")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    revision = "1" * 40

    class UnknownLicenseTransport:
        def get(self, url, headers=None):
            if "/resolve/" in url:
                return resolver.HttpResult(url, url, 200, "application/octet-stream", {}, b"{}")
            payload = {
                "sha": revision,
                "cardData": {"license": card_license},
                "siblings": [
                    {"rfilename": "model.safetensors", "lfs": {"sha256": "2" * 64}},
                    {"rfilename": "config.json"},
                    {"rfilename": "LICENSE"},
                ],
            }
            return resolver.HttpResult(
                url, url, 200, "application/json", {}, json.dumps(payload).encode()
            )

    resolver._probe_model(state, UnknownLicenseTransport(), spec.model_urls[0])

    assert state.model_artifacts == []
    assert any("trusted SPDX" in item for item in state.missing)


@pytest.mark.parametrize(
    "card_license,canonical",
    [("AGPL-3.0", "AGPL-3.0-only"), ("GPL-2.0", "GPL-2.0-only"), ("GPL-3.0", "GPL-3.0-only")],
)
def test_model_probe_normalizes_spdx_aliases(card_license, canonical):
    spec = next(spec for spec in resolver.SPECS if spec.component == "docling-serve")
    state = resolver.ProbeState(spec=spec, checked_at="2026-08-31T12:00:00Z")
    revision = "1" * 40

    class AliasLicenseTransport:
        def get(self, url, headers=None):
            if "/resolve/" in url:
                return resolver.HttpResult(url, url, 200, "application/octet-stream", {}, b"{}")
            payload = {
                "sha": revision,
                "cardData": {"license": card_license},
                "siblings": [
                    {"rfilename": "model.safetensors", "lfs": {"sha256": "2" * 64}},
                    {"rfilename": "config.json"},
                    {"rfilename": "LICENSE"},
                ],
            }
            return resolver.HttpResult(
                url, url, 200, "application/json", {}, json.dumps(payload).encode()
            )

    resolver._probe_model(state, AliasLicenseTransport(), spec.model_urls[0])

    [artifact] = state.model_artifacts
    assert artifact["license"]["id"] == canonical


@pytest.mark.parametrize(
    "checked_at",
    [
        "2026-08-31 12:00:00Z",
        "2026-08-31T12:00:00z",
        "2026-8-31T12:00:00Z",
        "2026-08-31T12:00Z",
        "2026-08-31T12:00:00+0800",
    ],
)
def test_rfc3339_checker_rejects_noncanonical_datetime_forms(checked_at):
    fixture = lock_fixture()
    fixture["components"]["outline"]["checked_at"] = checked_at

    with pytest.raises(ValidationError):
        validate(fixture, "components-lock")
    with pytest.raises(ValidationError):
        resolver.validate_lock_document(fixture)


@pytest.mark.parametrize(
    "checked_at", ["2026-08-31T12:00:00Z", "2026-08-31T20:00:00.123+08:00"]
)
def test_rfc3339_checker_accepts_canonical_timezone_forms(checked_at):
    fixture = lock_fixture()
    fixture["components"]["outline"]["checked_at"] = checked_at

    validate(fixture, "components-lock")
    resolver.validate_lock_document(fixture)
