import asyncio
from backend.app.services.github_repo_analyzer import GitHubRepoAnalyzer

async def test():
    try:
        import time
        t0 = time.time()
        res = await GitHubRepoAnalyzer.inspect_repo("https://github.com/harman823/SENTINEL-API")
        print("SUCCESS! Took", time.time()-t0, "seconds")
    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
