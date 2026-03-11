import httpx
import asyncio
import os
import time
import json
from   dotenv import load_dotenv
import logging

# load .env file for credentials and IP address
load_dotenv()

# set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NDmcp")


class NdAuthManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NdAuthManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self):
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            self.nd_host = os.getenv("ND_HOST")
            self.nd_username = os.getenv("ND_USERNAME")
            self.nd_password = os.getenv("ND_PASSWORD")
            self.nd_domain = os.getenv("ND_DOMAIN", "default")
            self.token_endpoint = f"https://{self.nd_host}/login"
            self._access_token = None
            self._initialized = True
            self._client = httpx.AsyncClient(verify=False)

    async def get_access_token(self) -> str:
        await self.initialize()
        if self._access_token:
            return self._access_token

        login_payload = {
            "userName": self.nd_username,
            "userPasswd": self.nd_password,
            "domain": self.nd_domain,
            "uiLogin": False
        }
        try:
            response = await self._client.post(
                self.token_endpoint,
                json=login_payload,
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
            token = data.get("token")
            if not token:
                raise ValueError("ND session token not found in login response.")
            self._access_token = token
            return self._access_token
        except Exception as e:
            logger.error(f"ND authentication failed: {e}")
            raise

nd_auth_manager = NdAuthManager()
