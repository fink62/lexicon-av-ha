#!/usr/bin/env python3
"""
Lexicon Receiver - Advanced Connection & Protocol Behavior Tests
================================================================

PURPOSE: Investigate why the Lexicon app reports "Socket closed by remote peer"
or "Unable to connect" when the HA integration is active.

Previous tests proved:
  - TCP connections can be opened concurrently (ON and OFF)
  - 50ms post-disconnect delay is sufficient for clean reconnect
  - No idle timeout on connections

BUT: Those tests never sent actual RS232/IP protocol commands.
This script tests what happens when real protocol traffic flows
on concurrent connections — the likely root cause of app blocking.

REQUIRES: Receiver must be ON for most tests (queries need responses).

Usage:
    python test_connection_advanced.py <receiver_ip> [port]

Example:
    python test_connection_advanced.py 192.168.20.178
    python test_connection_advanced.py 192.168.20.178 50000
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional, Tuple, List

# ─── Protocol Constants (from const.py) ─────────────────────────────────────

PROTOCOL_START = 0x21
PROTOCOL_END = 0x0D
PROTOCOL_ZONE1 = 0x01
PROTOCOL_REQUEST = 0xF0
PROTOCOL_ANSWER_OK = 0x00

# Query command codes
CMD_POWER = 0x00
CMD_VOLUME = 0x0D
CMD_MUTE = 0x0E
CMD_CURRENT_SOURCE = 0x1D
CMD_AUDIO_FORMAT = 0x43
CMD_SAMPLE_RATE = 0x44
CMD_DECODE_2CH = 0x10
CMD_DECODE_MCH = 0x11
CMD_DIRECT_MODE = 0x0F

QUERY_NAMES = {
    CMD_POWER: "Power",
    CMD_VOLUME: "Volume",
    CMD_MUTE: "Mute",
    CMD_CURRENT_SOURCE: "Source",
    CMD_AUDIO_FORMAT: "AudioFormat",
    CMD_SAMPLE_RATE: "SampleRate",
    CMD_DECODE_2CH: "Decode2ch",
    CMD_DECODE_MCH: "DecodeMCH",
    CMD_DIRECT_MODE: "DirectMode",
}

# RC5 IR Simulate (Command 0x08) — used to trigger state changes
CMD_SIMULATE_RC5 = 0x08
RC5_SYSTEM = 0x10
RC5_VOLUME_UP = 0x10
RC5_VOLUME_DOWN = 0x11

# ─── Logging ─────────────────────────────────────────────────────────────────

results_log: List[str] = []


def log(message: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {message}"
    print(line)
    results_log.append(line)


def log_header(title: str):
    log("")
    log("=" * 70)
    log(title)
    log("=" * 70)


def log_subheader(title: str):
    log("")
    log(f"--- {title} ---")


# ─── Protocol Helpers ────────────────────────────────────────────────────────

def build_query(cmd: int) -> bytes:
    """Build a status query frame."""
    return bytes([PROTOCOL_START, PROTOCOL_ZONE1, cmd, 0x01, PROTOCOL_REQUEST, PROTOCOL_END])


def build_rc5_command(rc5_cmd: int) -> bytes:
    """Build an RC5 IR simulate command frame (Cc=0x08, Dl=0x02)."""
    return bytes([PROTOCOL_START, PROTOCOL_ZONE1, CMD_SIMULATE_RC5, 0x02, RC5_SYSTEM, rc5_cmd, PROTOCOL_END])


async def read_frame(reader: asyncio.StreamReader, timeout: float = 3.0) -> Optional[bytes]:
    """Read one protocol response frame. Returns full frame or None on timeout/error."""
    try:
        # Read header: Start(1) + Zone(1) + Cmd(1) + Answer(1) + DataLen(1) = 5 bytes
        header = await asyncio.wait_for(reader.readexactly(5), timeout=timeout)
        if header[0] != PROTOCOL_START:
            log(f"  Invalid frame start: 0x{header[0]:02X}")
            return None

        data_len = header[4]
        # Read data + end byte
        remaining = await asyncio.wait_for(reader.readexactly(data_len + 1), timeout=timeout)

        if remaining[-1] != PROTOCOL_END:
            log(f"  Invalid frame end: 0x{remaining[-1]:02X}")
            return None

        return header + remaining

    except asyncio.TimeoutError:
        return None
    except asyncio.IncompleteReadError:
        return None
    except (OSError, ConnectionError):
        return None


async def send_query(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    cmd: int,
    timeout: float = 3.0,
) -> Tuple[Optional[bytes], float]:
    """Send query and return (response_frame, elapsed_ms). Response is None on failure."""
    query = build_query(cmd)
    name = QUERY_NAMES.get(cmd, f"0x{cmd:02X}")

    start = time.perf_counter()
    try:
        writer.write(query)
        await writer.drain()
        frame = await read_frame(reader, timeout=timeout)
        elapsed = (time.perf_counter() - start) * 1000
        return frame, elapsed
    except (OSError, ConnectionError) as e:
        elapsed = (time.perf_counter() - start) * 1000
        log(f"  Send/receive error for {name}: {e}")
        return None, elapsed


async def open_connection(host: str, port: int, label: str, timeout: float = 5.0):
    """Open a TCP connection and return (reader, writer) or (None, None)."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        log(f"  {label}: connected")
        return reader, writer
    except (asyncio.TimeoutError, OSError, ConnectionRefusedError) as e:
        log(f"  {label}: FAILED to connect — {e}")
        return None, None


