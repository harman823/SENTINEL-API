import time
import httpx
from backend.app.services.github_repo_analyzer import GitHubRepoAnalyzer

def test():
    print("Fetching repo...")
    url = "https://github.com/harman823/SENTINEL-API"
    
    parsed_repo = GitHubRepoAnalyzer._parse_repo_url(url)
    
    t0 = time.time()
    repo_meta = GitHubRepoAnalyzer._fetch_json(f"https://api.github.com/repos/{parsed_repo.owner}/{parsed_repo.repo}")
    print(f"fetch repo_meta took {time.time()-t0:.2f}s")
    
    default_branch = repo_meta.get("default_branch", "main")
    ref = parsed_repo.ref or default_branch

    t0 = time.time()
    tree = GitHubRepoAnalyzer._fetch_json(
        f"https://api.github.com/repos/{parsed_repo.owner}/{parsed_repo.repo}/git/trees/{ref}?recursive=1"
    )
    print(f"fetch tree took {time.time()-t0:.2f}s")
    
    tree_entries = tree.get("tree", [])
    candidates = GitHubRepoAnalyzer._discover_spec_candidates(tree_entries, None)
    
    print(f"found {len(candidates)} candidates")
    
    for candidate in candidates:
        t0 = time.time()
        print(f"Parsing candidate {candidate['path']}...")
        spec_raw, candidate_meta = GitHubRepoAnalyzer._parse_spec_candidate(parsed_repo, ref, candidate["path"])
        print(f"Parsed in {time.time()-t0:.2f}s")

if __name__ == "__main__":
    test()
