import asyncio
from backend.app.services.github_repo_analyzer import GitHubRepoAnalyzer

def test():
    try:
        res = GitHubRepoAnalyzer.inspect_repo("https://github.com/harman823/SENTINEL-API")
        print("SUCCESS!")
    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