async def close_connection(writer: asyncio.StreamWriter, label: str, delay_ms: int = 50):
    """Close connection with post-close delay."""
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000.0)
    log(f"  {label}: closed (+ {delay_ms}ms delay)")


async def check_alive(reader: asyncio.StreamReader, label: str = "") -> bool:
    """Check if connection is alive, draining any unsolicited status frames.

    Unlike a naive single-byte read, this reads complete protocol frames
    so that the stream stays synchronized for subsequent read_frame() calls.
    The PDF states that state changes are relayed to all connected clients
    as unsolicited status messages — this function safely consumes them.
    """
    drained = 0
    while True:
        try:
            header = await asyncio.wait_for(reader.readexactly(5), timeout=0.15)

            if header[0] != PROTOCOL_START:
                # Non-frame data in the stream — log and stop draining
                pfx = f"  {label} " if label else "  "
                log(f"{pfx}drain: unexpected byte 0x{header[0]:02X} (stream may be corrupt)")
                break

            data_len = header[4]
            remaining = await asyncio.wait_for(reader.readexactly(data_len + 1), timeout=0.5)

            frame = header + remaining
            cmd = header[2]
            name = QUERY_NAMES.get(cmd, f"0x{cmd:02X}")
            data = frame[5:-1]
            pfx = f"  {label} " if label else "  "
            log(f"{pfx}drain: unsolicited {name} frame: {data.hex()}")
            drained += 1

        except asyncio.TimeoutError:
            # No more data pending — connection is alive and clean
            break

        except asyncio.IncompleteReadError:
            # EOF — remote closed the connection
            pfx = f"  {label} " if label else "  "
            log(f"{pfx}drain: EOF detected (remote closed)")
            return False

        except (OSError, ConnectionError):
            return False

    if drained > 0:
        pfx = f"  {label} " if label else "  "
        log(f"{pfx}drain: {drained} unsolicited frame(s) consumed")

    return True


# ─── TEST 1: Query Response Timing ──────────────────────────────────────────

