#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from main import list_nd_fabrics

async def main():
    result = await list_nd_fabrics()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
