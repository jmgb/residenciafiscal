"""Preflight y ejecución explícita del piloto C2 con Codex CLI."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import selectors
import shlex
import shutil
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from deep_research_bundle import BUNDLE_MANIFEST_NAME, verify_deep_research_bundle
from deep_research_contracts import (
    DeepResearchJob,
    DeepResearchLimits,
    DeepResearchOutput,
    DeepResearchPilotPlan,
    DeepResearchPilotQuestion,
    DeepResearchPilotSpec,
)
from jurisprudence_retrieval_corpus import load_retrieval_corpus
from jurisprudence_sample_evaluation_models import RetrievalEvaluationBank
from okf_provenance import sha256_file
from verbatim_artifact import load_verbatim_corpus

PILOT_SOURCE_SCHEMA = "residenciafiscal-chat-f02-dev-set/1"


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _normalise_question(value: str) -> str:
    return " ".join(value.casefold().split())


def _assert_resource_path(path: Path, declared: str, project_root: Path, label: str) -> None:
    expected = (project_root / Path(*PurePosixPath(declared).parts)).resolve()
    if path.resolve() != expected:
        raise ValueError(f"{label} no coincide con el recurso bloqueado")


def _load_source_questions(path: Path) -> tuple[DeepResearchPilotQuestion, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != PILOT_SOURCE_SCHEMA:
        raise ValueError("el banco fuente no es el dev set C2 esperado")
    questions = raw.get("questions")
    if not isinstance(questions, list):
        raise ValueError("el banco fuente no contiene questions")
    parsed = tuple(DeepResearchPilotQuestion.model_validate(item) for item in questions)
    if len(parsed) != len({item.question_id for item in parsed}):
        raise ValueError("el banco fuente contiene question_id duplicado")
    return parsed


def _load_holdout(path: Path) -> RetrievalEvaluationBank:
    return RetrievalEvaluationBank.model_validate_json(path.read_bytes())


def _assert_lock(spec: DeepResearchPilotSpec, source_path: Path, holdout_path: Path) -> None:
    if sha256_file(source_path) != spec.source_sha256:
        raise ValueError("hash del banco fuente no coincide con el lock C2")
    if sha256_file(holdout_path) != spec.holdout_sha256:
        raise ValueError("hash del holdout no coincide con el lock C2")


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as destination:
        destination.write(payload)


def _build_pilot_plan(
    *,
    project_root: Path,
    spec_path: Path,
    source_path: Path,
    holdout_path: Path,
    bundle_path: Path,
    limits: DeepResearchLimits | None = None,
) -> DeepResearchPilotPlan:
    """Valida los locks y crea el plan en memoria, sin llamar a un modelo."""

    project_root = project_root.resolve()
    spec = DeepResearchPilotSpec.model_validate_json(spec_path.read_bytes())
    _assert_resource_path(source_path, spec.source_resource, project_root, "source_resource")
    _assert_resource_path(holdout_path, spec.holdout_resource, project_root, "holdout_resource")
    _assert_lock(spec, source_path, holdout_path)
    bundle_manifest = verify_deep_research_bundle(bundle_path)
    source_questions = _load_source_questions(source_path)
    holdout = _load_holdout(holdout_path)

    by_id = {item.question_id: item for item in source_questions}
    holdout_ids = {item.question_id for item in holdout.questions}
    holdout_questions = {_normalise_question(item.question) for item in holdout.questions}
    selected: list[DeepResearchPilotQuestion] = []
    for question_id in spec.question_ids:
        question = by_id.get(question_id)
        if question is None:
            raise ValueError(f"question_id ausente del banco fuente: {question_id}")
        if (
            question_id in holdout_ids
            or _normalise_question(question.question) in holdout_questions
        ):
            raise ValueError(f"la pregunta {question_id} pertenece al holdout")
        selected.append(question)

    selected_questions = tuple(selected)
    selected_limits = limits or DeepResearchLimits()
    jobs = tuple(
        DeepResearchJob(
            schema_version="residenciafiscal-deep-research-job/1",
            job_id=f"{spec.pilot_id}-{index:02d}",
            request_id=f"{spec.pilot_id}-{index:02d}",
            bundle_id=str(bundle_manifest["bundle_id"]),
            question=question.question,
            limits=selected_limits,
        )
        for index, question in enumerate(selected_questions, start=1)
    )
    plan = DeepResearchPilotPlan(
        schema_version="residenciafiscal-deep-research-plan/1",
        pilot_id=spec.pilot_id,
        source_resource=spec.source_resource,
        source_sha256=spec.source_sha256,
        holdout_resource=spec.holdout_resource,
        holdout_sha256=spec.holdout_sha256,
        bundle_id=str(bundle_manifest["bundle_id"]),
        bundle_sha256=sha256_file(bundle_path),
        questions=selected_questions,
        jobs=jobs,
    )

    return plan


def prepare_pilot(
    *,
    project_root: Path,
    spec_path: Path,
    source_path: Path,
    holdout_path: Path,
    bundle_path: Path,
    output_dir: Path,
    limits: DeepResearchLimits | None = None,
) -> DeepResearchPilotPlan:
    """Valida los locks y materializa jobs, sin llamar a ningún modelo."""

    plan = _build_pilot_plan(
        project_root=project_root,
        spec_path=spec_path,
        source_path=source_path,
        holdout_path=holdout_path,
        bundle_path=bundle_path,
        limits=limits,
    )
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"el directorio del piloto no está vacío: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_new(output_dir / "PLAN.json", _json_bytes(plan.model_dump(mode="json")))
    for job in plan.jobs:
        _write_new(
            output_dir / "jobs" / f"{job.job_id}.json", _json_bytes(job.model_dump(mode="json"))
        )
    return plan


def _prompt_for(job: DeepResearchJob) -> str:
    return f"""Actúa como explorador jurídico offline para residencia fiscal española.