async def test_query_response_timing(host: str, port: int):
    """Measure response time for each query type.

    Establishes baseline: how fast does the receiver respond?
    Run with receiver ON.
    """
    log_header("TEST 1: Query Response Timing (receiver must be ON)")

    reader, writer = await open_connection(host, port, "Conn")
    if not reader:
        log("SKIP: Cannot connect")
        return

    queries = [
        CMD_POWER, CMD_VOLUME, CMD_MUTE, CMD_CURRENT_SOURCE,
        CMD_AUDIO_FORMAT, CMD_SAMPLE_RATE, CMD_DECODE_2CH,
        CMD_DECODE_MCH, CMD_DIRECT_MODE,
    ]

    log("")
    log(f"  {'Query':<14} {'Response':>10} {'Time':>10}  Data")
    log(f"  {'-'*14} {'-'*10} {'-'*10}  {'-'*20}")

    for cmd in queries:
        name = QUERY_NAMES.get(cmd, f"0x{cmd:02X}")
        frame, elapsed = await send_query(reader, writer, cmd, timeout=3.0)

        if frame:
            answer = frame[3]
            data = frame[5:-1]
            status = "OK" if answer == PROTOCOL_ANSWER_OK else f"ERR(0x{answer:02X})"
            log(f"  {name:<14} {status:>10} {elapsed:>8.1f}ms  {data.hex()}")
        else:
            log(f"  {name:<14} {'TIMEOUT':>10} {elapsed:>8.1f}ms  —")

        # Small pause between queries (like real usage)
        await asyncio.sleep(0.05)

    await close_connection(writer, "Conn")


# ─── TEST 2: Connection Eviction on Command ─────────────────────────────────

async def test_connection_eviction(host: str, port: int):
    """Test if sending a command on conn2 causes the receiver to close conn1.

    This directly tests the "Socket closed by remote peer" scenario.
    """
    log_header("TEST 2: Connection Eviction (does command on conn2 kill conn1?)")

    # Step 1: Open conn1 (simulates the app)
    log_subheader("Step 1: Open conn1 (the 'app')")
    r1, w1 = await open_connection(host, port, "Conn1-app")
    if not r1:
        log("SKIP: Cannot open conn1")
        return

    alive = await check_alive(r1, "Conn1-app")
    log(f"  Conn1-app alive: {alive}")

    # Step 2: Open conn2 (simulates integration)
    log_subheader("Step 2: Open conn2 (the 'integration') — no commands yet")
    r2, w2 = await open_connection(host, port, "Conn2-integ")
    if not r2:
        log("SKIP: Cannot open conn2")
        await close_connection(w1, "Conn1-app")
        return

    # Check if just opening conn2 killed conn1
    await asyncio.sleep(0.2)
    alive = await check_alive(r1, "Conn1-app")
    log(f"  Conn1-app still alive after conn2 opened: {alive}")

    if not alive:
        log("  FINDING: Receiver closed conn1 just because conn2 was opened!")
        await close_connection(w2, "Conn2-integ")
        return

    # Step 3: Send a query on conn2
    log_subheader("Step 3: Send Power query on conn2")
    frame, elapsed = await send_query(r2, w2, CMD_POWER)
    if frame:
        log(f"  Conn2-integ got response: {frame.hex()} ({elapsed:.1f}ms)")
    else:
        log(f"  Conn2-integ: no response ({elapsed:.1f}ms)")

    # Step 4: Check if conn1 is still alive
    await asyncio.sleep(0.2)
    alive = await check_alive(r1, "Conn1-app")
    log(f"  Conn1-app still alive after conn2 sent command: {alive}")

    if not alive:
        log("  FINDING: Receiver closed conn1 when conn2 sent a command!")
    else:
        # Step 5: Try sending command on conn1 too
        log_subheader("Step 4: Send Volume query on conn1 (both active)")
        frame1, elapsed1 = await send_query(r1, w1, CMD_VOLUME)
        if frame1:
            log(f"  Conn1-app got response: {frame1.hex()} ({elapsed1:.1f}ms)")
        else:
            log(f"  Conn1-app: no response ({elapsed1:.1f}ms)")

        # Check conn2 after conn1 sent
        await asyncio.sleep(0.2)
        alive2 = await check_alive(r2, "Conn2-integ")
        log(f"  Conn2-integ still alive after conn1 sent command: {alive2}")

        if not alive2:
            log("  FINDING: Receiver closed conn2 when conn1 sent a command (LIFO eviction)")

    # Cleanup
    await close_connection(w1, "Conn1-app", delay_ms=0)
    await close_connection(w2, "Conn2-integ")


# ─── TEST 3: Multi-Query Burst Impact ───────────────────────────────────────

