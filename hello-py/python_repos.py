import requests

url = "https://api.github.com/search/repositories"
url += "?q=language:python+sort:stars"

headers = {"Accept": "application/vnd.github.v3+json"}
r = requests.get(url, headers=headers, verify=False)  # Disable SSL verification

print(f"Status code: {r.status_code}")

response_dict = r.json()

print(f"Total repositories: {response_dict['total_count']}")
print(response_dict.keys())
