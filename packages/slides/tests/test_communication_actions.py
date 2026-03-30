"""
Tests for communication_actions.py - camera control integration.
"""
import sys
from pathlib import Path

# Ensure slides_app is importable
SLIDES_DIR = Path(__file__).resolve().parent.parent
if str(SLIDES_DIR) not in sys.path:
    sys.path.insert(0, str(SLIDES_DIR))

from slides_app import communication_actions
import action_pb2


def test_load_camera_control_config_enabled():
    """Test loading enabled camera control config"""
    config = {
        "camera_control": {
            "enabled": True,
            "device": {
                "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
                "name": "Companion"
            },
            "mappings": [
                {"titles": ["Prayer"], "command": "CC 9/3/0"}
            ]
        }
    }
    
    result = communication_actions.load_camera_control_config(config)
    assert result is not None
    assert result["enabled"] is True


def test_load_camera_control_config_disabled():
    """Test that disabled config returns None"""
    config = {
        "camera_control": {
            "enabled": False
        }
    }
    
    result = communication_actions.load_camera_control_config(config)
    assert result is None


def test_load_camera_control_config_missing():
    """Test that missing camera_control returns None"""
    config = {}
    
    result = communication_actions.load_camera_control_config(config)
    assert result is None


def test_get_camera_command_single_title():
    """Test matching with single title"""
    camera_config = {
        "mappings": [
            {"titles": ["Prayer"], "command": "CC 9/3/0"}
        ]
    }
    
    result = communication_actions.get_camera_command_for_item("Prayer", camera_config)
    assert result == "CC 9/3/0"


def test_get_camera_command_multiple_titles():
    """Test matching with multiple title variations"""
    camera_config = {
        "mappings": [
            {"titles": ["Prayer", "Prayers", "Prayer of Confession"], "command": "CC 9/3/0"}
        ]
    }
    
    # Test first variation
    result = communication_actions.get_camera_command_for_item("Prayer", camera_config)
    assert result == "CC 9/3/0"
    
    # Test second variation
    result = communication_actions.get_camera_command_for_item("Prayers", camera_config)
    assert result == "CC 9/3/0"
    
    # Test third variation
    result = communication_actions.get_camera_command_for_item("Prayer of Confession", camera_config)
    assert result == "CC 9/3/0"


def test_get_camera_command_case_insensitive():
    """Test that matching is case-insensitive"""
    camera_config = {
        "mappings": [
            {"titles": ["Prayer"], "command": "CC 9/3/0"}
        ]
    }
    
    result = communication_actions.get_camera_command_for_item("PRAYER", camera_config)
    assert result == "CC 9/3/0"
    
    result = communication_actions.get_camera_command_for_item("prayer", camera_config)
    assert result == "CC 9/3/0"
    
    result = communication_actions.get_camera_command_for_item("PrAyEr", camera_config)
    assert result == "CC 9/3/0"


def test_get_camera_command_whitespace_handling():
    """Test that whitespace is stripped during matching"""
    camera_config = {
        "mappings": [
            {"titles": ["Prayer"], "command": "CC 9/3/0"}
        ]
    }
    
    result = communication_actions.get_camera_command_for_item("  Prayer  ", camera_config)
    assert result == "CC 9/3/0"


def test_get_camera_command_no_match():
    """Test that non-matching title returns None"""
    camera_config = {
        "mappings": [
            {"titles": ["Prayer"], "command": "CC 9/3/0"}
        ]
    }
    
    result = communication_actions.get_camera_command_for_item("Scripture Reading", camera_config)
    assert result is None


def test_get_camera_command_multiple_mappings():
    """Test searching across multiple mappings"""
    camera_config = {
        "mappings": [
            {"titles": ["Prayer"], "command": "CC 9/3/0"},
            {"titles": ["Scripture Reading"], "command": "CC 9/1/0"},
            {"titles": ["Sermon"], "command": "CC 9/2/0"}
        ]
    }
    
    result = communication_actions.get_camera_command_for_item("Scripture Reading", camera_config)
    assert result == "CC 9/1/0"


def test_create_communication_action_structure():
    """Test that created action has correct protobuf structure"""
    camera_config = {
        "device": {
            "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
            "name": "Companion"
        },
        "command": {
            "format": "CC x",
            "replacement_range": {
                "start": 3,
                "end": 4
            }
        }
    }
    
    action = communication_actions.create_communication_action("CC 9/3/0", camera_config)
    
    # Check action type
    assert action.type == action_pb2.Action.ACTION_TYPE_COMMUNICATION
    
    # Check action is enabled
    assert action.isEnabled is True
    
    # Check UUID is present
    assert action.uuid.string != ""
    
    # Check name
    assert action.name == "Custom Control"


def test_create_communication_action_device_identification():
    """Test device identification in created action"""
    camera_config = {
        "device": {
            "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
            "name": "Companion"
        },
        "command": {
            "format": "CC x",
            "replacement_range": {"start": 3, "end": 4}
        }
    }
    
    action = communication_actions.create_communication_action("CC 9/3/0", camera_config)
    
    # Check device UUID
    assert action.communication.device_identification.parameter_uuid.string == "DA2125C2-2809-4822-85BE-A614022530BC"
    
    # Check device name
    assert action.communication.device_identification.parameter_name == "Companion"


def test_create_communication_action_command_format():
    """Test command format and value in created action"""
    camera_config = {
        "device": {
            "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
            "name": "Companion"
        },
        "command": {
            "format": "CC x",
            "replacement_range": {"start": 3, "end": 4}
        }
    }
    
    action = communication_actions.create_communication_action("CC 9/3/0", camera_config)
    
    # Check format
    assert action.communication.format == "CC x"
    
    # Check command value
    assert len(action.communication.commands) == 1
    cmd = action.communication.commands[0]
    assert cmd.value == "CC 9/3/0"
    assert cmd.name == "Custom Control"


def test_create_communication_action_replacement_range():
    """Test replacement range in created action"""
    camera_config = {
        "device": {
            "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
            "name": "Companion"
        },
        "command": {
            "format": "CC x",
            "replacement_range": {"start": 3, "end": 4}
        }
    }
    
    action = communication_actions.create_communication_action("CC 9/3/0", camera_config)
    
    cmd = action.communication.commands[0]
    assert cmd.replacement_range.start == 3
    assert cmd.replacement_range.end == 4