async def test_multi_query_burst(host: str, port: int):
    """Simulate integration polling: open conn2, send ALL queries, check conn1.

    This reproduces what the integration actually does every 30 seconds.
    """
    log_header("TEST 3: Multi-Query Burst (simulates integration poll cycle)")

    # Open conn1 (the "app")
    log_subheader("Open conn1 (app) — will monitor for closure")
    r1, w1 = await open_connection(host, port, "Conn1-app")
    if not r1:
        log("SKIP: Cannot open conn1")
        return

    # Open conn2 (integration)
    log_subheader("Open conn2 (integration) — sending query burst")
    r2, w2 = await open_connection(host, port, "Conn2-integ")
    if not r2:
        log("SKIP: Cannot open conn2")
        await close_connection(w1, "Conn1-app")
        return

    # Send all queries like the integration polling does
    poll_queries = [
        CMD_POWER, CMD_VOLUME, CMD_MUTE, CMD_CURRENT_SOURCE,
        CMD_AUDIO_FORMAT, CMD_DECODE_2CH, CMD_DECODE_MCH,
        CMD_SAMPLE_RATE, CMD_DIRECT_MODE,
    ]

    total_start = time.perf_counter()
    conn1_alive = True

    for cmd in poll_queries:
        name = QUERY_NAMES.get(cmd, f"0x{cmd:02X}")
        frame, elapsed = await send_query(r2, w2, cmd, timeout=3.0)

        status = "OK" if frame else "TIMEOUT"
        log(f"  Conn2 query {name}: {status} ({elapsed:.1f}ms)")

        # Check conn1 after each query
        if conn1_alive:
            alive = await check_alive(r1, "Conn1-app")
            if not alive:
                conn1_alive = False
                total_elapsed = (time.perf_counter() - total_start) * 1000
                log(f"  >>> Conn1-app CLOSED by receiver after {name} query ({total_elapsed:.0f}ms into burst)")

    total_elapsed = (time.perf_counter() - total_start) * 1000
    log(f"\n  Total burst time: {total_elapsed:.0f}ms")
    log(f"  Conn1-app survived burst: {conn1_alive}")

    if conn1_alive:
        log("  FINDING: App connection survives full polling burst")
    else:
        log("  FINDING: App connection killed during polling burst!")

    # Disconnect conn2 (like integration does after poll)
    log_subheader("Conn2 disconnects (integration poll done)")
    await close_connection(w2, "Conn2-integ")

    # If conn1 died, try to determine: can the app reconnect now?
    if not conn1_alive:
        await asyncio.sleep(0.1)
        log_subheader("Attempting conn1 reconnect (app retry)")
        r1_new, w1_new = await open_connection(host, port, "Conn1-app-retry")
        if r1_new:
            log("  App can reconnect after integration disconnects")
            await close_connection(w1_new, "Conn1-app-retry")
        else:
            log("  App CANNOT reconnect even after integration disconnects!")
    else:
        await close_connection(w1, "Conn1-app")


# ─── TEST 4: Connection Order and Last-Writer-Wins ──────────────────────────

async def test_command_interleaving(host: str, port: int):
    """Test alternating commands between two connections.

    Determines if the receiver supports true concurrent command processing
    or if it's last-command-wins / first-connection-wins.
    """
    log_header("TEST 4: Command Interleaving (alternating between 2 connections)")

    r1, w1 = await open_connection(host, port, "ConnA")
    if not r1:
        log("SKIP: Cannot open ConnA")
        return

    r2, w2 = await open_connection(host, port, "ConnB")
    if not r2:
        log("SKIP: Cannot open ConnB")
        await close_connection(w1, "ConnA")
        return

    # Alternate: A sends, B sends, A sends, B sends
    sequence = [
        ("ConnA", r1, w1, CMD_POWER),
        ("ConnB", r2, w2, CMD_VOLUME),
        ("ConnA", r1, w1, CMD_MUTE),
        ("ConnB", r2, w2, CMD_CURRENT_SOURCE),
        ("ConnA", r1, w1, CMD_VOLUME),
        ("ConnB", r2, w2, CMD_POWER),
    ]

    for label, reader, writer, cmd in sequence:
        name = QUERY_NAMES.get(cmd, f"0x{cmd:02X}")
        frame, elapsed = await send_query(reader, writer, cmd, timeout=3.0)

        if frame:
            data = frame[5:-1]
            log(f"  {label} -> {name}: OK ({elapsed:.1f}ms) data={data.hex()}")
        else:
            log(f"  {label} -> {name}: FAILED ({elapsed:.1f}ms)")
            # Check if the connection was closed
            alive = await check_alive(reader, label)
            if not alive:
                log(f"  >>> {label} connection was CLOSED by receiver!")
                break

        await asyncio.sleep(0.05)

    # Cleanup
    try:
        await close_connection(w1, "ConnA", delay_ms=0)
    except Exception:
        pass
    try:
        await close_connection(w2, "ConnB")
    except Exception:
        pass


