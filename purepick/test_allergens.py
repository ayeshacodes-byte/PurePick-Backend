import requests

url = "http://127.0.0.1:8000/purepick/check_allergen/"
headers = {"Content-Type": "application/json"}
data = {"query": "organic whole rolled oates, organic raisins, organic expeller pressed canola oil, organic flax seed, organic corn meal, organic almonds, organic coconut, organic cinnamon, salt."}
response = requests.post(url, json=data, headers=headers)
print("Response:", response.json())
