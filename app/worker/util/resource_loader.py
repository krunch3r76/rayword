# ./worker/util/resource_loader.py

import os
import requests
import logging
import zipfile
import uuid
import tempfile
import time
from pathlib import Path


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class URLContentFetcher:
    """
    A class to fetch content from a URL and save it to a temporary file, supporting download resumption.

    This class handles HTTP GET requests to download content, especially larger files like ZIPs,
    and supports resuming interrupted downloads. It also handles various HTTP errors and timeouts.

    Attributes:
        url (str): URL of the file to be downloaded.
        temp_zip_path (str): Path to the temporary file where the content is saved.
        max_retries (int): Maximum number of retry attempts for the download.
        timeout_duration (int): Timeout duration in seconds for the HTTP request.
        timeout_error (bool): Flag indicating if a timeout error occurred during the download.

    Notes:
        functor called by load_resource
    """

    def __init__(self, url, temp_zip_path, max_retries=3, timeout_duration=60):
        """
        Initializes the URLContentFetcher with the specified URL, path for the temporary file,
        maximum retries, and timeout duration.
        """
        self.url = url
        self.temp_zip_path = temp_zip_path
        self.max_retries = max_retries
        self.timeout_duration = timeout_duration
        self.timeout_error = False

    def __call__(self):
        """
        Executes the content fetching process. This method attempts to download the content from the URL,
        retrying up to the maximum number of retries in case of failures or timeouts.

        Returns:
            bool: False if the download is successful before exhausting retries, True if all retries are exhausted.
        """
        for attempt in range(self.max_retries):
            self.timeout_error = False
            headers, file_size = self._check_existing_download()

            try:
                with requests.get(
                    self.url,
                    headers=headers,
                    stream=True,
                    timeout=self.timeout_duration,
                ) as response:
                    response.raise_for_status()
                    if self._handle_response(response, file_size, attempt):
                        continue
                    return False
            except requests.exceptions.ReadTimeout:
                self._log_timeout(attempt, "Read")
                self.timeout_error = True
            except requests.exceptions.ConnectTimeout:
                self._log_timeout(attempt, "Connection")
                self.timeout_error = True
            except requests.exceptions.HTTPError as e:
                if self._handle_http_error(e):
                    return False
            except requests.exceptions.RequestException as e:
                logger.debug(f"Unexpected error on {self.url}: {e}")
                self.timeout_error = True

        return True  # Timeout error by default if all retries exhausted

    def _check_existing_download(self):
        """
        Checks if the download already exists and determines the size of the already downloaded content.

        Returns:
            tuple: A tuple containing the headers to be used for HTTP request (for resuming download)
                   and the size of the already downloaded content.
        """
        if os.path.exists(self.temp_zip_path):
            file_size = os.path.getsize(self.temp_zip_path)
            return {"Range": f"bytes={file_size}-"}, file_size
        return {}, 0

    def _handle_response(self, response, file_size, attempt):
        """
        Handles the HTTP response for the download request.

        Args:
            response (requests.Response): The HTTP response object.
            file_size (int): Size of the file already downloaded.
            attempt (int): Current attempt number of the download.

        Returns:
            bool: True if the download needs to be retried, False otherwise.
        """
        total_size = None
        if response.status_code == 206 or "content-range" in response.headers:
            logger.debug("content-range seen")
            content_range = response.headers.get("content-range")
            total_size = int(content_range.split("/")[-1]) if content_range else None

            if total_size is not None and file_size >= total_size:
                return False  # Download already complete

        with open(self.temp_zip_path, "ab") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        if total_size and os.path.getsize(self.temp_zip_path) < total_size:
            logger.debug(
                f"Incomplete transfer on {self.url}, attempt {attempt + 1} of {self.max_retries}"
            )
            return True  # Continue to next retry for incomplete transfer

        return False  # Download successful, no timeout error

    def _log_timeout(self, attempt, timeout_type):
        """
        Logs a timeout error.

        Args:
            attempt (int): Current attempt number of the download.
            timeout_type (str): Type of the timeout ('Read' or 'Connection').
        """
        logger.debug(
            f"{timeout_type} timeout on {self.url}, attempt {attempt + 1} of {self.max_retries}"
        )

    def _handle_http_error(self, e):
        """
        Handles HTTP errors encountered during the download.

        Args:
            e (requests.exceptions.HTTPError): The HTTP error encountered.

        Returns:
            bool: True if the error is a 404 (Not Found), indicating no further retries; False otherwise.
        """
        if e.response.status_code == 404:
            logger.debug(f"URL not found (404) on {self.url}")
            try:
                os.remove(self.temp_zip_path)
            except FileNotFoundError:
                pass
            return True
        else:
            logger.debug(f"HTTP Error on {self.url}: {e}")
            return False


