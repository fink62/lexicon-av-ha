"""Lexicon RS232/IP Protocol implementation."""
import asyncio
import logging
from typing import Optional

from .const import (
    PROTOCOL_START,
    PROTOCOL_END,
    PROTOCOL_ZONE1,
    PROTOCOL_CMD_SIMULATE_RC5,
    PROTOCOL_CMD_POWER,
    PROTOCOL_CMD_VOLUME,
    PROTOCOL_CMD_MUTE,
    PROTOCOL_CMD_CURRENT_SOURCE,
    PROTOCOL_DATA_LENGTH,
    PROTOCOL_REQUEST,
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
    SOURCE_CODES,
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

    def _build_query_command(self, command_code: int) -> bytes:
        """Build an RS232 command frame for status queries."""
        return bytes([
            PROTOCOL_START,
            PROTOCOL_ZONE1,
            command_code,
            0x01,  # Data length: 1 byte
            PROTOCOL_REQUEST,  # 0xF0 = request current value
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

    async def _send_query(self, command: bytes) -> Optional[bytes]:
        """Send a query command and return the response data."""
        # Try to reconnect if not connected
        if not self._connected or not self._writer or not self._reader:
            _LOGGER.debug("Not connected, attempting to reconnect...")
            if not await self.connect():
                return None

        try:
            # Send command
            self._writer.write(command)
            await self._writer.drain()
            _LOGGER.debug("Sent query: %s", command.hex())

            # Wait for response
            response = await asyncio.wait_for(
                self._reader.read(1024),
                timeout=self._timeout
            )
            _LOGGER.debug("Received query response: %s", response.hex())

            # Check response format: <Start> <Zone> <Cmd> <Answer> <DataLen> <Data...> <End>
            if len(response) >= 6 and response[3] == PROTOCOL_ANSWER_OK:
                data_length = response[4]
                if len(response) >= 5 + data_length + 1:
                    # Extract data bytes (skip Start, Zone, Cmd, Answer, DataLen; stop before End)
                    data = response[5:5+data_length]
                    _LOGGER.debug("Query successful, data: %s", data.hex())
                    return data
                else:
                    _LOGGER.warning("Response too short for data_length=%d", data_length)
                    return None
            else:
                _LOGGER.warning("Query failed or unexpected response: %s", response.hex())
                return None

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for query response")
            self._connected = False
            return None
            
        except (OSError, ConnectionError, BrokenPipeError) as err:
            _LOGGER.error("Communication error during query: %s", err)
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
            return None

    # ==================== Control Commands ====================

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

    async def set_volume(self, volume: int) -> bool:
        """Set absolute volume level (0-99)."""
        if not 0 <= volume <= 99:
            _LOGGER.error("Volume must be between 0 and 99, got %d", volume)
            return False
        
        command = bytes([
            PROTOCOL_START,
            PROTOCOL_ZONE1,
            PROTOCOL_CMD_VOLUME,
            0x01,  # Data length
            volume,  # Volume value 0x00-0x63
            PROTOCOL_END
        ])
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

    # ==================== Status Query Commands ====================

    async def get_power_state(self) -> Optional[bool]:
        """
        Query power state.
        Returns: True = on, False = standby, None = error
        """
        command = self._build_query_command(PROTOCOL_CMD_POWER)
        data = await self._send_query(command)
        
        if data and len(data) >= 1:
            power_state = data[0]
            # 0x00 = standby, 0x01 = powered on
            return power_state == 0x01
        return None

    async def get_volume(self) -> Optional[int]:
        """
        Query current volume level.
        Returns: Volume (0-99), None = error
        """
        command = self._build_query_command(PROTOCOL_CMD_VOLUME)
        data = await self._send_query(command)
        
        if data and len(data) >= 1:
            volume = data[0]
            _LOGGER.debug("Current volume: %d", volume)
            return volume
        return None

    async def get_mute_state(self) -> Optional[bool]:
        """
        Query mute state.
        Returns: True = muted, False = not muted, None = error
        """
        command = self._build_query_command(PROTOCOL_CMD_MUTE)
        data = await self._send_query(command)
        
        if data and len(data) >= 1:
            mute_state = data[0]
            # 0x00 = muted, 0x01 = not muted
            is_muted = (mute_state == 0x00)
            _LOGGER.debug("Mute state: %s (raw: 0x%02X)", is_muted, mute_state)
            return is_muted
        return None

    async def get_current_source(self) -> Optional[str]:
        """
        Query currently selected source.
        Returns: Source name (e.g., "BD", "CD"), None = error
        """
        command = self._build_query_command(PROTOCOL_CMD_CURRENT_SOURCE)
        data = await self._send_query(command)
        
        if data and len(data) >= 1:
            source_code = data[0]
            _LOGGER.debug("Received source code: 0x%02X (decimal: %d)", source_code, source_code)
            source_name = SOURCE_CODES.get(source_code, f"UNKNOWN_0x{source_code:02X}")
            _LOGGER.debug("Mapped to source name: %s", source_name)
            return source_name
        return None

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected
