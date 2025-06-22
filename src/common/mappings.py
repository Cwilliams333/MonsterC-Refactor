"""
Central location for all constant lookup maps and helper resolvers.

This module contains all the mapping dictionaries used throughout the application
for translating device codes, station IDs, and test results into human-readable names.
"""

from typing import Any, Dict, List, Union

# Test category to result fail descriptions mapping
TEST_TO_RESULT_FAIL_MAP: Dict[str, List[str]] = {
    "Display": [
        "Hot pixel analysis",
        "Burn in",
        "Blemish analysis",
        "6Y-Bad/Dead pixels/Lines/Areas",
        "6L-White Discolored Area",
        "6X-Display Burn-In of any type",
        "6M-Discolored DSP/Pressure Point",
        "6A-Display Fail",
        "6W-Horizontal/Vertical lines",
    ],
    "Mic": ["AQA_Microphone"],
    "Camera front photo": ["Front camera", "Front Camera"],
    "Camera rear photo": ["Camera Pictures", "Camera pictures", "Camera"],
    "Camera Flash": ["Camera Flash", "Camera flash"],
    "Speaker": ["AQA_Speaker"],
    "speaker": ["AQA_Earpiece"],
    "Touch": ["Touch screen", "Touch Screen"],
    "Vibration Engine": ["Device Vibrate", "Device vibrate"],
    "Proximity": ["Proximity sensor"],
    "Headset": ["AQA_Headset"],
}

# Station ID to machine/location mapping
STATION_TO_MACHINE: Dict[str, str] = {
    "radi135": "B56 Red Primary",
    "radi138": "B56 Red Primary",
    "radi115": "B56 Red Primary",
    "radi163": "B56 Red Primary",
    "radi185": "B56 Red Primary",
    "radi133": "B56 Red Primary",
    "radi160": "B18 Red Secondary",
    "radi161": "B18 Red Secondary",
    "radi162": "B18 Red Secondary",
    "radi181": "B18 Red Secondary",
    "radi183": "B18 Red Secondary",
    "radi116": "B18 Red Secondary",
    "radi154": "B25 Green Secondary",
    "radi155": "B25 Green Secondary",
    "radi156": "B25 Green Secondary",
    "radi166": "B25 Green Secondary",
    "radi158": "B25 Green Secondary",
    "radi157": "B25 Green Secondary",
    "radi149": "B17 Green Primary",
    "radi151": "B17 Green Primary",
    "radi152": "B17 Green Primary",
    "radi165": "B17 Green Primary",
    "radi164": "B17 Green Primary",
    "radi153": "B17 Green Primary",
    "radi079": "B24 Manual Trades",
    "radi044": "B24 Manual Trades",
    "radi041": "B24 Manual Trades",
    "radi055": "B22 Manual Core",
    "radi052": "B22 Manual Core",
    "radi058": "B22 Manual Core",
    "radi056": "B22 Manual Core",
    "radi078": "B22 Manual Core",
    "radi062": "B22 Manual Core",
    "radi081": "B22 Manual Core",
    # LS NPI Area
    "radi117": "B56 NPI Area",
    # New Bertta37 DHL stations
    "radi173": "B37 Packers",
    "radi177": "B37 Packers",
    "radi180": "B37 Packers",
    "radi172": "B37 Packers",
    "radi175": "B37 Packers",
    "radi176": "B37 Packers",
    # New Bertta58 DHL stations
    "radi169": "B58 Hawks",
    "radi171": "B58 Hawks",
    "radi174": "B58 Hawks",
    "radi178": "B58 Hawks",
    "radi179": "B58 Hawks",
    "radi182": "B58 Hawks",
}

