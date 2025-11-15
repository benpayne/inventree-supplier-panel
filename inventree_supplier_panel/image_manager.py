"""
Image Manager for Supplier Panel Plugin

Copied and adapted from Digikey-Inventree-Integration/inventree_digikey/ImageManager.py
This handles downloading images from supplier APIs with proper URL encoding and caching.
"""

import os
import random
import string
import http.client
from urllib.parse import urlparse, quote
from pathlib import Path


class ImageManager:
    """
    Manages downloading and caching of part images from supplier websites.
    
    Key features:
    - URL encoding with quote(url, safe=':/) to handle special characters
    - Uses http.client for more control over connections (not requests)
    - Stream download in 1024-byte chunks for large images
    - Cache-based approach: create temp cache dir, download, then clean up
    - Random filename generation to prevent conflicts
    - Handles both HTTP and HTTPS protocols
    - Returns None on failure instead of crashing
    """

    cache_path: Path = Path(__file__).resolve().parent / "cache"

    @classmethod
    def get_image(cls, url: str) -> str:
        """
        Gets an image given a URL.
        
        Args:
            url: The image URL from supplier API
            
        Returns:
            filepath: Path to downloaded image file, or None if failed
        """
        if not cls.cache_active():
            print("[ImageManager] Cache not active, creating...")
            cls._create_cache()

        path = cls._download_image(url)
        return path

    @classmethod
    def cache_active(cls):
        """Check if cache directory exists."""
        exists = os.path.exists(cls.cache_path)
        print(f"[ImageManager] Cache exists: {exists}")
        return exists

    @classmethod
    def _create_cache(cls):
        """Create cache directory."""
        try:
            print(f"[ImageManager] Making cache at {cls.cache_path}")
            os.mkdir(cls.cache_path)
        except Exception as e:
            print(f"[ImageManager] Error making cache: {e}")

    @classmethod
    def clean_cache(cls):
        """Clean all files from cache directory."""
        if cls.cache_active():
            for f in Path(cls.cache_path).glob("*"):
                try:
                    f.unlink()
                    print(f"[ImageManager] Deleted cache file: {f.name}")
                except Exception as e:
                    print(f"[ImageManager] Error deleting {f.name}: {e}")

    @staticmethod
    def _filename_generator(size=6) -> str:
        """Generate random filename for cached image."""
        return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(size)) + ".jpg"

    @classmethod
    def _download_image(cls, url: str) -> str:
        """
        Download image from URL using http.client for proper handling.
        
        This method handles:
        - URL encoding with special characters
        - Both HTTP and HTTPS
        - Streaming download in chunks
        - Error handling without crashes
        
        Args:
            url: Image URL from supplier
            
        Returns:
            filepath: Path to downloaded file, or None if failed
        """
        print(f"[ImageManager] Downloading image from: {url}")

        # Encode URL properly - this is critical for URLs with special characters
        escaped_url = quote(url, safe=':/')
        parsed_url = urlparse(escaped_url)

        # Extract protocol, server host, and path
        protocol = parsed_url.scheme
        server_host = parsed_url.netloc
        path = parsed_url.path

        # Create an HTTP connection to the server based on the protocol
        try:
            if protocol == 'http':
                conn = http.client.HTTPConnection(server_host)
            elif protocol == 'https':
                conn = http.client.HTTPSConnection(server_host)
            else:
                print(f"[ImageManager] Unsupported protocol: {protocol}")
                return None

            # Send an HTTP GET request
            conn.request('GET', path)

            # Get the response
            response = conn.getresponse()

            if response.status != 200:
                print(f"[ImageManager] ERROR: HTTP status {response.status}")
                return None

            # Generate random filename
            filename = cls._filename_generator()
            filepath = cls.cache_path / filename

            # Download image in chunks
            with open(filepath, 'wb') as handler:
                while True:
                    chunk = response.read(1024)
                    if not chunk:
                        break
                    handler.write(chunk)

            print(f"[ImageManager] Image downloaded successfully: {filepath}")
            return str(filepath)

        except Exception as e:
            print(f"[ImageManager] Error downloading image: {e}")
            return None

