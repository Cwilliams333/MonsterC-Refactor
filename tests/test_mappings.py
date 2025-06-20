"""Unit tests for common.mappings module."""

import pytest
from src.common.mappings import (
    get_device_code,
    resolve_station,
    get_test_from_result_fail,
    DEVICE_MAP,
    STATION_TO_MACHINE,
    TEST_TO_RESULT_FAIL_MAP
)


class TestGetDeviceCode:
    """Test cases for get_device_code function."""
    
    def test_valid_device_single_code(self):
        """Test retrieving device code for device with single code."""
        assert get_device_code("iPhone14ProMax") == "iphone15,3"
        assert get_device_code("iPhone16") == "iphone17,3"
        assert get_device_code("Pixel 8 Pro") == "husky"
    
    def test_valid_device_multiple_codes(self):
        """Test retrieving device code for device with multiple codes (returns first)."""
        assert get_device_code("iPhone7") == "iphone9,1"
        assert get_device_code("iPhone8Plus") == "iphone10,2"
        assert get_device_code("iPhoneXS-Max") == "iphone11,4"
    
    def test_unknown_device(self):
        """Test handling of unknown device models."""
        assert get_device_code("UnknownDevice") == "Unknown"
        assert get_device_code("") == "Unknown"
        assert get_device_code("iPhone999") == "Unknown"
    
    def test_case_sensitivity(self):
        """Test that device names are case-sensitive."""
        # The function expects exact case match
        assert get_device_code("iphone14promax") == "Unknown"
        assert get_device_code("IPHONE14PROMAX") == "Unknown"


class TestResolveStation:
    """Test cases for resolve_station function."""
    
    def test_valid_station_ids(self):
        """Test resolving valid station IDs."""
        assert resolve_station("radi135") == "B56 Red Primary"
        assert resolve_station("radi044") == "B24 Manual Trades"
        assert resolve_station("radi169") == "B58 Hawks"
        assert resolve_station("radi117") == "B56 NPI Area"
    
    def test_case_insensitive(self):
        """Test that station IDs are case-insensitive."""
        assert resolve_station("RADI135") == "B56 Red Primary"
        assert resolve_station("Radi044") == "B24 Manual Trades"
        assert resolve_station("RADI169") == "B58 Hawks"
    
    def test_unknown_station(self):
        """Test handling of unknown station IDs."""
        assert resolve_station("radi999") == "Unknown Machine"
        assert resolve_station("") == "Unknown Machine"
        assert resolve_station("invalid") == "Unknown Machine"
    
    def test_all_mapped_stations(self):
        """Test that all stations in the map resolve correctly."""
        for station_id, expected_machine in STATION_TO_MACHINE.items():
            assert resolve_station(station_id) == expected_machine


class TestGetTestFromResultFail:
    """Test cases for get_test_from_result_fail function."""
    
    def test_display_failures(self):
        """Test mapping display-related failures."""
        assert get_test_from_result_fail("Hot pixel analysis") == "Display"
        assert get_test_from_result_fail("6A-Display Fail") == "Display"
        assert get_test_from_result_fail("6W-Horizontal/Vertical lines") == "Display"
    
    def test_camera_failures(self):
        """Test mapping camera-related failures."""
        assert get_test_from_result_fail("Front Camera") == "Camera front photo"
        assert get_test_from_result_fail("Camera Pictures") == "Camera rear photo"
        assert get_test_from_result_fail("Camera Flash") == "Camera Flash"
    
    def test_audio_failures(self):
        """Test mapping audio-related failures."""
        assert get_test_from_result_fail("AQA_Microphone") == "Mic"
        assert get_test_from_result_fail("AQA_Speaker") == "Speaker"
        assert get_test_from_result_fail("AQA_Earpiece") == "speaker"
        assert get_test_from_result_fail("AQA_Headset") == "Headset"
    
    def test_other_failures(self):
        """Test mapping other failure types."""
        assert get_test_from_result_fail("Touch Screen") == "Touch"
        assert get_test_from_result_fail("Device Vibrate") == "Vibration Engine"
        assert get_test_from_result_fail("Proximity sensor") == "Proximity"
    
    def test_unknown_failure(self):
        """Test handling of unknown failure descriptions."""
        assert get_test_from_result_fail("Unknown Failure") == "Unknown Test"
        assert get_test_from_result_fail("") == "Unknown Test"
        assert get_test_from_result_fail("Random Error") == "Unknown Test"
    
    def test_case_sensitivity_matters(self):
        """Test that failure descriptions are case-sensitive."""
        # The function expects exact case match
        assert get_test_from_result_fail("camera pictures") != "Camera rear photo"
        assert get_test_from_result_fail("touch screen") != "Touch"


class TestMappingDataIntegrity:
    """Test the integrity of mapping data structures."""
    
    def test_device_map_structure(self):
        """Test that device map values are strings or lists of strings."""
        for device, code in DEVICE_MAP.items():
            assert isinstance(device, str), f"Device key {device} should be string"
            assert isinstance(code, (str, list)), f"Device code for {device} should be string or list"
            if isinstance(code, list):
                assert all(isinstance(c, str) for c in code), f"All codes for {device} should be strings"
                assert len(code) > 0, f"Code list for {device} should not be empty"
    
    def test_station_map_structure(self):
        """Test that station map has string keys and values."""
        for station, machine in STATION_TO_MACHINE.items():
            assert isinstance(station, str), f"Station key {station} should be string"
            assert isinstance(machine, str), f"Machine name for {station} should be string"
            assert station.lower() == station, f"Station ID {station} should be lowercase"
    
    def test_test_fail_map_structure(self):
        """Test that test fail map has proper structure."""
        for test, failures in TEST_TO_RESULT_FAIL_MAP.items():
            assert isinstance(test, str), f"Test key {test} should be string"
            assert isinstance(failures, list), f"Failures for {test} should be a list"
            assert len(failures) > 0, f"Failure list for {test} should not be empty"
            assert all(isinstance(f, str) for f in failures), f"All failures for {test} should be strings"
    
    def test_no_duplicate_failures(self):
        """Test that no failure description appears in multiple test categories."""
        seen_failures = {}
        for test, failures in TEST_TO_RESULT_FAIL_MAP.items():
            for failure in failures:
                if failure in seen_failures:
                    pytest.fail(f"Failure '{failure}' appears in both '{test}' and '{seen_failures[failure]}'")
                seen_failures[failure] = test