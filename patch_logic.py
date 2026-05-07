with open("backend/app/services/github_repo_analyzer.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace the fetching and conditional logic
old_logic = """        source_files = await cls._fetch_source_files(parsed_repo, ref, tree_entries)
        code_analysis = RepoCodeApiExtractor.analyze_repo_sources(source_files)

        selected_source_kind = "openapi"
        selected_spec_raw: Dict[str, Any]
        selected_spec: Dict[str, Any]
        if any(item[0] is not None for item in parsed_candidates):
            selected_spec_raw, selected_spec = cls._rank_selected_spec(parsed_candidates)
        elif code_analysis["summary"]["route_count"] > 0:"""

new_logic = """        valid_candidates = [item for item in parsed_candidates if item[0] is not None and item[1].get("total_operations", 0) > 0]
        
        # If we already have a valid OpenAPI spec, skip the heavy code analysis
        if valid_candidates:
            source_files = {}
            code_analysis = RepoCodeApiExtractor.analyze_repo_sources(source_files)
        else:
            source_files = await cls._fetch_source_files(parsed_repo, ref, tree_entries)
            code_analysis = RepoCodeApiExtractor.analyze_repo_sources(source_files)

        selected_source_kind = "openapi"
        selected_spec_raw: Dict[str, Any]
        selected_spec: Dict[str, Any]
        
        if valid_candidates:
            selected_spec_raw, selected_spec = cls._rank_selected_spec(valid_candidates)
        elif any(item[0] is not None for item in parsed_candidates) and code_analysis["summary"]["route_count"] == 0:
            # Fallback to an empty spec if we found files but no code routes
            selected_spec_raw, selected_spec = cls._rank_selected_spec(parsed_candidates)
        elif code_analysis["summary"]["route_count"] > 0:"""

code = code.replace(old_logic, new_logic)

with open("backend/app/services/github_repo_analyzer.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Applied fix to github_repo_analyzer.py")
