import requests

# URL to test
url = "https://ir.vnulib.edu.vn/flowpaper/services/view.php?doc=167642949174089127214865901467877578492&format=jpg&page=102&subfolder=16/76/42/"

try:
    # Send GET request
    response = requests.get(url, verify=False)  # Bypass SSL verification (not recommended for production)
    response.raise_for_status()  # Raise an error for HTTP status codes 4xx/5xx

    # Check if the response body contains the error text
    if "Error converting document" in response.text:
        print("Error found in the response!")
        print(response.text)
    else:
        print("No error found in the response.")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