# ─── TEST 5: Passive Monitor (reproduces app scenario) ──────────────────────

async def test_passive_monitor(host: str, port: int):
    """Open a passive 'app' connection that just listens while
    the 'integration' does a full connect-query-disconnect cycle.

    This is the closest reproduction of the real-world scenario.
    """
    log_header("TEST 5: Passive Monitor (app open, integration does full cycle)")

    # Conn1 = app (opens and stays idle, like the Lexicon app)
    log_subheader("Step 1: App opens connection and stays idle")
    r1, w1 = await open_connection(host, port, "App")
    if not r1:
        log("SKIP: Cannot open app connection")
        return

    # Let it sit idle for a moment (like a real app)
    await asyncio.sleep(1.0)
    alive = await check_alive(r1, "App")
    log(f"  App alive after 1s idle: {alive}")
    if not alive:
        log("  FINDING: Connection died while idle — unexpected!")
        return

    # Conn2 = integration does full poll cycle: connect → queries → disconnect
    log_subheader("Step 2: Integration connects, polls, disconnects")
    r2, w2 = await open_connection(host, port, "Integration")
    if not r2:
        log("SKIP: Cannot open integration connection")
        await close_connection(w1, "App")
        return

    # Integration sends all queries
    poll_queries = [CMD_POWER, CMD_VOLUME, CMD_MUTE, CMD_CURRENT_SOURCE]
    for cmd in poll_queries:
        name = QUERY_NAMES.get(cmd, f"0x{cmd:02X}")
        frame, elapsed = await send_query(r2, w2, cmd, timeout=3.0)
        status = "OK" if frame else "TIMEOUT"
        log(f"  Integration query {name}: {status} ({elapsed:.1f}ms)")
        await asyncio.sleep(0.05)

    # Integration disconnects
    await close_connection(w2, "Integration")

    # Check: is the app connection still alive?
    log_subheader("Step 3: Check app connection after integration cycle")
    await asyncio.sleep(0.2)
    alive = await check_alive(r1, "App")
    log(f"  App alive after integration cycle: {alive}")

    if alive:
        # Can the app still send commands?
        frame, elapsed = await send_query(r1, w1, CMD_VOLUME)
        if frame:
            log(f"  App query after integration cycle: OK ({elapsed:.1f}ms)")
        else:
            log(f"  App query after integration cycle: FAILED ({elapsed:.1f}ms)")
    else:
        log("  FINDING: App connection killed by integration poll cycle!")

    # Cleanup
    try:
        await close_connection(w1, "App")
    except Exception:
        pass


# ─── TEST 6: Repeated Poll Cycles ───────────────────────────────────────────

