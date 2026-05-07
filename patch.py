import re

with open("backend/app/services/github_repo_analyzer.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update _fetch_json
code = code.replace("    @classmethod\n    def _fetch_json(cls, url: str) -> Dict[str, Any]:\n        try:\n            with httpx.Client(follow_redirects=True, timeout=20.0, headers=cls._headers()) as client:\n                response = client.get(url)", "    @classmethod\n    async def _fetch_json(cls, url: str) -> Dict[str, Any]:\n        try:\n            async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, headers=cls._headers()) as client:\n                response = await client.get(url)")

# 2. Update _fetch_text
code = code.replace("    @classmethod\n    def _fetch_text(cls, url: str) -> str:\n        try:\n            with httpx.Client(follow_redirects=True, timeout=20.0, headers=cls._headers()) as client:\n                response = client.get(url)", "    @classmethod\n    async def _fetch_text(cls, url: str) -> str:\n        try:\n            async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, headers=cls._headers()) as client:\n                response = await client.get(url)")

# 3. Update _parse_spec_candidate
code = code.replace("    @classmethod\n    def _parse_spec_candidate(", "    @classmethod\n    async def _parse_spec_candidate(")
code = code.replace("            content = cls._fetch_text(raw_url)", "            content = await cls._fetch_text(raw_url)")

# 4. Update _fetch_source_files
code = code.replace("    @classmethod\n    def _fetch_source_files(", "    @classmethod\n    async def _fetch_source_files(")
code = re.sub(
    r"        contents: Dict\[str, str\] = \{\}\n        for path in selected_files:\n            raw_url = f\"\{RAW_GITHUB_BASE\}/\{parsed_repo\.owner\}/\{parsed_repo\.repo\}/\{ref\}/\{path\}\"\n            try:\n                contents\[path\] = cls\._fetch_text\(raw_url\)\n            except Exception:\n                continue\n        return contents",
    "        import asyncio\n        async def fetch(path):\n            raw_url = f\"{RAW_GITHUB_BASE}/{parsed_repo.owner}/{parsed_repo.repo}/{ref}/{path}\"\n            try:\n                return path, await cls._fetch_text(raw_url)\n            except Exception:\n                return path, None\n\n        results = await asyncio.gather(*(fetch(p) for p in selected_files))\n        return {p: text for p, text in results if text is not None}",
    code
)

# 5. Update inspect_repo
code = code.replace("    @classmethod\n    def inspect_repo(cls, url: str, selected_path: Optional[str] = None) -> Dict[str, Any]:", "    @classmethod\n    async def inspect_repo(cls, url: str, selected_path: Optional[str] = None) -> Dict[str, Any]:")
code = code.replace("        repo_meta = cls._fetch_json(f\"{GITHUB_API_BASE}/repos/{parsed_repo.owner}/{parsed_repo.repo}\")", "        repo_meta = await cls._fetch_json(f\"{GITHUB_API_BASE}/repos/{parsed_repo.owner}/{parsed_repo.repo}\")")
code = code.replace("        tree = cls._fetch_json(\n            f\"{GITHUB_API_BASE}/repos/{parsed_repo.owner}/{parsed_repo.repo}/git/trees/{ref}?recursive=1\"\n        )", "        tree = await cls._fetch_json(\n            f\"{GITHUB_API_BASE}/repos/{parsed_repo.owner}/{parsed_repo.repo}/git/trees/{ref}?recursive=1\"\n        )")
code = code.replace("        language_bytes = cls._fetch_json(f\"{GITHUB_API_BASE}/repos/{parsed_repo.owner}/{parsed_repo.repo}/languages\")", "        language_bytes = await cls._fetch_json(f\"{GITHUB_API_BASE}/repos/{parsed_repo.owner}/{parsed_repo.repo}/languages\")")

code = re.sub(
    r"        for candidate in candidates:\n            spec_raw, candidate_meta = cls\._parse_spec_candidate\(parsed_repo, ref, candidate\[\"path\"\]\)\n            candidate_meta\[\"candidate_score\"\] = candidate\[\"score\"\]\n            parsed_candidates\.append\(\(spec_raw, candidate_meta, candidate\[\"score\"\]\)\)",
    "        import asyncio\n        async def parse(candidate):\n            spec_raw, candidate_meta = await cls._parse_spec_candidate(parsed_repo, ref, candidate[\"path\"])\n            candidate_meta[\"candidate_score\"] = candidate[\"score\"]\n            return (spec_raw, candidate_meta, candidate[\"score\"])\n        \n        parsed_candidates = await asyncio.gather(*(parse(c) for c in candidates))",
    code
)

code = code.replace("        source_files = cls._fetch_source_files(parsed_repo, ref, tree_entries)", "        source_files = await cls._fetch_source_files(parsed_repo, ref, tree_entries)")

with open("backend/app/services/github_repo_analyzer.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Patched GitHubRepoAnalyzer")
