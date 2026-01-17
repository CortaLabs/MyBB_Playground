"""CSS cache refresh for disk-sync.

Handles HTTP requests to MyBB's cachecss.php endpoint for stylesheet cache regeneration.
"""

import httpx
from typing import Any


class CacheRefresher:
    """Triggers MyBB stylesheet cache regeneration via HTTP POST."""

    def __init__(self, mybb_url: str, token: str = ""):
        """Initialize cache refresher.

        Args:
            mybb_url: Base URL of MyBB installation (e.g., "http://localhost:8080")
            token: Optional authentication token for cachecss.php
        """
        self.mybb_url = mybb_url.rstrip('/')
        self.endpoint = f"{self.mybb_url}/cachecss.php"
        self.token = token

    async def refresh_stylesheet(self, theme_name: str, stylesheet_name: str) -> bool:
        """Trigger cache refresh for a specific stylesheet.

        Sends HTTP POST to cachecss.php with theme_name, stylesheet, and token.

        Args:
            theme_name: Theme name (e.g., "Default")
            stylesheet_name: Stylesheet name (e.g., "global.css")

        Returns:
            True if cache refresh succeeded, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.endpoint,
                    data={
                        'theme_name': theme_name,
                        'stylesheet': stylesheet_name,
                        'token': self.token
                    },
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                )

                # Check if request succeeded
                if response.status_code != 200:
                    return False

                # Parse JSON response
                try:
                    result = response.json()
                    return result.get('success', False)
                except Exception:
                    # Non-JSON response or malformed JSON
                    return False

        except httpx.TimeoutException:
            # Timeout - log but don't crash
            return False
        except httpx.RequestError:
            # Network error - log but don't crash
            return False
        except Exception:
            # Any other error - log but don't crash
            return False