async def test_repeated_poll_cycles(host: str, port: int, cycles: int = 3, interval: float = 5.0):
    """Simulate multiple integration poll cycles while app stays connected.

    Reproduces the real-world scenario over multiple cycles to detect
    intermittent failures.
    """
    log_header(f"TEST 6: Repeated Poll Cycles ({cycles} cycles, {interval}s apart)")

    # App opens connection
    log_subheader("App connects")
    r_app, w_app = await open_connection(host, port, "App")
    if not r_app:
        log("SKIP: Cannot open app connection")
        return

    app_alive = True
    poll_queries = [CMD_POWER, CMD_VOLUME, CMD_MUTE, CMD_CURRENT_SOURCE]

    for cycle in range(1, cycles + 1):
        log_subheader(f"Poll cycle {cycle}/{cycles}")

        # Check app before cycle
        if app_alive:
            alive = await check_alive(r_app, "App")
            if not alive:
                app_alive = False
                log(f"  App connection DEAD before cycle {cycle}")

        # Integration: connect → poll → disconnect
        r_int, w_int = await open_connection(host, port, f"Integration-C{cycle}")
        if r_int:
            for cmd in poll_queries:
                name = QUERY_NAMES.get(cmd, f"0x{cmd:02X}")
                frame, elapsed = await send_query(r_int, w_int, cmd, timeout=3.0)
                status = "OK" if frame else "TIMEOUT"
                log(f"  C{cycle} query {name}: {status} ({elapsed:.1f}ms)")
                await asyncio.sleep(0.05)

            await close_connection(w_int, f"Integration-C{cycle}")
        else:
            log(f"  Integration could not connect for cycle {cycle}")

        # Check app after cycle
        if app_alive:
            await asyncio.sleep(0.2)
            alive = await check_alive(r_app, "App")
            if not alive:
                app_alive = False
                log(f"  >>> App connection KILLED during cycle {cycle}!")
            else:
                # Verify app can still query
                frame, elapsed = await send_query(r_app, w_app, CMD_VOLUME)
                if frame:
                    log(f"  App query after cycle {cycle}: OK ({elapsed:.1f}ms)")
                else:
                    log(f"  App query after cycle {cycle}: FAILED ({elapsed:.1f}ms)")
                    app_alive = False
                    log(f"  >>> App connection BROKEN after cycle {cycle}!")

        if not app_alive:
            log(f"  App died at cycle {cycle} — stopping repeated test")
            break

        # Wait between cycles
        if cycle < cycles:
            log(f"  Waiting {interval}s until next cycle...")
            await asyncio.sleep(interval)

    log_subheader("Summary")
    if app_alive:
        log(f"  App survived all {cycles} poll cycles")
    else:
        log(f"  App connection lost during testing")

    # Cleanup
    try:
        await close_connection(w_app, "App")
    except Exception:
        pass


# ─── TEST 7: Simultaneous Query Race ────────────────────────────────────────

async def test_simultaneous_query(host: str, port: int):
    """Send the same query from two connections at exactly the same time.

    Tests the worst case: true simultaneous protocol access.
    """
    log_header("TEST 7: Simultaneous Query (both send at exact same time)")

    r1, w1 = await open_connection(host, port, "ConnA")
    if not r1:
        log("SKIP: Cannot open ConnA")
        return

    r2, w2 = await open_connection(host, port, "ConnB")
    if not r2:
        log("SKIP: Cannot open ConnB")
        await close_connection(w1, "ConnA")
        return

    async def query_on(label, reader, writer, cmd):
        name = QUERY_NAMES.get(cmd, f"0x{cmd:02X}")
        frame, elapsed = await send_query(reader, writer, cmd, timeout=3.0)
        if frame:
            data = frame[5:-1]
            log(f"  {label} -> {name}: OK ({elapsed:.1f}ms) data={data.hex()}")
            return True
        else:
            log(f"  {label} -> {name}: FAILED ({elapsed:.1f}ms)")
            alive = await check_alive(reader, label)
            if not alive:
                log(f"  >>> {label} connection CLOSED by receiver!")
            return False

    # Fire both at the same time using gather
    log_subheader("Sending Volume query on both connections simultaneously")
    results = await asyncio.gather(
        query_on("ConnA", r1, w1, CMD_VOLUME),
        query_on("ConnB", r2, w2, CMD_VOLUME),
        return_exceptions=True,
    )

    log(f"  ConnA result: {results[0]}")
    log(f"  ConnB result: {results[1]}")

    # Try a second round if both survived
    if all(r is True for r in results):
        log_subheader("Round 2: Different queries simultaneously")
        results2 = await asyncio.gather(
            query_on("ConnA", r1, w1, CMD_POWER),
            query_on("ConnB", r2, w2, CMD_CURRENT_SOURCE),
            return_exceptions=True,
        )
        log(f"  ConnA result: {results2[0]}")
        log(f"  ConnB result: {results2[1]}")

    # Cleanup
    try:
        await close_connection(w1, "ConnA", delay_ms=0)
    except Exception:
        pass
    try:
        await close_connection(w2, "ConnB")
    except Exception:
        pass