# Device model to internal code mapping
DEVICE_MAP: Dict[str, Union[str, List[str]]] = {
    "iPhone6": "iphone7,2",
    "iPhone6 Plus": "iphone7,1",
    "iPhone6S": "iphone8,1",
    "iPhone6S Plus": "iphone8,2",
    "iPhoneSE (1st Gen)": "iphone8,4",
    "iPhone7": ["iphone9,1", "iphone9,3"],
    "iPhone7Plus": ["iphone9,2", "iphone9,4"],
    "iPhone8": "iphone10,1",
    "iPhone8Plus": ["iphone10,2", "iphone10,5"],
    "iPhoneX": ["iphone10,3", "iphone10,6"],
    "iPhoneXR": "iphone11,8",
    "iPhoneXS": "iphone11,2",
    "iPhoneXS-Max": ["iphone11,4", "iphone11,6"],
    "iPhone11": "iphone12,1",
    "iPhone11Pro": "iphone12,3",
    "iPhone11ProMax": "iphone12,5",
    "iPhoneSE2": "iphone12,8",
    "iPhone12": "iphone13,2",
    "iPhone12mini": "iphone13,1",
    "iPhone12Mini": "iphone13,1",
    "iPhone12Pro": "iphone13,3",
    "iPhone12ProMax": "iphone13,4",
    "iPhone13": "iphone14,5",
    "iPhone13mini": "iphone14,4",
    "iPhone13Mini": "iphone14,4",
    "iPhone13Pro": "iphone14,2",
    "iPhone13ProMax": "iphone14,3",
    "iPhoneSE3": "iphone14,6",
    "iPhone14": "iphone14,7",
    "iPhone14Plus": "iphone14,8",
    "iPhone14Pro": "iphone15,2",
    "iPhone14ProMax": "iphone15,3",
    "iPhone15": "iphone15,4",
    "iPhone15Plus": "iphone15,5",
    "iPhone15Pro": "iphone16,1",
    "iPhone15ProMax": "iphone16,2",
    "iPhone16": "iphone17,3",
    "iPhone16Plus": "iphone17,4",
    "iPhone16Pro": "iphone17,1",
    "iPhone16ProMax": "iphone17,2",
    "SM-G996U": "t2q",
    "SM-A156U": "a15x",
    "SM-A037U": "a03su",
    "SM-S928U": "e3q",
    "SM-S926U": "e2q",
    "SM-S921U": "e1q",
    "SM-G991U": "o1q",
    "SM-G998U": "p3q",
    "SM-G781V": "r8q",
    "SM-S906U": "g0q",
    "SM-S901U": "r0q",
    "SM-A515U": "a51",
    "SM-A426U": "a42xuq",
    "SM-A426U1": "a42xuq",
    "SM-G981V": "x1q",
    "SM-N986U": "c2q",
    "SM-G970U": "beyond0q",
    "SM-G965U": "star2qltesq",
    "SM-G960U": "starqltesq",
    "SM-G975U": "beyond2q",
    "SM-G986U": "y2q",
    "SM-S908U": "b0q",
    "SM-S911U": "dm1q",
    "SM-S918U": "dm3q",
    "SM-S916U": "dm2q",
    "SM-N960U": "crownqltesq",
    "SM-N975U": "d2q",
    "SM-N970U": "d1q",
    "SM-A215U": "a21",
    "SM-A505U": "a50",
    "SM-A716V": "a71xq",
    "SM-G950U": "dreamqltesq",
    "SM-A236V": "a23x",
    "Pixel 6a": "bluejay",
    "Pixel 6": "oriole",
    "Pixel 6 Pro": "raven",
    "Pixel 7": "panther",
    "Pixel 7a": "lynx",
    "Pixel 7 Pro": "cheetah",
    "Pixel 8": "shiba",
    "Pixel 8 Pro": "husky",
    "Pixel 8a": "akita",
    "Pixel 9": "tokay",
    "Pixel 9 Pro": "caiman",
    "Pixel 9 Pro XL": "komodo",
    "SM-G973U": "beyond1q",
    "SM-G973U1": "beyond1q",
    "SM-G988U": "z3q",
    "SM-G991U1": "o1q",
    "SM-A102U": "a10e",
    "SM-A205U": "a20q",
    "SM-S711U": "r11q",
    "SM-S721U": "r12s",
    "SM-S938U": "pa3q",
    "SM-S936U": "pa2q",
    "SM-S931U": "pa1q",
}


def get_device_code(model: str) -> str:
    """
    Helper function to get device code from device map.

    Args:
        model: Device model name

    Returns:
        Device code string, or 'Unknown' if not found
    """
    code = DEVICE_MAP.get(model, "Unknown")
    if isinstance(code, list):
        return code[0]  # Take first code if multiple exist
    return code


def resolve_station(station_id: str) -> str:
    """
    Resolve a station ID to a machine/location name.

    Args:
        station_id: Station identifier

    Returns:
        Human-readable machine/location name
    """
    return STATION_TO_MACHINE.get(station_id.lower(), "Unknown Machine")


def get_test_from_result_fail(result_fail: str) -> str:
    """
    Resolve a result_fail description to a test category name.

    Args:
        result_fail: Failure description from test results

    Returns:
        Test category name, or 'Unknown Test' if not found
    """
    for test, descriptions in TEST_TO_RESULT_FAIL_MAP.items():
        if result_fail in descriptions:
            return test
    return "Unknown Test"
