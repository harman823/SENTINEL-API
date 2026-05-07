with open("backend/app/main.py", "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("inspection = GitHubRepoAnalyzer.inspect_repo(request.url, selected_path=request.selected_path)", "inspection = await GitHubRepoAnalyzer.inspect_repo(request.url, selected_path=request.selected_path)")

with open("backend/app/main.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Patched main.py")
