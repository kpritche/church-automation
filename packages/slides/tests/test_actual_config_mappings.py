"""
Integration test for the actual slides_config.json camera mappings
"""
import sys
import json
from pathlib import Path

# Ensure slides_app is importable
SLIDES_DIR = Path(__file__).resolve().parent.parent
if str(SLIDES_DIR) not in sys.path:
    sys.path.insert(0, str(SLIDES_DIR))

from slides_app import communication_actions


def test_first_up_song_service_1041663():
    """Test that any song in service 1041663 maps to CC 9/4/0 (First Up Song)"""
    # Load actual config
    config_path = SLIDES_DIR / "slides_config.json"
    with open(config_path) as f:
        cfg = json.load(f)
    
    camera_config = communication_actions.load_camera_control_config(cfg)
    
    # Test various song titles in service 1041663
    test_songs = ["Amazing Grace", "How Great Thou Art", "Forever Reign", "10,000 Reasons"]
    
    for song_title in test_songs:
        result = communication_actions.get_camera_command_for_item(
            song_title,
            camera_config,
            service_type_id=1041663,
            is_song=True
        )
        assert result == "CC 9/4/0", f"Song '{song_title}' in service 1041663 should map to CC 9/4/0"


def test_celebrate_song_services_78127_and_1145553():
    """Test that any song in services 78127/1145553 maps to CC 9/5/0 (Celebrate Song)"""
    # Load actual config
    config_path = SLIDES_DIR / "slides_config.json"
    with open(config_path) as f:
        cfg = json.load(f)
    
    camera_config = communication_actions.load_camera_control_config(cfg)
    
    test_songs = ["Build Your Kingdom Here", "Cornerstone", "Great Are You Lord"]
    
    # Test service 78127
    for song_title in test_songs:
        result = communication_actions.get_camera_command_for_item(
            song_title,
            camera_config,
            service_type_id=78127,
            is_song=True
        )
        assert result == "CC 9/5/0", f"Song '{song_title}' in service 78127 should map to CC 9/5/0"
    
    # Test service 1145553
    for song_title in test_songs:
        result = communication_actions.get_camera_command_for_item(
            song_title,
            camera_config,
            service_type_id=1145553,
            is_song=True
        )
        assert result == "CC 9/5/0", f"Song '{song_title}' in service 1145553 should map to CC 9/5/0"


def test_non_songs_dont_match_any_song_mappings():
    """Test that non-song items don't match any_song mappings"""
    # Load actual config
    config_path = SLIDES_DIR / "slides_config.json"
    with open(config_path) as f:
        cfg = json.load(f)
    
    camera_config = communication_actions.load_camera_control_config(cfg)
    
    # Non-song items should not match any_song mappings
    result = communication_actions.get_camera_command_for_item(
        "Some Random Item",
        camera_config,
        service_type_id=1041663,
        is_song=False
    )
    assert result is None, "Non-song items should not match any_song mappings"


def test_exact_mappings_still_work():
    """Test that exact title mappings still work alongside any_song mappings"""
    # Load actual config
    config_path = SLIDES_DIR / "slides_config.json"
    with open(config_path) as f:
        cfg = json.load(f)
    
    camera_config = communication_actions.load_camera_control_config(cfg)
    
    # Test exact mappings
    exact_tests = [
        ("Prayer", "CC 9/3/0"),
        ("Prayers", "CC 9/3/0"),
        ("Welcome", "CC 9/2/0"),
        ("Countdown", "CC 9/1/0"),
        ("Passing Peace", "CC 9/6/0"),
        ("Scripture Reading", "CC 9/2/1"),
        ("Sermon", "CC 9/1/1"),
        ("Benediction", "CC 9/7/1"),
    ]
    
    for title, expected_command in exact_tests:
        result = communication_actions.get_camera_command_for_item(
            title,
            camera_config
        )
        assert result == expected_command, f"'{title}' should map to {expected_command}"
