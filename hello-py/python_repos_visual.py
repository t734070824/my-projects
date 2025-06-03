import requests
import plotly.express as px



url = "https://api.github.com/search/repositories"
url += "?q=language:python+sort:stars+stars:>10000"

headers = {"Accept": "application/vnd.github.v3+json"}
r = requests.get(url, headers=headers)

print(f"Status code: {r.status_code}")


response_dict = r.json()

print(f"Complete result ：{not response_dict['incomplete_results']}")

repo_dicts = response_dict["items"]

repo_names, stars = [], []

for repo_dict in repo_dicts:
    stars.append(repo_dict["stargazers_count"])
    repo_names.append(repo_dict["name"])

title  = "Most-Starred Python Projects on GitHub"
labels = {
    "x": "Repository",
    "y": "Stars",
}
fig = px.bar(x=repo_names, y=stars, title=title, labels=labels)
fig.update_layout(
    xaxis_tickangle=-45,
    xaxis_title="Repository",
    yaxis_title="Stars",
    title_x=0.5,
    title_y=0.95,
    width=800,
    height=600,
)
fig.show()