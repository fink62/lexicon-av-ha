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

# Status Query Commands
PROTOCOL_CMD_POWER = 0x00          # Request power state
PROTOCOL_CMD_VOLUME = 0x0D         # Set/Request volume (0x00-0x63 = 0-99)
PROTOCOL_CMD_MUTE = 0x0E           # Request mute status
PROTOCOL_CMD_DIRECT_MODE = 0x0F    # Request direct mode status
PROTOCOL_CMD_DECODE_2CH = 0x10     # Request decode mode for 2-channel
PROTOCOL_CMD_DECODE_MCH = 0x11     # Request decode mode for multi-channel
PROTOCOL_CMD_CURRENT_SOURCE = 0x1D # Request current source
PROTOCOL_CMD_AUDIO_FORMAT = 0x43   # Request incoming audio format
PROTOCOL_CMD_SAMPLE_RATE = 0x44    # Request incoming audio sample rate

# Request Data Byte
PROTOCOL_REQUEST = 0xF0

# Polling
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Source Code Mapping (Response codes from Command 0x1D - PDF page 9)
# These are DIFFERENT from RC5 command codes!
SOURCE_CODES = {
    0x00: "FOLLOW_ZONE1",
    0x01: "CD",
    0x02: "BD",
    0x03: "AV",
    0x04: "SAT",
    0x05: "PVR",
    0x06: "VCR",
    0x08: "AUX",
    0x09: "DISPLAY",
    0x0B: "RADIO",      # FM
    0x0C: "RADIO_DAB",  # DAB
    0x0E: "NET",
    0x0F: "USB",
    0x10: "STB",
    0x11: "GAME",
}

# Decode Mode Mapping - 2 Channel Material (Command 0x10 Response)
DECODE_MODE_2CH = {
    0x01: "Stereo",
    0x04: "Dolby Surround",
    0x07: "Neo:6 Cinema",
    0x08: "Neo:6 Music",
    0x09: "5/7 Ch Stereo",
    0x0A: "DTS Neural:X",
    0x0B: "Logic7 Immersion",
    0x0C: "DTS Virtual:X",
}

# Decode Mode Mapping - Multi-Channel Material (Command 0x11 Response)
DECODE_MODE_MCH = {
    0x01: "Stereo Downmix",
    0x02: "Multi-Channel",
    0x03: "DTS Neural:X",
    0x06: "Dolby Surround",
    0x0B: "Logic7 Immersion",
    0x0C: "DTS Virtual:X",
}

# Audio Format Mapping (Command 0x43 Response - Data1)
AUDIO_FORMAT = {
    0x00: "PCM",
    0x01: "Analogue Direct",
    0x02: "Dolby Digital",
    0x03: "Dolby Digital EX",
    0x04: "Dolby Surround",
    0x05: "Dolby Digital Plus",
    0x06: "Dolby TrueHD",
    0x07: "DTS",
    0x08: "DTS 96/24",
    0x09: "DTS ES Matrix",
    0x0A: "DTS ES Discrete",
    0x0B: "DTS ES Matrix 96/24",
    0x0C: "DTS ES Discrete 96/24",
    0x0D: "DTS HD Master Audio",
    0x0E: "DTS HD High Res",
    0x0F: "DTS Low Bit Rate",
    0x10: "DTS Core",
    0x13: "PCM Zero",
    0x14: "Unsupported",
    0x15: "Undetected",
    0x16: "Dolby Atmos",
    0x17: "DTS:X",
    0x18: "IMAX Enhanced",
}

# Sample Rate Mapping (Command 0x44 Response)
SAMPLE_RATE = {
    0x00: "32 kHz",
    0x01: "44.1 kHz",
    0x02: "48 kHz",
    0x03: "88.2 kHz",
    0x04: "96 kHz",
    0x05: "176.4 kHz",
    0x06: "192 kHz",
    0x07: "Unknown",
    0x08: "Undetected",
}