Pregunta del job {job.job_id}: {job.question}

Reglas obligatorias:
- Solo puedes leer los archivos del workspace actual, que es un bundle inmutable.
- Lee MANIFEST.json y usa exclusivamente los artefactos listados allí.
- No uses internet, web search, red, otros directorios, credenciales ni repositorios.
- No escribas archivos ni modifiques el workspace; la ejecución es no interactiva.
- Para que los límites de lectura sean verificables, usa solo comandos simples con rutas
  literales; no uses intérpretes, shell, variables, globbing, pipes ni redirecciones.
- No inventes identificadores, autoridad, hechos, páginas, hashes ni citas.
- Para cada claim sustantivo aporta evidencias con cita literal, página física y hash del
  PDF tal como aparecen en el bundle. Si no puedes verificarlo, no lo afirmes.
- Si el bundle no basta, usa estado parcial, pregunta o abstención y explica el límite.
- Devuelve únicamente un JSON válido que cumpla el esquema de salida proporcionado.
- No incluyas cadena de pensamiento ni razonamiento interno; solo respuesta, límites, claims
  y evidencias operativas.

El job_id debe ser "{job.job_id}" y request_id debe ser "{job.request_id}".
"""


def codex_command(
    *,
    job: DeepResearchJob,
    workspace: Path,
    schema_path: Path,
    output_path: Path,
    codex_binary: str = "codex",
    model: str | None = None,
    sandbox_binary: str | None = "bwrap",
) -> list[str]:
    """Construye el comando C2 dentro de una frontera de filesystem externa."""

    inner_command = [
        *_resolve_codex_binary(codex_binary, sandbox_binary),
        "--ask-for-approval",
        "never",
        "exec",
        "--cd",
        "/workspace" if sandbox_binary else str(workspace),
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox",
        "read-only",
        "--json",
        "--color",
        "never",
        "--output-schema",
        "/schema.json" if sandbox_binary else str(schema_path),
        "--output-last-message",
        f"/output/{output_path.name}" if sandbox_binary else str(output_path),
    ]
    if model:
        inner_command.extend(["--model", model])
    inner_command.append(_prompt_for(job))
    if sandbox_binary is None:
        return inner_command

    return _wrap_in_filesystem_sandbox(
        inner_command=inner_command,
        workspace=workspace,
        schema_path=schema_path,
        output_path=output_path,
        sandbox_binary=sandbox_binary,
    )


def _resolve_codex_binary(codex_binary: str, sandbox_binary: str | None) -> list[str]:
    parts = shlex.split(codex_binary)
    if not parts:
        raise ValueError("codex_binary no puede estar vacío")
    if sandbox_binary is None:
        return parts
    if len(parts) != 1:
        raise ValueError("el modo sandbox requiere un único binario Codex")
    resolved = shutil.which(parts[0])
    if resolved is None:
        raise FileNotFoundError(f"no se encuentra el binario Codex: {parts[0]}")
    return [str(Path(resolved).resolve())]


def _wrap_in_filesystem_sandbox(
    *,
    inner_command: list[str],
    workspace: Path,
    schema_path: Path,
    output_path: Path,
    sandbox_binary: str,
) -> list[str]:
    """Aísla Codex del repo y del host; deja solo bundle, schema y salida visibles."""

    sandbox_parts = shlex.split(sandbox_binary)
    if not sandbox_parts:
        raise ValueError("sandbox_binary no puede estar vacío")
    workspace = workspace.resolve()
    schema_path = schema_path.resolve()
    output_path = output_path.resolve()
    codex_path = Path(inner_command[0])
    nvm_root = Path.home() / ".nvm"
    if codex_path.is_relative_to(nvm_root.resolve()):
        runtime_mount = (nvm_root.resolve(), nvm_root.resolve())
        node_bin = next(
            (parent / "bin" for parent in codex_path.parents if parent.parent.name == "node"),
            None,
        )
        if node_bin is None:
            raise ValueError("no se pudo localizar el runtime Node del binario Codex")
        runtime_path = f"{node_bin}:/usr/local/bin:/usr/bin:/bin"
    elif codex_path.is_relative_to(Path("/usr")):
        runtime_mount = None
        runtime_path = "/usr/local/bin:/usr/bin:/bin"
    else:
        raise ValueError("el binario Codex debe estar en /usr o en $CODEX_HOME/.nvm")

    command = [
        *sandbox_parts,
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--unshare-net",
        "--clearenv",
        "--tmpfs",
        "/",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/usr/local",
        "/usr/local",
        "--ro-bind",
        "/bin",
        "/bin",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        "/lib64",
        "/lib64",
        "--ro-bind",
        "/etc",
        "/etc",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/tmp/codex-home",
        "--ro-bind",
        str(workspace),
        "/workspace",
        "--ro-bind",
        str(schema_path),
        "/schema.json",
        "--bind",
        str(output_path.parent),
        "/output",
        "--setenv",
        "HOME",
        "/tmp/codex-home",
        "--setenv",
        "CODEX_HOME",
        "/codex-home",
        "--setenv",
        "PATH",
        runtime_path,
        "--setenv",
        "LANG",
        os.environ.get("LANG", "C.UTF-8"),
        "--chdir",
        "/workspace",
    ]
    if runtime_mount:
        command.extend(
            ["--dir", "/home", "--dir", str(Path.home()), "--ro-bind", *map(str, runtime_mount)]
        )
    command.extend(["--", *inner_command])
    return command


def _telemetry_delta(event: object) -> tuple[int, int, int, int]:
    if not isinstance(event, dict):
        return 0, 0, 0, 0
    turns = int(event.get("type") == "turn.started")
    tool_calls = 0
    item = event.get("item")
    if (
        event.get("type") == "item.started"
        and isinstance(item, dict)
        and item.get("type") in {"command_execution", "function_call", "mcp_tool_call"}
    ):
        tool_calls = 1
    usage = event.get("usage")
    if not isinstance(usage, dict):
        return turns, tool_calls, 0, 0
    try:
        input_tokens = int(usage.get("input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
    except (TypeError, ValueError):
        return turns, tool_calls, 0, 0
    if input_tokens < 0 or output_tokens < 0:
        return turns, tool_calls, 0, 0
    return turns, tool_calls, input_tokens, output_tokens


def _estimated_cost(
    input_tokens: int,
    output_tokens: int,
    input_cost_microusd_per_million: int,
    output_cost_microusd_per_million: int,
) -> int:
    return math.ceil(
        (
            input_tokens * input_cost_microusd_per_million
            + output_tokens * output_cost_microusd_per_million
        )
        / 1_000_000
    )


_COMMAND_SHELL_SYNTAX = re.compile(r"[;&|`$()<>*?{}\[\]!\\\n\r]")
_NON_READING_COMMANDS = frozenset({"echo", "false", "ls", "printf", "pwd", "true"})


def _literal_read_command_paths(command: str, workspace: Path) -> tuple[Path, ...] | None:
    """Devuelve las rutas que puede leer un comando simple, o None si es ambiguo."""

    if not command or _COMMAND_SHELL_SYNTAX.search(command):
        return None
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    if not argv:
        return None

    executable = Path(argv[0]).name
    if executable in _NON_READING_COMMANDS:
        return ()
    if executable != "cat":
        return None

    arguments = argv[1:]
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    if not arguments or any(argument.startswith("-") for argument in arguments):
        return None

    workspace = workspace.resolve()
    paths: list[Path] = []
    for argument in arguments:
        portable = PurePosixPath(argument)
        if portable.is_absolute():
            if portable.parts[:2] != ("/", "workspace"):
                return None
            portable = PurePosixPath(*portable.parts[2:])
        if not portable.parts or ".." in portable.parts or "\\" in argument:
            return None
        path = (workspace / Path(*portable.parts)).resolve()
        if not path.is_relative_to(workspace):
            return None
        paths.append(path)
    return tuple(paths)


def _resource_from_literal_path(
    path: Path, workspace: Path
) -> tuple[set[str], set[tuple[str, int]], bool]:
    """Cuenta un artefacto solo cuando la ruta literal se puede auditar."""

    relative = path.resolve().relative_to(workspace.resolve()).as_posix()
    if relative == "retrieval/rollout-106.corpus.json":
        try:
            load_retrieval_corpus(path.read_bytes())
        except (FileNotFoundError, ValueError):
            return set(), set(), True
        # Es un índice agregado, no una lectura de documentos fuente. Las
        # lecturas que consumen presupuesto son las rutas per-documento
        # (`cases`, `verbatim`, `pdf`); las evidencias siguen teniendo un gate
        # independiente al validar la salida.
        return set(), set(), False
    match = re.fullmatch(
        r"(?P<kind>cases|verbatim|retrieval|jurisdicciones|pdf)/"
        r"(?P<document>[A-Za-z0-9][A-Za-z0-9_-]*)"
        r"(?P<suffix>\.pages\.json|\.pdf|\.case\.json|\.issues\.json|\.roles\.json)",
        relative,
    )
    if match is None:
        if relative.startswith("retrieval/"):
            return set(), set(), True
        return set(), set(), False

    document = match.group("document")
    documents = {document}
    if match.group("kind") not in {"verbatim", "pdf"}:
        return documents, set(), False

    corpus_path = workspace / "verbatim" / f"{document}.pages.json"
    try:
        verbatim_corpus = load_verbatim_corpus(corpus_path.read_bytes())
    except (FileNotFoundError, ValueError):
        return documents, set(), True
    return documents, {(document, page.page_index) for page in verbatim_corpus.pages}, False


def _resource_delta(event: object, workspace: Path) -> tuple[set[str], set[tuple[str, int]], bool]:
    """Audita accesos literales y falla cerrado ante comandos indirectos."""

    if not isinstance(event, dict) or event.get("type") != "item.started":
        return set(), set(), False
    item = event.get("item")
    if not isinstance(item, dict) or item.get("type") != "command_execution":
        return set(), set(), False
    command = item.get("command")
    if not isinstance(command, str):
        return set(), set(), True
    literal_paths = _literal_read_command_paths(command, workspace)
    if literal_paths is None:
        return set(), set(), True

    documents: set[str] = set()
    pages: set[tuple[str, int]] = set()
    for path in literal_paths:
        resource_documents, resource_pages, audit_failed = _resource_from_literal_path(
            path, workspace
        )
        documents.update(resource_documents)
        pages.update(resource_pages)
        if audit_failed:
            return documents, pages, True
    return documents, pages, False


@dataclass(frozen=True)
class _CodexExecution:
    returncode: int
    stdout: str
    turns: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    documents_read: int
    pages_read: int
    stop_limit: str | None = None


def _run_codex(
    command: list[str],
    job: DeepResearchJob,
    workspace: Path,
    input_cost_microusd_per_million: int,
    output_cost_microusd_per_million: int,
) -> _CodexExecution:
    """Ejecuta Codex y corta el proceso al alcanzar cualquier límite operativo."""

    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    stdout_parts: list[str] = []
    pending = b""
    turns = 0
    tool_calls = 0
    input_tokens = 0
    output_tokens = 0
    document_ids_read: set[str] = set()
    page_ids_read: set[tuple[str, int]] = set()
    stop_limit: str | None = None
    deadline = time.monotonic() + job.limits.timeout_ms / 1_000

    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stop_limit = "runner_timeout"
                break
            for key, _ in selector.select(min(remaining, 0.25)):
                chunk = os.read(key.fd, 65_536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                pending += chunk
                while b"\n" in pending:
                    raw_line, pending = pending.split(b"\n", 1)
                    line = raw_line.decode("utf-8", errors="replace") + "\n"
                    stdout_parts.append(line)
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = _telemetry_delta(event)
                    turns += delta[0]
                    tool_calls += delta[1]
                    input_tokens += delta[2]
                    output_tokens += delta[3]
                    resource_documents, resource_pages, resource_audit_failed = _resource_delta(
                        event, workspace
                    )
                    document_ids_read.update(resource_documents)
                    page_ids_read.update(resource_pages)
                    if resource_audit_failed:
                        stop_limit = "resource_audit"
                    elif len(document_ids_read) > job.limits.max_documents:
                        stop_limit = "max_documents_read"
                    elif len(page_ids_read) > job.limits.max_pages:
                        stop_limit = "max_pages_read"
                    elif turns > job.limits.max_turns:
                        stop_limit = "max_turns"
                    elif tool_calls > job.limits.max_tool_calls:
                        stop_limit = "max_tool_calls"
                    elif (
                        _estimated_cost(
                            input_tokens,
                            output_tokens,
                            input_cost_microusd_per_million,
                            output_cost_microusd_per_million,
                        )
                        > job.limits.max_cost_microusd
                    ):
                        stop_limit = "max_cost_microusd"
                    if stop_limit:
                        break
                if stop_limit:
                    break
            if stop_limit:
                break
    finally:
        if stop_limit and process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)
        remaining_output = process.stdout.read()
        if remaining_output:
            pending += remaining_output
        if pending:
            stdout_parts.append(pending.decode("utf-8", errors="replace"))
        selector.close()

    return _CodexExecution(
        returncode=process.returncode,
        stdout="".join(stdout_parts),
        turns=turns,
        tool_calls=tool_calls,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        documents_read=len(document_ids_read),
        pages_read=len(page_ids_read),
        stop_limit=stop_limit,
    )


def _extract_bundle(bundle_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(bundle_path) as archive:
        for info in archive.infolist():
            if info.filename == BUNDLE_MANIFEST_NAME:
                continue
            relative = PurePosixPath(info.filename)
            target = (destination / Path(*relative.parts)).resolve()
            if not target.is_relative_to(destination) or relative.is_absolute():
                raise ValueError("entrada insegura durante la extracción del bundle")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                output.write(archive.read(info))
        (destination / BUNDLE_MANIFEST_NAME).write_bytes(archive.read(BUNDLE_MANIFEST_NAME))


def _error_output(job: DeepResearchJob, limit: str) -> DeepResearchOutput:
    return DeepResearchOutput(
        schema_version="residenciafiscal-deep-research-output/1",
        job_id=job.job_id,
        request_id=job.request_id,
        status="error",
        text="No se ha podido completar la investigación profunda.",
        limits=(limit,),
        claims=(),
        evidence=(),
    )


def validate_output_evidence(output: DeepResearchOutput, workspace: Path) -> bool:
    """Comprueba cada evidencia contra verbatim y PDF del workspace efímero."""

    if output.status in {"completa", "parcial"} and (not output.claims or not output.evidence):
        return False
    referenced_indexes = {index for claim in output.claims for index in claim.evidence_indexes}
    if referenced_indexes != set(range(1, len(output.evidence) + 1)):
        return False
    for evidence in output.evidence:
        verbatim_path = workspace / "verbatim" / f"{evidence.judgment_id}.pages.json"
        pdf_path = workspace / "pdf" / f"{evidence.judgment_id}.pdf"
        if not verbatim_path.is_file() or not pdf_path.is_file():
            return False
        try:
            corpus = load_verbatim_corpus(verbatim_path.read_bytes())
        except ValueError:
            return False
        if corpus.document_id != evidence.judgment_id:
            return False
        if evidence.source_sha256 != corpus.source_sha256:
            return False
        if sha256_file(pdf_path) != corpus.source_sha256:
            return False
        page = next((item for item in corpus.pages if item.page_index == evidence.page), None)
        if page is None or evidence.quote not in page.raw_page_text:
            return False
    return True


def run_pilot(
    *,
    plan_path: Path,
    project_root: Path,
    spec_path: Path,
    source_path: Path,
    holdout_path: Path,
    bundle_path: Path,
    output_dir: Path,
    codex_binary: str = "codex",
    sandbox_binary: str | None = "bwrap",
    model: str | None = None,
    input_cost_microusd_per_million: int | None = None,
    output_cost_microusd_per_million: int | None = None,
) -> tuple[DeepResearchOutput, ...]:
    """Ejecuta el plan solo si sigue coincidiendo con sus locks originales."""

    try:
        plan = DeepResearchPilotPlan.model_validate_json(plan_path.read_bytes())
    except ValueError as error:
        raise ValueError(f"PLAN.json inválido: {error}") from error
    if input_cost_microusd_per_million is None or output_cost_microusd_per_million is None:
        raise ValueError("el runner necesita tarifas confiables para aplicar max_cost_microusd")
    if input_cost_microusd_per_million < 0 or output_cost_microusd_per_million < 0:
        raise ValueError("las tarifas no pueden ser negativas")
    if sandbox_binary is not None:
        raise RuntimeError(
            "el runner fail-closed necesita el worker autenticado de Alfredo: "
            "falta un broker externo que separe credenciales y egress de las herramientas"
        )
    plan_limits = plan.jobs[0].limits
    if any(job.limits != plan_limits for job in plan.jobs):
        raise ValueError("PLAN.json contiene límites inconsistentes entre jobs")
    expected_plan = _build_pilot_plan(
        project_root=project_root,
        spec_path=spec_path,
        source_path=source_path,
        holdout_path=holdout_path,
        bundle_path=bundle_path,
        limits=plan_limits,
    )
    if plan.model_dump(mode="json") != expected_plan.model_dump(mode="json"):
        raise ValueError("PLAN.json no coincide con los locks fuente, holdout, bundle o límites")

    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    schema_path = (output_dir / "deep-research-output.schema.json").resolve()
    if not schema_path.exists():
        _write_new(schema_path, _json_bytes(DeepResearchOutput.model_json_schema()))

    results: list[DeepResearchOutput] = []
    for job in plan.jobs:
        result_path = results_dir / f"{job.job_id}.json"
        if result_path.exists():
            raise FileExistsError(result_path)
        with tempfile.TemporaryDirectory(prefix=f"deep-research-{job.job_id}-") as workspace_name:
            workspace = Path(workspace_name)
            _extract_bundle(bundle_path, workspace)
            with tempfile.TemporaryDirectory(
                prefix=f"deep-research-answer-{job.job_id}-"
            ) as answer_dir_name:
                answer_path = Path(answer_dir_name) / "answer.json"
                command = codex_command(
                    job=job,
                    workspace=workspace,
                    schema_path=schema_path,
                    output_path=answer_path,
                    codex_binary=codex_binary,
                    model=model,
                    sandbox_binary=sandbox_binary,
                )
                execution = _run_codex(
                    command,
                    job,
                    workspace,
                    input_cost_microusd_per_million,
                    output_cost_microusd_per_million,
                )
                if execution.stop_limit:
                    output = _error_output(job, execution.stop_limit)
                elif execution.returncode != 0:
                    output = _error_output(job, "runner_failed")
                elif execution.turns == 0:
                    output = _error_output(job, "runner_missing_telemetry")
                elif execution.input_tokens == 0 and execution.output_tokens == 0:
                    output = _error_output(job, "runner_missing_usage")
                elif not answer_path.is_file():
                    output = _error_output(job, "runner_missing_output")
                else:
                    try:
                        output = DeepResearchOutput.model_validate_json(answer_path.read_bytes())
                    except ValueError:
                        output = _error_output(job, "runner_invalid_output")
                    if output.job_id != job.job_id or output.request_id != job.request_id:
                        output = _error_output(job, "runner_job_mismatch")
                    elif output.status == "error":
                        pass
                    else:
                        estimated_cost = _estimated_cost(
                            execution.input_tokens,
                            execution.output_tokens,
                            input_cost_microusd_per_million,
                            output_cost_microusd_per_million,
                        )
                        if estimated_cost > job.limits.max_cost_microusd:
                            output = _error_output(job, "max_cost_microusd")
                        else:
                            output = output.model_copy(
                                update={
                                    "cost_microusd": estimated_cost,
                                    "cost_measurement": "ESTIMATED",
                                }
                            )
                            if (
                                len({item.judgment_id for item in output.evidence})
                                > job.limits.max_documents
                            ):
                                output = _error_output(job, "max_documents")
                            elif (
                                len({(item.judgment_id, item.page) for item in output.evidence})
                                > job.limits.max_pages
                            ):
                                output = _error_output(job, "max_pages")
                            elif not validate_output_evidence(output, workspace):
                                output = _error_output(job, "citation_verification")
        _write_new(result_path, _json_bytes(output.model_dump(mode="json")))
        results.append(output)
    return tuple(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--project-root", type=Path, default=Path("."))
    prepare.add_argument("--spec", type=Path, required=True)
    prepare.add_argument("--source", type=Path, required=True)
    prepare.add_argument("--holdout", type=Path, required=True)
    prepare.add_argument("--bundle", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--project-root", type=Path, default=Path("."))
    run.add_argument("--spec", type=Path, required=True)
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--holdout", type=Path, required=True)
    run.add_argument("--bundle", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--codex-binary", default="codex")
    run.add_argument("--sandbox-binary", default="bwrap")
    run.add_argument("--model")
    run.add_argument("--input-cost-microusd-per-million", type=int, required=True)
    run.add_argument("--output-cost-microusd-per-million", type=int, required=True)

    arguments = parser.parse_args(argv)
    if arguments.command == "prepare":
        plan = prepare_pilot(
            project_root=arguments.project_root,
            spec_path=arguments.spec,
            source_path=arguments.source,
            holdout_path=arguments.holdout,
            bundle_path=arguments.bundle,
            output_dir=arguments.output,
        )
        print(
            json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        )
        return 0

    results = run_pilot(
        plan_path=arguments.plan,
        project_root=arguments.project_root,
        spec_path=arguments.spec,
        source_path=arguments.source,
        holdout_path=arguments.holdout,
        bundle_path=arguments.bundle,
        output_dir=arguments.output,
        codex_binary=arguments.codex_binary,
        sandbox_binary=arguments.sandbox_binary,
        model=arguments.model,
        input_cost_microusd_per_million=arguments.input_cost_microusd_per_million,
        output_cost_microusd_per_million=arguments.output_cost_microusd_per_million,
    )
    print(
        json.dumps(
            {"results": [{"job_id": item.job_id, "status": item.status} for item in results]},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
