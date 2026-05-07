from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from backend.app.services.api_spec_compat import ApiSpecCompat
from backend.app.services.openapi_loader import OpenAPILoader
from backend.app.services.repo_code_api_extractor import RepoCodeApiExtractor
from backend.app.services.risk_scorer import RiskScorer
from backend.app.services.spec_normalizer import SpecNormalizer
from backend.app.services.spec_validator import SpecValidator


GITHUB_API_BASE = "https://api.github.com"
RAW_GITHUB_BASE = "https://raw.githubusercontent.com"
SPEC_EXTENSIONS = {".json", ".yaml", ".yml"}
SPEC_HINTS = ("openapi", "swagger", "api", "spec", "contract")
SPEC_EXCLUDED_FILENAMES = {
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "jsconfig.json",
    "composer.json",
    "manifest.json",
    "schema.json",
}
MAX_SOURCE_FILE_SIZE = 200_000


@dataclass
class ParsedRepoUrl:
    owner: str
    repo: str
    ref: Optional[str] = None
    path: Optional[str] = None
    html_url: Optional[str] = None


class GitHubRepoAnalyzer:
    @staticmethod
    def _headers() -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": "sentinel-api-repo-analyzer",
        }

    @staticmethod
    def _parse_repo_url(url: str) -> ParsedRepoUrl:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("GitHub URL must start with http:// or https://")
        if parsed.netloc not in {"github.com", "www.github.com"}:
            raise ValueError("Only github.com repository URLs are supported")

        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            raise ValueError("GitHub URL must include an owner and repository name")

        owner, repo = parts[0], parts[1].removesuffix(".git")
        ref: Optional[str] = None
        file_path: Optional[str] = None

        if len(parts) >= 4 and parts[2] in {"tree", "blob"}:
            ref = parts[3]
            if len(parts) > 4:
                file_path = "/".join(parts[4:])

        html_url = f"https://github.com/{owner}/{repo}"
        if ref:
            html_url = f"{html_url}/tree/{ref}"
            if file_path:
                html_url = f"https://github.com/{owner}/{repo}/blob/{ref}/{file_path}"

        return ParsedRepoUrl(
            owner=owner,
            repo=repo,
            ref=ref,
            path=file_path,
            html_url=html_url,
        )

    @classmethod
    def _fetch_json(cls, url: str) -> Dict[str, Any]:
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0, headers=cls._headers()) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"GitHub request failed ({exc.response.status_code}) for {url}") from exc
        except httpx.RequestError as exc:
            raise ValueError(f"Failed to reach GitHub: {exc}") from exc

    @classmethod
    def _fetch_text(cls, url: str) -> str:
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0, headers=cls._headers()) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"GitHub file fetch failed ({exc.response.status_code}) for {url}") from exc
        except httpx.RequestError as exc:
            raise ValueError(f"Failed to reach GitHub: {exc}") from exc

    @staticmethod
    def _extension(path: str) -> str:
        dot = path.rfind(".")
        return path[dot:].lower() if dot >= 0 else ""

    @classmethod
    def _list_extensions(cls, file_paths: List[str]) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for path in file_paths:
            filename = path.rsplit("/", 1)[-1]
            ext = cls._extension(path) or "[no extension]"
            if filename.startswith(".") and filename.count(".") == 1:
                ext = "[dotfile]"
            counts[ext] = counts.get(ext, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [{"extension": ext, "count": count} for ext, count in ranked[:15]]

    @staticmethod
    def _language_breakdown(language_bytes: Dict[str, int]) -> List[Dict[str, Any]]:
        total = sum(language_bytes.values()) or 1
        ranked = sorted(language_bytes.items(), key=lambda item: (-item[1], item[0]))
        return [
            {
                "name": language,
                "bytes": size,
                "percent": round((size / total) * 100, 1),
            }
            for language, size in ranked
        ]

    @classmethod
    def _candidate_score(cls, path: str, requested_path: Optional[str]) -> int:
        lower = path.lower()
        score = 0
        if requested_path and path == requested_path:
            score += 100

        tokens = set(token for token in re.split(r"[/._-]+", lower) if token)
        for hint in SPEC_HINTS:
            if hint in tokens:
                score += 20
        if lower.endswith(".yaml") or lower.endswith(".yml"):
            score += 8
        if "/docs/" in lower or lower.startswith("docs/"):
            score += 4
        if lower.rsplit("/", 1)[-1] in SPEC_EXCLUDED_FILENAMES:
            score -= 40
        return score

    @classmethod
    def _discover_spec_candidates(
        cls,
        tree_entries: List[Dict[str, Any]],
        requested_path: Optional[str],
    ) -> List[Dict[str, Any]]:
        blobs = [entry for entry in tree_entries if entry.get("type") == "blob"]
        ranked = []
        for entry in blobs:
            path = entry.get("path", "")
            ext = cls._extension(path)
            if ext not in SPEC_EXTENSIONS:
                continue
            score = cls._candidate_score(path, requested_path)
            if score < 20 and path != requested_path:
                continue
            ranked.append(
                {
                    "path": path,
                    "size": entry.get("size", 0),
                    "format": ext.lstrip("."),
                    "score": score,
                }
            )
        ranked.sort(key=lambda item: (-item["score"], item["path"]))
        return ranked[:12]

    @classmethod
    def _parse_spec_candidate(
        cls,
        parsed_repo: ParsedRepoUrl,
        ref: str,
        candidate_path: str,
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        raw_url = f"{RAW_GITHUB_BASE}/{parsed_repo.owner}/{parsed_repo.repo}/{ref}/{candidate_path}"
        candidate_meta: Dict[str, Any] = {
            "path": candidate_path,
            "raw_url": raw_url,
            "parseable": False,
            "title": None,
            "version": None,
            "total_operations": 0,
            "openapi_version": None,
            "errors": [],
        }

        try:
            content = cls._fetch_text(raw_url)
            ext = cls._extension(candidate_path)
            if ext == ".json":
                spec_raw = OpenAPILoader._parse_json(content)
            else:
                spec_raw = OpenAPILoader._parse_yaml(content)

            compatible_spec = ApiSpecCompat.to_openapi3(spec_raw)
            SpecValidator.validate(compatible_spec)
            normalized = SpecNormalizer.normalize(compatible_spec)
            source_format = ApiSpecCompat.detect_format(spec_raw)
            candidate_meta.update(
                {
                    "parseable": True,
                    "title": normalized.info.get("title", "Unknown"),
                    "version": normalized.info.get("version", "Unknown"),
                    "total_operations": len(normalized.operations),
                    "openapi_version": compatible_spec.get("openapi"),
                    "source_format": source_format.get("kind"),
                    "source_version": source_format.get("version"),
                }
            )
            return compatible_spec, candidate_meta
        except Exception as exc:
            candidate_meta["errors"] = [str(exc)]
            return None, candidate_meta

    @classmethod
    def _rank_selected_spec(
        cls,
        parsed_candidates: List[Tuple[Optional[Dict[str, Any]], Dict[str, Any], int]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        parseable = [item for item in parsed_candidates if item[0] is not None]
        if not parseable:
            raise ValueError(
                "No valid OpenAPI file was found in this repository. "
                "Make sure the repo contains an OpenAPI 3.x YAML or JSON spec."
            )

        parseable.sort(
            key=lambda item: (
                -item[1].get("total_operations", 0),
                -item[2],
                item[1].get("path", ""),
            )
        )
        selected_spec, selected_meta, _ = parseable[0]
        return selected_spec or {}, selected_meta

    @classmethod
    def _build_api_inventory(cls, spec_raw: Dict[str, Any]) -> Dict[str, Any]:
        normalized = SpecNormalizer.normalize(spec_raw)
        detailed_scores = RiskScorer.score_spec(normalized)
        operations: List[Dict[str, Any]] = []
        destructive_count = 0
        high_risk_count = 0

        for op in normalized.operations:
            key = f"{op.path}.{op.method}"
            score = detailed_scores.get(key)
            level = score.level.value if score else "low"
            numeric_score = score.score if score else 0.0
            destructive_count += 1 if op.is_destructive else 0
            high_risk_count += 1 if numeric_score >= 0.6 else 0
            operations.append(
                {
                    "operation_key": key,
                    "method": op.method.upper(),
                    "path": op.path,
                    "summary": op.summary,
                    "description": op.description,
                    "operation_id": op.operationId,
                    "tags": op.tags,
                    "is_destructive": op.is_destructive,
                    "security_schemes": op.security_schemes,
                    "pii_fields": op.pii_fields,
                    "schema_complexity": op.schema_complexity,
                    "risk_score": numeric_score,
                    "risk_level": level,
                    "risk_factors": [factor.model_dump() for factor in score.factors] if score else [],
                    "risk_explanation": score.explanation if score else None,
                }
            )

        operations.sort(key=lambda item: (-item["risk_score"], item["path"], item["method"]))
        return {
            "spec_info": {
                "title": normalized.info.get("title", "Unknown"),
                "version": normalized.info.get("version", "Unknown"),
                "openapi_version": spec_raw.get("openapi", "Unknown"),
                "total_operations": len(normalized.operations),
            },
            "summary": {
                "total_operations": len(normalized.operations),
                "destructive_operations": destructive_count,
                "high_risk_operations": high_risk_count,
            },
            "operations": operations,
        }

    @classmethod
    def _fetch_source_files(
        cls,
        parsed_repo: ParsedRepoUrl,
        ref: str,
        tree_entries: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        file_paths = [
            entry.get("path", "")
            for entry in tree_entries
            if entry.get("type") == "blob"
            and RepoCodeApiExtractor.is_candidate_source_file(entry.get("path", ""))
            and int(entry.get("size", 0) or 0) <= MAX_SOURCE_FILE_SIZE
        ]
        selected_files = RepoCodeApiExtractor.select_source_files(file_paths)
        contents: Dict[str, str] = {}
        for path in selected_files:
            raw_url = f"{RAW_GITHUB_BASE}/{parsed_repo.owner}/{parsed_repo.repo}/{ref}/{path}"
            try:
                contents[path] = cls._fetch_text(raw_url)
            except Exception:
                continue
        return contents

    @classmethod
    def inspect_repo(cls, url: str, selected_path: Optional[str] = None) -> Dict[str, Any]:
        parsed_repo = cls._parse_repo_url(url)

        repo_meta = cls._fetch_json(f"{GITHUB_API_BASE}/repos/{parsed_repo.owner}/{parsed_repo.repo}")
        default_branch = repo_meta.get("default_branch", "main")
        ref = parsed_repo.ref or default_branch

        tree = cls._fetch_json(
            f"{GITHUB_API_BASE}/repos/{parsed_repo.owner}/{parsed_repo.repo}/git/trees/{ref}?recursive=1"
        )
        tree_entries = tree.get("tree", [])
        file_paths = [entry.get("path", "") for entry in tree_entries if entry.get("type") == "blob"]
        language_bytes = cls._fetch_json(f"{GITHUB_API_BASE}/repos/{parsed_repo.owner}/{parsed_repo.repo}/languages")

        requested_path = selected_path or parsed_repo.path
        candidates = cls._discover_spec_candidates(tree_entries, requested_path)
        parsed_candidates: List[Tuple[Optional[Dict[str, Any]], Dict[str, Any], int]] = []

        for candidate in candidates:
            spec_raw, candidate_meta = cls._parse_spec_candidate(parsed_repo, ref, candidate["path"])
            candidate_meta["candidate_score"] = candidate["score"]
            parsed_candidates.append((spec_raw, candidate_meta, candidate["score"]))

        source_files = cls._fetch_source_files(parsed_repo, ref, tree_entries)
        code_analysis = RepoCodeApiExtractor.analyze_repo_sources(source_files)

        selected_source_kind = "openapi"
        selected_spec_raw: Dict[str, Any]
        selected_spec: Dict[str, Any]
        if any(item[0] is not None for item in parsed_candidates):
            selected_spec_raw, selected_spec = cls._rank_selected_spec(parsed_candidates)
        elif code_analysis["summary"]["route_count"] > 0:
            selected_spec_raw = RepoCodeApiExtractor.synthesize_openapi_spec(
                repo_name=repo_meta.get("name", parsed_repo.repo),
                repo_description=repo_meta.get("description"),
                code_analysis=code_analysis,
            )
            selected_spec = {
                "path": "[source-code]",
                "raw_url": None,
                "parseable": True,
                "title": selected_spec_raw.get("info", {}).get("title"),
                "version": selected_spec_raw.get("info", {}).get("version"),
                "total_operations": code_analysis["summary"]["route_count"],
                "openapi_version": selected_spec_raw.get("openapi"),
                "errors": [],
                "candidate_score": 0,
                "source_kind": "code",
            }
            selected_source_kind = "code"
        else:
            raise ValueError(
                "No valid OpenAPI file or supported framework routes were found in this repository. "
                "Sentinel currently extracts APIs from OpenAPI specs and common framework code such as FastAPI, Flask, Django, Express, Fastify, Koa, Hono, NestJS, Bottle, and Sanic."
            )

        api_inventory = cls._build_api_inventory(selected_spec_raw)
        api_inventory["source_kind"] = selected_source_kind
        api_inventory["code_analysis"] = code_analysis

        approval_required = api_inventory["summary"]["destructive_operations"] > 0 or api_inventory["summary"]["high_risk_operations"] > 0
        approval_prompt = (
            "This repository contains destructive or high-risk API operations. Approve report generation to continue."
            if approval_required
            else "Repository inspection looks safe enough for a standard report run."
        )

        candidate_summaries = [meta for _, meta, _ in parsed_candidates]
        repo_inspection = {
            "source_url": url,
            "repo_url": repo_meta.get("html_url") or parsed_repo.html_url,
            "name": repo_meta.get("name", parsed_repo.repo),
            "full_name": repo_meta.get("full_name", f"{parsed_repo.owner}/{parsed_repo.repo}"),
            "description": repo_meta.get("description"),
            "owner": parsed_repo.owner,
            "default_branch": default_branch,
            "selected_ref": ref,
            "stars": repo_meta.get("stargazers_count", 0),
            "watchers": repo_meta.get("watchers_count", 0),
            "forks": repo_meta.get("forks_count", 0),
            "visibility": repo_meta.get("visibility", "public"),
            "languages": cls._language_breakdown(language_bytes),
            "file_formats": cls._list_extensions(file_paths),
            "total_files": len(file_paths),
            "detected_frameworks": code_analysis.get("frameworks", []),
            "code_route_count": code_analysis.get("summary", {}).get("route_count", 0),
            "selected_source_kind": selected_source_kind,
            "candidate_specs": candidate_summaries,
            "selected_spec": selected_spec,
            "approval_required": approval_required,
            "approval_prompt": approval_prompt,
        }

        api_manifest = {
            "manifest_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": {
                "type": "github_repo",
                "url": url,
                "owner": parsed_repo.owner,
                "repo": parsed_repo.repo,
                "ref": ref,
            },
            "repository": {
                "name": repo_inspection["name"],
                "full_name": repo_inspection["full_name"],
                "description": repo_inspection["description"],
                "repo_url": repo_inspection["repo_url"],
                "default_branch": default_branch,
                "visibility": repo_inspection["visibility"],
            },
            "tech_stack": {
                "languages": repo_inspection["languages"],
                "file_formats": repo_inspection["file_formats"],
                "total_files": repo_inspection["total_files"],
            },
            "api_catalog": {
                "source_kind": selected_source_kind,
                "selected_spec": selected_spec,
                "candidate_specs": candidate_summaries,
                **api_inventory,
            },
        }

        return {
            "repo_inspection": repo_inspection,
            "api_manifest": api_manifest,
            "selected_spec_raw": selected_spec_raw,
        }
