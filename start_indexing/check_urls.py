# check_urls.py

import requests
from urllib.parse import urljoin


def check_urls(base_url, paths):
    """
    Check if the given URL paths are reachable.

    Parameters:
    - base_url (str): The base URL to which the paths will be appended.
    - paths (list of str): List of URL paths to check.

    Returns:
    - dict: A dictionary where the keys are the URL paths and the values are booleans indicating reachability.
    Authored by ChatGPT
    """
    results = {}
    for path in paths:
        full_url = urljoin(base_url, path)
        try:
            response = requests.head(full_url, allow_redirects=True)
            if response.status_code != 200:
                response = requests.get(full_url, allow_redirects=True)
            results[path] = response.status_code == 200
        except requests.RequestException as e:
            # Print or log the exception if needed
            # print(f"Error checking URL {full_url}: {e}")
            results[path] = False
    return results


# Example usage:
# base_url = "http://example.com"
# paths = ["/", "/nonexistentpath", "/anotherpath"]

# reachable_urls = check_urls(base_url, paths)
# for path, is_reachable in reachable_urls.items():
#     status = "reachable" if is_reachable else "not reachable"
#     print(f"Path '{path}' is {status}.")
