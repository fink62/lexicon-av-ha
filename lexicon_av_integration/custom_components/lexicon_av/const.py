"""Constants for the Lexicon AV Receiver integration."""

DOMAIN = "lexicon_av"

# Configuration
CONF_HOST = "host"
CONF_PORT = "port"
CONF_INPUT_MAPPINGS = "input_mappings"

# Defaults
DEFAULT_PORT = 50000
DEFAULT_NAME = "Lexicon AV Receiver"
DEFAULT_TIMEOUT = 3

# RC5 System Code
RC5_SYSTEM = 0x10

# Available Lexicon physical inputs with RC5 codes
LEXICON_INPUTS = {
    "BD": 0x62,       # BluRay/DVD
    "CD": 0x76,       # CD Player
    "STB": 0x64,      # Set Top Box
    "AV": 0x5E,       # AV Input
    "SAT": 0x1B,      # Satellite
    "PVR": 0x60,      # Personal Video Recorder
    "GAME": 0x61,     # Game Console
    "VCR": 0x77,      # Video Cassette Recorder
    "AUX": 0x63,      # Auxiliary
    "RADIO": 0x5B,    # Tuner/Radio
    "NET": 0x5C,      # Network
    "USB": 0x5D,      # USB
    "DISPLAY": 0x3A,  # TV Audio Return Channel (ARC)
}

# RC5 Commands
RC5_POWER_TOGGLE = 0x0C  # Main power toggle
RC5_POWER_ON = 0x7B      # Discrete power on (may not work on all units)
RC5_POWER_OFF = 0x7C     # Discrete power off (may not work on all units)
RC5_VOLUME_UP = 0x10
RC5_VOLUME_DOWN = 0x11
RC5_MUTE_TOGGLE = 0x0D
RC5_MUTE_ON = 0x1A
RC5_MUTE_OFF = 0x78

# Protocol
PROTOCOL_START = 0x21
PROTOCOL_END = 0x0D
PROTOCOL_ZONE1 = 0x01
PROTOCOL_CMD_SIMULATE_RC5 = 0x08
PROTOCOL_DATA_LENGTH = 0x02
PROTOCOL_ANSWER_OK = 0x00
