import requests

url = "https://api.github.com/search/repositories"
url += "?q=language:python+sort:stars"

r = requests.get(url)

print(f"Status code: {r.status_code}")

response_dict = r.json()

print(f"Total repositories: {response_dict['total_count']}")
print(response_dict.keys())
