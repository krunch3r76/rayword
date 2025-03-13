# resource.py
# logic concerning urls

from urllib.parse import urlparse, urlunparse
import os


def ResourceFactory(root_path=None):
    class Resource:
        def __init__(self, url):
            self.url = url
            self.parsed_url = urlparse(url)
            if root_path is None:
                self.use_file_scheme = False
            else:
                self.use_file_scheme = True

        def get_url(self):
            if self.use_file_scheme:
                # Join root_path with the netloc and path of the original URL
                new_path = os.path.join(
                    root_path, self.parsed_url.netloc, self.parsed_url.path.lstrip("/")
                )
                # File URLs typically have an empty netloc
                return urlunparse(("file", "", new_path, "", "", ""))
            else:
                return self.url

        def get_path(self):
            return self.parsed_url.path

        def set_file_scheme(self, use_file_scheme):
            self.use_file_scheme = use_file_scheme

        def __str__(self):
            return self.get_url()

    return Resource


def parse_resources_file(file_object):
    # rename to parse_resources_from_file
    """
    Reads lines from an open file object containing URLs and creates a list of Resource objects.

    :param file_object: An open file object with URLs.
    :return: A list of Resource objects.
    """
    # Resource = ResourceFactory("/mnt/guts/guten/harvest")
    Resource = ResourceFactory()
    return [Resource(line.strip()) for line in file_object]


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <file with urls>")

    resources = []
    with open(sys.argv[1]) as f:
        resources = parse_resources_file(f)
    from pprint import pprint

    root = Path("/mnt/guts/guten/harvest/")
    paths = [str(resource) for resource in resources]
    # resolved_paths = [root / Path(path) for path in paths]
    pprint(paths)

# # Usage
# Resource = ResourceFactory("<root_path>")
# resource_instance = Resource("http://aleph.gutenberg.org/1/2/3/7/12373/12373-8.zip")
# print(resource_instance.get_url())  # Returns the original http URL

# resource_instance.set_file_scheme(True)
# print(resource_instance.get_url())  # Returns the file URL

# @dataclass
# class Resource:
#     url: str

#     @property
#     def path(self):
#         return _extract_path(self.url)

#     @property
#     def fileurl(self):
#         fileloc = _extract_path(self.url)
#         return "file://" + fileloc