def process_zip_file(temp_zip_path):
    """
    Processes a ZIP file located at the given temporary path and extracts its first file's contents.

    This function opens a ZIP file, reads the contents of the first file in the ZIP archive,
    and decodes it using the 'iso-8859-1' encoding. It is designed to work with ZIP files containing
    a single file. If the ZIP file is corrupted or an error occurs during processing, it logs the error
    and returns a failure indication.

    Args:
        temp_zip_path (str): The file path to the temporary ZIP file.

    Returns:
        tuple: A tuple containing the content of the first file in the ZIP archive as a decoded string
               and a boolean flag. The flag is False if the file was processed successfully,
               and True if an error occurred (e.g., if the ZIP file is bad or the process fails).

    Notes:
        called by load_resource
    """
    try:
        with zipfile.ZipFile(temp_zip_path, "r") as zip_file:
            if zip_file.namelist():
                file_name = zip_file.namelist()[0]
                with zip_file.open(file_name, "r") as file:
                    return file.read().decode("iso-8859-1"), False
    except zipfile.BadZipFile:
        logger.debug(f"Bad ZIP file from {temp_zip_path}")
    return None, True


def load_resource(url, max_retries=3):
    """
    Load a ZIP file from a URL and decompress its contents. This function supports resuming
    partial downloads and handles both HTTP and local file URLs. It uses a temporary file to store
    the downloaded ZIP content, which is automatically cleaned up on function exit, even in cases of
    errors or program crashes.

    Args:
        url (str): The URL of the ZIP file to be downloaded. Can be an HTTP URL or a local file URL (prefixed with 'file://').
        max_retries (int, optional): The maximum number of retries for the download in case of failures. Defaults to 3.

    Returns:
        tuple: A tuple containing the decompressed file content as the first element, and a boolean flag as the second element
               indicating whether an error occurred (True if an error occurred, False otherwise).
               Returns (None, False) if the file is not found or is a bad ZIP file. Returns (None, True) if other errors occur.
    """
    if url.startswith("file://"):
        local_file_path = Path(url[7:])
        if not local_file_path.exists():
            logger.debug(f"File not found at {local_file_path}")
            return None, False
        try:
            with zipfile.ZipFile(local_file_path, "r") as zip_file:
                if zip_file.namelist():
                    file_name = zip_file.namelist()[0]
                    with zip_file.open(file_name, "r") as file:
                        return file.read().decode("iso-8859-1"), False
        except zipfile.BadZipFile:
            logger.debug(f"Bad ZIP file at {local_file_path}")
            return None, False

    # Get the system-defined temporary directory
    temp_dir = Path(tempfile.gettempdir())
    unique_id = uuid.uuid4()  # Generate a unique ID
    timestamp = int(time.time())  # Get current Unix timestamp
    temp_zip_path = temp_dir / f"temp_partial_download_{unique_id}_{timestamp}.zip"

    # Ensure any existing temporary file is removed
    if temp_zip_path.exists():
        # this would be really something if it happened :-p
        raise Exception("temporary file collision, fatal error!")

    fetcher = URLContentFetcher(url, str(temp_zip_path), max_retries)
    fetcher()
    timeout_error = fetcher.timeout_error

    if not timeout_error and temp_zip_path.exists():
        try:
            file_content, zip_error = process_zip_file(str(temp_zip_path))
            if zip_error:
                raise zipfile.BadZipFile(f"Error processing ZIP file from {url}")
            return file_content, False
        finally:
            # Clean-up temporary file
            if temp_zip_path.exists():
                temp_zip_path.unlink()
    elif not timeout_error:
        logger.debug("Downloaded file not found for processing.")

    return None, timeout_error
