"""Lexicon RS232/IP Protocol implementation with improved connection handling."""
import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

from .const import (
    PROTOCOL_START,
    PROTOCOL_END,
    PROTOCOL_ZONE1,
    PROTOCOL_CMD_SIMULATE_RC5,
    PROTOCOL_CMD_POWER,
    PROTOCOL_CMD_VOLUME,
    PROTOCOL_CMD_MUTE,
    PROTOCOL_CMD_DIRECT_MODE,
    PROTOCOL_CMD_DECODE_2CH,
    PROTOCOL_CMD_DECODE_MCH,
    PROTOCOL_CMD_CURRENT_SOURCE,
    PROTOCOL_CMD_AUDIO_FORMAT,
    PROTOCOL_CMD_SAMPLE_RATE,
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
    DECODE_MODE_2CH,
    DECODE_MODE_MCH,
    AUDIO_FORMAT,
    SAMPLE_RATE,
)

_LOGGER = logging.getLogger(__name__)


class LexiconProtocol:
    """Implements the Lexicon RS232/IP protocol with robust error handling."""

    def __init__(self, host: str, port: int, timeout: int = 3):
        """Initialize the protocol handler."""
        self._host = host
        self._port = port
        self._timeout = timeout
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._connection_lock = asyncio.Lock()
        
        # Reconnect handling with exponential backoff
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._last_reconnect_attempt: Optional[datetime] = None
        self._min_reconnect_interval = timedelta(seconds=5)

    async def connect(self) -> bool:
        """Connect to the Lexicon receiver with connection state management."""
        async with self._connection_lock:
            # Already connected
            if self._connected and self._writer and self._reader:
                return True
            
            # Check reconnect throttling
            if self._last_reconnect_attempt:
                time_since_last = datetime.now() - self._last_reconnect_attempt
                if time_since_last < self._min_reconnect_interval:
                    _LOGGER.debug(
                        "Reconnect throttled, waiting %.1fs",
                        (self._min_reconnect_interval - time_since_last).total_seconds()
                    )
                    return False
            
            self._last_reconnect_attempt = datetime.now()
            
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=self._timeout
                )
                self._connected = True
                self._reconnect_attempts = 0
                _LOGGER.info("Connected to Lexicon at %s:%s", self._host, self._port)
                return True
                
            except (asyncio.TimeoutError, OSError) as err:
                self._reconnect_attempts += 1
                self._connected = False
                
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    _LOGGER.error(
                        "Failed to connect after %d attempts: %s",
                        self._reconnect_attempts, err
                    )
                else:
                    _LOGGER.warning(
                        "Connection attempt %d/%d failed: %s",
                        self._reconnect_attempts, self._max_reconnect_attempts, err
                    )
                return False

    async def disconnect(self):
        """Disconnect from the receiver."""
        async with self._connection_lock:
            if self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception as err:
                    _LOGGER.debug("Error closing connection: %s", err)
            
            self._connected = False
            self._reader = None
            self._writer = None
            _LOGGER.info("Disconnected from Lexicon")

    async def _read_frame(self) -> Optional[bytes]:
        """
        Read a complete protocol frame with proper parsing.
        
        Frame format: <Start> <Zone> <Cmd> <Answer> <DataLen> <Data...> <End>
        Returns complete frame or None on error.
        """
        if not self._reader:
            return None
        
        try:
            # Read frame header (5 bytes): Start, Zone, Cmd, Answer, DataLen
            header = await asyncio.wait_for(
                self._reader.readexactly(5),
                timeout=self._timeout
            )
            
            if header[0] != PROTOCOL_START:
                _LOGGER.warning("Invalid frame start: 0x%02X", header[0])
                return None
            
            # Extract data length
            data_len = header[4]
            
            # Read data + end byte
            remaining = await asyncio.wait_for(
                self._reader.readexactly(data_len + 1),
                timeout=self._timeout
            )
            
            # Verify end byte
            if remaining[-1] != PROTOCOL_END:
                _LOGGER.warning("Invalid frame end: 0x%02X", remaining[-1])
                return None
            
            # Return complete frame
            frame = header + remaining
            _LOGGER.debug("Read complete frame: %s", frame.hex())
            return frame
            
        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout reading frame")
            return None
        except asyncio.IncompleteReadError as err:
            _LOGGER.debug("Incomplete frame: %s", err)
            return None
        except Exception as err:
            _LOGGER.error("Error reading frame: %s", err)
            return None

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

    async def _ensure_connection(self) -> bool:
        """Ensure connection is established, reconnect if needed."""
        if not self._connected or not self._writer or not self._reader:
            _LOGGER.debug("Connection lost, attempting reconnect...")
            return await self.connect()
        return True

    async def _send_command(self, command: bytes) -> bool:
        """Send a command and wait for response with auto-reconnect."""
        if not await self._ensure_connection():
            return False

        try:
            # Send command
            self._writer.write(command)
            await self._writer.drain()
            _LOGGER.debug("Sent command: %s", command.hex())

            # Read response frame
            response = await self._read_frame()
            if not response:
                _LOGGER.warning("No response received")
                self._connected = False
                return False

            # Check response (Answer Code should be 0x00 for success)
            if len(response) >= 6 and response[3] == PROTOCOL_ANSWER_OK:
                _LOGGER.debug("Command successful")
                return True
            else:
                _LOGGER.warning("Unexpected response: %s", response.hex())
                return False

        except (OSError, ConnectionError, BrokenPipeError) as err:
            _LOGGER.error("Communication error: %s", err)
            self._connected = False
            await self._cleanup_connection()
            
            # Single retry attempt
            _LOGGER.info("Attempting immediate reconnect...")
            if await self.connect():
                try:
                    self._writer.write(command)
                    await self._writer.drain()
                    response = await self._read_frame()
                    if response and len(response) >= 6 and response[3] == PROTOCOL_ANSWER_OK:
                        _LOGGER.info("Command successful after reconnect")
                        return True
                except Exception as retry_err:
                    _LOGGER.error("Retry failed: %s", retry_err)
            
            return False

    async def _send_query(self, command: bytes) -> Optional[bytes]:
        """Send a query command and return the response data."""
        if not await self._ensure_connection():
            return None

        try:
            # Send command
            self._writer.write(command)
            await self._writer.drain()
            _LOGGER.debug("Sent query: %s", command.hex())

            # Read response frame
            response = await self._read_frame()
            if not response:
                _LOGGER.warning("No query response received")
                self._connected = False
                return None

            # Parse response: <Start> <Zone> <Cmd> <Answer> <DataLen> <Data...> <End>
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

        except (OSError, ConnectionError, BrokenPipeError) as err:
            _LOGGER.error("Communication error during query: %s", err)
            self._connected = False
            await self._cleanup_connection()
            return None

    async def _cleanup_connection(self):
        """Clean up broken connection without holding the lock."""
        try:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
        except Exception:
            pass
        self._reader = None
        self._writer = None

    # ==================== Control Commands ====================

    async def power_on(self) -> bool:
        """Turn on the receiver (using power toggle) and wait for readiness."""
        command = self._build_command(RC5_POWER_TOGGLE)
        if not await self._send_command(command):
            return False
        
        # Wait a moment for receiver to start powering on
        await asyncio.sleep(2)
        
        # Verify receiver is actually on (up to 5 attempts over 5 seconds)
        for attempt in range(5):
            power_state = await self.get_power_state()
            if power_state is True:
                _LOGGER.info("Receiver powered on and verified ready")
                return True
            _LOGGER.debug("Waiting for receiver to power on (attempt %d/5)", attempt + 1)
            await asyncio.sleep(1)
        
        # Assume success even if we can't verify (receiver might not support query while booting)
        _LOGGER.warning("Could not verify power on state, assuming success")
        return True

    async def power_off(self) -> bool:
        """Turn off the receiver (using power toggle)."""
        command = self._build_command(RC5_POWER_TOGGLE)
        return await self._send_command(command)

    async def wait_until_ready(self, timeout: int = 10) -> bool:
        """
        Wait until receiver is ready to accept commands.
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            True if receiver is ready, False if timeout
        """
        _LOGGER.debug("Waiting for receiver to be ready (timeout: %ds)", timeout)
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # Try to query volume - if successful, receiver is ready
            volume = await self.get_volume()
            if volume is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                _LOGGER.info("Receiver ready after %.1f seconds", elapsed)
                return True
            
            await asyncio.sleep(0.5)
        
        _LOGGER.warning("Receiver not ready after %d seconds", timeout)
        return False

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

    async def get_direct_mode(self) -> Optional[bool]:
        """
        Query direct mode status.
        Returns: True = on, False = off, None = error
        """
        command = self._build_query_command(PROTOCOL_CMD_DIRECT_MODE)
        data = await self._send_query(command)
        
        if data and len(data) >= 1:
            direct_mode = data[0]
            # 0x00 = off, 0x01 = on
            is_direct = (direct_mode == 0x01)
            _LOGGER.debug("Direct mode: %s (raw: 0x%02X)", is_direct, direct_mode)
            return is_direct
        return None

    async def get_decode_mode(self) -> Optional[str]:
        """
        Query decode mode (tries 2ch first, then MCH).
        Returns: Decode mode name (e.g., "Stereo", "Dolby Surround"), None = error
        """
        # Try 2-channel decode mode first
        command = self._build_query_command(PROTOCOL_CMD_DECODE_2CH)
        data = await self._send_query(command)
        
        if data and len(data) >= 1:
            mode_code = data[0]
            mode_name = DECODE_MODE_2CH.get(mode_code)
            if mode_name:
                _LOGGER.debug("Decode mode (2ch): %s (code: 0x%02X)", mode_name, mode_code)
                return mode_name
        
        # Try multi-channel decode mode
        command = self._build_query_command(PROTOCOL_CMD_DECODE_MCH)
        data = await self._send_query(command)
        
        if data and len(data) >= 1:
            mode_code = data[0]
            mode_name = DECODE_MODE_MCH.get(mode_code, f"UNKNOWN_0x{mode_code:02X}")
            _LOGGER.debug("Decode mode (MCH): %s (code: 0x%02X)", mode_name, mode_code)
            return mode_name
        
        return None

    async def get_audio_format(self) -> Optional[str]:
        """
        Query incoming audio format.
        Returns: Format name (e.g., "Dolby Atmos", "DTS:X"), None = error
        """
        command = self._build_query_command(PROTOCOL_CMD_AUDIO_FORMAT)
        data = await self._send_query(command)
        
        if data and len(data) >= 2:
            format_code = data[0]
            format_name = AUDIO_FORMAT.get(format_code, f"UNKNOWN_0x{format_code:02X}")
            _LOGGER.debug("Audio format: %s (code: 0x%02X)", format_name, format_code)
            return format_name
        return None

    async def get_sample_rate(self) -> Optional[str]:
        """
        Query incoming audio sample rate.
        Returns: Sample rate (e.g., "48 kHz", "96 kHz"), None = error
        """
        command = self._build_query_command(PROTOCOL_CMD_SAMPLE_RATE)
        data = await self._send_query(command)
        
        if data and len(data) >= 1:
            rate_code = data[0]
            rate_name = SAMPLE_RATE.get(rate_code, f"UNKNOWN_0x{rate_code:02X}")
            _LOGGER.debug("Sample rate: %s (code: 0x%02X)", rate_name, rate_code)
            return rate_name
        return None

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected

    @property
    def reconnect_attempts(self) -> int:
        """Return number of reconnect attempts."""
        return self._reconnect_attempts