# ─── TEST 8: Unsolicited Status Messages ──────────────────────────────────────

async def test_unsolicited_status(host: str, port: int):
    """Test if RC5 commands on one connection generate unsolicited status
    frames on another connection.

    The PDF states: "State changes as a result of other inputs are relayed
    back to connected RCs" and "An additional status message will be sent
    in most cases as a result of the IR command."

    This test sends an RC5 volume change on conn2 and checks whether conn1
    (passive observer) receives any unsolicited status frames. Volume is
    restored afterward.

    WARNING: This test will briefly change the volume by +1 step then -1 step.
    """
    log_header("TEST 8: Unsolicited Status Messages (does RC5 on conn2 push status to conn1?)")

    # Open conn1 (observer — simulates the app)
    log_subheader("Step 1: Open observer connection (the 'app')")
    r1, w1 = await open_connection(host, port, "Observer")
    if not r1:
        log("SKIP: Cannot open observer connection")
        return

    # Let it settle and drain any initial data
    await asyncio.sleep(0.5)
    alive = await check_alive(r1, "Observer")
    if not alive:
        log("SKIP: Observer connection died immediately")
        return

    # Open conn2 (commander — simulates the integration)
    log_subheader("Step 2: Open commander connection (the 'integration')")
    r2, w2 = await open_connection(host, port, "Commander")
    if not r2:
        log("SKIP: Cannot open commander connection")
        await close_connection(w1, "Observer")
        return

    # Step 3: Read current volume for reference
    log_subheader("Step 3: Read current volume on commander")
    frame, elapsed = await send_query(r2, w2, CMD_VOLUME)
    if frame:
        vol_data = frame[5:-1]
        log(f"  Current volume: 0x{vol_data.hex()} ({elapsed:.1f}ms)")
    else:
        log(f"  Could not read volume ({elapsed:.1f}ms) — continuing anyway")

    # Drain observer in case volume query generated something
    await asyncio.sleep(0.3)
    await check_alive(r1, "Observer")

    # Step 4: Send RC5 Volume Up on commander
    log_subheader("Step 4: Commander sends RC5 Volume Up")
    rc5_up = build_rc5_command(RC5_VOLUME_UP)
    start = time.perf_counter()
    try:
        w2.write(rc5_up)
        await w2.drain()
        log(f"  Sent RC5 Volume Up: {rc5_up.hex()}")

        # Read response on commander (RC5 simulate should get an ACK)
        cmd_response = await read_frame(r2, timeout=3.0)
        elapsed = (time.perf_counter() - start) * 1000
        if cmd_response:
            log(f"  Commander got RC5 response: {cmd_response.hex()} ({elapsed:.1f}ms)")
        else:
            log(f"  Commander: no RC5 response ({elapsed:.1f}ms)")
    except (OSError, ConnectionError) as e:
        log(f"  Commander send error: {e}")

    # Step 5: Wait and check for unsolicited frames on observer
    log_subheader("Step 5: Check observer for unsolicited status frames")
    # Give receiver time to push status updates
    await asyncio.sleep(1.0)

    # Drain observer — this will log any unsolicited frames it finds
    alive = await check_alive(r1, "Observer")
    log(f"  Observer alive after RC5 command: {alive}")

    if not alive:
        log("  FINDING: Observer connection KILLED by RC5 command on commander!")
    else:
        # Also try reading with longer timeout to catch delayed pushes
        log("  Checking for delayed unsolicited frames (2s window)...")
        await asyncio.sleep(2.0)
        alive = await check_alive(r1, "Observer")

    # Step 6: Also check if commander received extra unsolicited frames
    log_subheader("Step 6: Check commander for extra unsolicited frames")
    await check_alive(r2, "Commander")

    # Step 7: Restore volume — send RC5 Volume Down
    log_subheader("Step 7: Restore volume (RC5 Volume Down)")
    rc5_down = build_rc5_command(RC5_VOLUME_DOWN)
    try:
        w2.write(rc5_down)
        await w2.drain()
        log(f"  Sent RC5 Volume Down: {rc5_down.hex()}")

        cmd_response = await read_frame(r2, timeout=3.0)
        if cmd_response:
            log(f"  Commander got RC5 response: {cmd_response.hex()}")
        else:
            log(f"  Commander: no RC5 response")
    except (OSError, ConnectionError) as e:
        log(f"  Commander send error: {e}")

    # Final drain on observer after restore
    await asyncio.sleep(1.0)
    await check_alive(r1, "Observer")

    # Step 8: Verify both connections still functional
    log_subheader("Step 8: Final connectivity check")
    alive1 = await check_alive(r1, "Observer")
    log(f"  Observer alive: {alive1}")

    if alive1:
        frame, elapsed = await send_query(r1, w1, CMD_VOLUME)
        if frame:
            vol_data = frame[5:-1]
            log(f"  Observer query Volume: OK (0x{vol_data.hex()}, {elapsed:.1f}ms)")
        else:
            log(f"  Observer query Volume: FAILED ({elapsed:.1f}ms)")

    alive2 = await check_alive(r2, "Commander")
    log(f"  Commander alive: {alive2}")

    # Cleanup
    try:
        await close_connection(w1, "Observer", delay_ms=0)
    except Exception:
        pass
    try:
        await close_connection(w2, "Commander")
    except Exception:
        pass


