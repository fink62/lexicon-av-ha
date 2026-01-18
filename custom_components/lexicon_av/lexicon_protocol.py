"""Lexicon RS232/IP Protocol implementation."""
import asyncio
import logging
from typing import Optional

from .const import (
    PROTOCOL_START,
    PROTOCOL_END,
    PROTOCOL_ZONE1,
    PROTOCOL_CMD_SIMULATE_RC5,
    PROTOCOL_DATA_LENGTH,
    PROTOCOL_ANSWER_OK,
    RC5_SYSTEM,
    RC5_POWER_TOGGLE,
    RC5_POWER_ON,
    RC5_POWER_OFF,
    RC5_VOLUME_UP,
    RC5_VOLUME_DOWN,
    RC5_MUTE_TOGGLE,
    RC5_MUTE_ON,
    RC5_MUTE_OFF,
)

_LOGGER = logging.getLogger(__name__)


class LexiconProtocol:
    """Implements the Lexicon RS232/IP protocol."""

    def __init__(self, host: str, port: int, timeout: int = 3):
        """Initialize the protocol handler."""
        self._host = host
        self._port = port
        self._timeout = timeout
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to the Lexicon receiver."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout
            )
            self._connected = True
            _LOGGER.info("Connected to Lexicon at %s:%s", self._host, self._port)
            return True
        except (asyncio.TimeoutError, OSError) as err:
            _LOGGER.error("Failed to connect to Lexicon: %s", err)
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from the receiver."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False
        self._reader = None
        self._writer = None
        _LOGGER.info("Disconnected from Lexicon")

    def _build_command(self, rc5_command: int) -> bytes:
        """Build an RS232 command frame for RC5 IR simulation."""
        return bytes([
            PROTOCOL_START,
            PROTOCOL_ZONE1,
            PROTOCOL_CMD_SIMULATE_RC5,
            PROTOCOL_DATA_LENGTH,
            RC5_SYSTEM,
            rc5_command,
            PROTOCOL_END
        ])

    async def _send_command(self, command: bytes) -> bool:
        """Send a command and wait for response with auto-reconnect."""
        # Try to reconnect if not connected
        if not self._connected or not self._writer or not self._reader:
            _LOGGER.debug("Not connected, attempting to reconnect...")
            if not await self.connect():
                return False

        try:
            # Send command
            self._writer.write(command)
            await self._writer.drain()
            _LOGGER.debug("Sent command: %s", command.hex())

            # Wait for response (Lexicon typically responds quickly)
            response = await asyncio.wait_for(
                self._reader.read(1024),
                timeout=self._timeout
            )
            _LOGGER.debug("Received response: %s", response.hex())

            # Check response (Answer Code should be 0x00 for success)
            if len(response) >= 6 and response[3] == PROTOCOL_ANSWER_OK:
                _LOGGER.debug("Command successful")
                return True
            else:
                _LOGGER.warning("Unexpected response: %s", response.hex())
                # Don't disconnect on unexpected response, might be valid
                return False

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for response - will reconnect on next command")
            # Mark as disconnected but don't close yet (might be temporary)
            self._connected = False
            return False
            
        except (OSError, ConnectionError, BrokenPipeError) as err:
            _LOGGER.error("Communication error: %s - reconnecting", err)
            self._connected = False
            # Try to close cleanly
            try:
                if self._writer:
                    self._writer.close()
                    await self._writer.wait_closed()
            except Exception:
                pass
            self._reader = None
            self._writer = None
            
            # Try immediate reconnect and retry command
            _LOGGER.info("Attempting immediate reconnect...")
            if await self.connect():
                _LOGGER.info("Reconnected successfully, retrying command...")
                try:
                    self._writer.write(command)
                    await self._writer.drain()
                    response = await asyncio.wait_for(
                        self._reader.read(1024),
                        timeout=self._timeout
                    )
                    if len(response) >= 6 and response[3] == PROTOCOL_ANSWER_OK:
                        _LOGGER.info("Command successful after reconnect")
                        return True
                except Exception as retry_err:
                    _LOGGER.error("Retry failed: %s", retry_err)
                    
            return False

    async def power_on(self) -> bool:
        """Turn on the receiver (using power toggle)."""
        # Note: Lexicon uses power toggle, not discrete on/off
        # We send toggle which works reliably
        command = self._build_command(RC5_POWER_TOGGLE)
        return await self._send_command(command)

    async def power_off(self) -> bool:
        """Turn off the receiver (using power toggle)."""
        # Note: Lexicon uses power toggle, not discrete on/off
        # We send toggle which works reliably  
        command = self._build_command(RC5_POWER_TOGGLE)
        return await self._send_command(command)

    async def select_input(self, input_code: int) -> bool:
        """Select an input source."""
        command = self._build_command(input_code)
        return await self._send_command(command)

    async def volume_up(self) -> bool:
        """Increase volume."""
        command = self._build_command(RC5_VOLUME_UP)
        return await self._send_command(command)

    async def volume_down(self) -> bool:
        """Decrease volume."""
        command = self._build_command(RC5_VOLUME_DOWN)
        return await self._send_command(command)

    async def mute_toggle(self) -> bool:
        """Toggle mute."""
        command = self._build_command(RC5_MUTE_TOGGLE)
        return await self._send_command(command)

    async def mute_on(self) -> bool:
        """Mute on."""
        command = self._build_command(RC5_MUTE_ON)
        return await self._send_command(command)

    async def mute_off(self) -> bool:
        """Mute off."""
        command = self._build_command(RC5_MUTE_OFF)
        return await self._send_command(command)

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected
