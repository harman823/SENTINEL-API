import asyncio
import time
from backend.app.services.github_repo_analyzer import GitHubRepoAnalyzer

async def test():
    try:
        t0 = time.time()
        print("Starting...")
        
        parsed_repo = GitHubRepoAnalyzer._parse_repo_url("https://github.com/harman823/SENTINEL-API")
        print("Fetching repo meta...")
        repo_meta = await GitHubRepoAnalyzer._fetch_json(f"https://api.github.com/repos/{parsed_repo.owner}/{parsed_repo.repo}")
        print("Meta done in", time.time()-t0)
        
        default_branch = repo_meta.get("default_branch", "main")
        ref = parsed_repo.ref or default_branch
        
        print("Fetching tree...")
        tree = await GitHubRepoAnalyzer._fetch_json(f"https://api.github.com/repos/{parsed_repo.owner}/{parsed_repo.repo}/git/trees/{ref}?recursive=1")
        print("Tree done in", time.time()-t0)
        
        tree_entries = tree.get("tree", [])
        candidates = GitHubRepoAnalyzer._discover_spec_candidates(tree_entries, None)
        print("Candidates:", len(candidates))
        
        async def parse(c):
            t1 = time.time()
            res = await GitHubRepoAnalyzer._parse_spec_candidate(parsed_repo, ref, c["path"])
            print("Parsed", c["path"], "in", time.time()-t1)
            return res
            
        await asyncio.gather(*(parse(c) for c in candidates))
        print("SUCCESS! Total time:", time.time()-t0)
        
    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