# ─── MAIN ────────────────────────────────────────────────────────────────────

async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_connection_advanced.py <receiver_ip> [port]")
        print("Example: python test_connection_advanced.py 192.168.20.178")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 50000

    log_header("LEXICON RECEIVER — ADVANCED CONNECTION & PROTOCOL TESTS")
    log(f"Target: {host}:{port}")
    log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"NOTE: Receiver should be ON for meaningful results.")

    # Connectivity check
    log_subheader("Pre-flight connectivity check")
    r, w = await open_connection(host, port, "Pre-flight")
    if not r:
        log("ABORT: Cannot connect to receiver. Is it on? Is the IP correct?")
        return
    await close_connection(w, "Pre-flight")
    await asyncio.sleep(0.5)

    # Run all tests
    await test_query_response_timing(host, port)
    await asyncio.sleep(1)

    await test_connection_eviction(host, port)
    await asyncio.sleep(1)

    await test_multi_query_burst(host, port)
    await asyncio.sleep(1)

    await test_command_interleaving(host, port)
    await asyncio.sleep(1)

    await test_passive_monitor(host, port)
    await asyncio.sleep(1)

    await test_repeated_poll_cycles(host, port, cycles=3, interval=5.0)
    await asyncio.sleep(1)

    await test_simultaneous_query(host, port)
    await asyncio.sleep(1)

    await test_unsolicited_status(host, port)

    # Final summary
    log_header("ALL TESTS COMPLETE")
    log(f"Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Save results
    filename = "connection_advanced_results.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(results_log))
    log(f"\nResults saved to: {filename}")

    print("\n\nKEY QUESTIONS ANSWERED BY THESE TESTS:")
    print("1. How fast does the receiver respond to protocol queries? (Test 1)")
    print("2. Does sending a command on conn2 kill conn1? (Test 2)")
    print("3. Does a full poll burst kill the app connection? (Test 3)")
    print("4. Can commands alternate between connections? (Test 4)")
    print("5. Does connect-poll-disconnect cycle kill a passive app? (Test 5)")
    print("6. Does repeated polling eventually kill the app? (Test 6)")
    print("7. Can two connections query simultaneously? (Test 7)")
    print("8. Do RC5 commands push unsolicited status to other connections? (Test 8)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
