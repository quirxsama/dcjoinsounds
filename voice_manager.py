"""
Voice Manager - Discord bot voice connection management
Thread-safe voice connection handling with automatic reconnection
"""

import asyncio
import logging
from collections import defaultdict
from typing import Optional, Dict, Any

import discord
import aiohttp

log = logging.getLogger(__name__)

class VoiceManager:
    """Manages voice connections with thread-safe operations and automatic reconnection"""

    def __init__(self, bot: discord.Client):
        self.bot = bot
        # guild_id -> asyncio.Lock (only one connect/reconnect attempt per guild)
        self._locks = defaultdict(asyncio.Lock)
        # guild_id -> asyncio.Task of current connect attempt
        self._connect_tasks: Dict[int, asyncio.Task] = {}
        # guild_id -> voice client reference
        self._voice_clients: Dict[int, discord.VoiceClient] = {}

    async def connect_with_backoff(
        self,
        channel: discord.VoiceChannel,
        *,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        timeout: float = 20.0
    ) -> discord.VoiceClient:
        """
        Safely connect to voice channel with exponential backoff.
        Prevents parallel connection attempts for the same guild.
        """
        guild_id = channel.guild.id
        lock = self._locks[guild_id]

        async with lock:
            # Check if already connected
            existing_vc = self._voice_clients.get(guild_id)
            if existing_vc and getattr(existing_vc, "is_connected", lambda: True)():
                log.info("Already connected to voice channel in guild %s", guild_id)
                return existing_vc

            # Prevent parallel calls: wait for existing task
            if guild_id in self._connect_tasks and not self._connect_tasks[guild_id].done():
                log.info("Another connection attempt in progress for guild %s, waiting...", guild_id)
                return await self._connect_tasks[guild_id]

            # Create new connection task
            task = asyncio.create_task(
                self._attempt_connect(channel, max_attempts=max_attempts, base_delay=base_delay, timeout=timeout)
            )
            self._connect_tasks[guild_id] = task

            try:
                vc = await task
                self._voice_clients[guild_id] = vc
                return vc
            finally:
                self._connect_tasks.pop(guild_id, None)

    async def _attempt_connect(
        self,
        channel: discord.VoiceChannel,
        *,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        timeout: float = 20.0
    ) -> discord.VoiceClient:
        """Internal connection attempt with retry logic"""
        attempt = 0
        last_error = None

        while attempt < max_attempts:
            attempt += 1
            try:
                log.info("Starting voice handshake... (attempt %d/%d) guild=%s",
                        attempt, max_attempts, channel.guild.id)

                # Connect with timeout
                coro = channel.connect(timeout=timeout, reconnect=True)
                vc = await asyncio.wait_for(coro, timeout=timeout + 5)

                log.info("Voice connection completed: %s", vc)
                return vc

            except asyncio.TimeoutError as e:
                log.warning("Voice connect timeout (attempt %d): %s", attempt, e)
                last_error = e
            except (discord.errors.ConnectionClosed, aiohttp.ClientConnectionError,
                    aiohttp.ClientConnectorError) as e:
                log.warning("Voice transport error (attempt %d): %s", attempt, e)
                last_error = e
            except Exception as e:
                log.exception("Unexpected error during voice connect (attempt %d): %s", attempt, e)
                last_error = e

            # Exponential backoff
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                log.info("Retrying in %s seconds...", delay)
                await asyncio.sleep(delay)

        # All attempts failed
        raise RuntimeError(f"Voice connect failed after {max_attempts} attempts (guild={channel.guild.id})") from last_error

    async def safe_disconnect(self, guild: discord.Guild) -> None:
        """Safely disconnect from voice channel"""
        guild_id = guild.id
        vc = self._voice_clients.get(guild_id)

        if vc:
            try:
                await vc.disconnect(force=True)
                log.info("Disconnected from voice channel in guild %s", guild_id)
            except Exception:
                log.exception("Error during disconnect for guild %s", guild_id)
            finally:
                self._voice_clients.pop(guild_id, None)

    async def cleanup_all(self) -> None:
        """Cleanup all voice connections"""
        log.info("Cleaning up all voice connections...")

        tasks = []
        for guild_id, vc in self._voice_clients.items():
            if vc and vc.is_connected():
                tasks.append(self.safe_disconnect(vc.guild))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._voice_clients.clear()
        self._connect_tasks.clear()
        log.info("Voice cleanup completed")

    def get_voice_client(self, guild_id: int) -> Optional[discord.VoiceClient]:
        """Get voice client for guild"""
        return self._voice_clients.get(guild_id)

    def is_connected(self, guild_id: int) -> bool:
        """Check if connected to voice in guild"""
        vc = self._voice_clients.get(guild_id)
        return vc is not None and getattr(vc, "is_connected", lambda: False)()