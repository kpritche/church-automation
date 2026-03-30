"""
Tests for service-specific any_song camera mappings
"""
import sys
from pathlib import Path

# Ensure slides_app is importable
SLIDES_DIR = Path(__file__).resolve().parent.parent
if str(SLIDES_DIR) not in sys.path:
    sys.path.insert(0, str(SLIDES_DIR))

from slides_app import communication_actions


def test_any_song_mapping_matches_song_in_service():
    """Test that any_song mapping matches songs in the specified service"""
    camera_config = {
        "mappings": [
            {
                "match_type": "any_song",
                "service_type_ids": [1041663],
                "command": "CC 9/4/0"
            }
        ]
    }
    
    # Should match any song title in service 1041663
    result = communication_actions.get_camera_command_for_item(
        "Amazing Grace",
        camera_config,
        service_type_id=1041663,
        is_song=True
    )
    assert result == "CC 9/4/0"
    
    # Different song title should also match
    result = communication_actions.get_camera_command_for_item(
        "How Great Thou Art",
        camera_config,
        service_type_id=1041663,
        is_song=True
    )
    assert result == "CC 9/4/0"


def test_any_song_mapping_does_not_match_different_service():
    """Test that any_song mapping does not match songs in other services"""
    camera_config = {
        "mappings": [
            {
                "match_type": "any_song",
                "service_type_ids": [1041663],
                "command": "CC 9/4/0"
            }
        ]
    }
    
    # Should not match song in different service
    result = communication_actions.get_camera_command_for_item(
        "Amazing Grace",
        camera_config,
        service_type_id=78127,
        is_song=True
    )
    assert result is None


def test_any_song_mapping_does_not_match_non_song():
    """Test that any_song mapping does not match non-song items"""
    camera_config = {
        "mappings": [
            {
                "match_type": "any_song",
                "service_type_ids": [1041663],
                "command": "CC 9/4/0"
            }
        ]
    }
    
    # Should not match non-song items even in correct service
    result = communication_actions.get_camera_command_for_item(
        "Prayer",
        camera_config,
        service_type_id=1041663,
        is_song=False
    )
    assert result is None


def test_any_song_with_multiple_services():
    """Test that any_song mapping works with multiple service type IDs"""
    camera_config = {
        "mappings": [
            {
                "match_type": "any_song",
                "service_type_ids": [78127, 1145553],
                "command": "CC 9/5/0"
            }
        ]
    }
    
    # Should match song in first service
    result = communication_actions.get_camera_command_for_item(
        "Song Title",
        camera_config,
        service_type_id=78127,
        is_song=True
    )
    assert result == "CC 9/5/0"
    
    # Should match song in second service
    result = communication_actions.get_camera_command_for_item(
        "Different Song",
        camera_config,
        service_type_id=1145553,
        is_song=True
    )
    assert result == "CC 9/5/0"


def test_exact_mapping_takes_precedence_over_any_song():
    """Test that exact title mappings are checked before any_song mappings"""
    camera_config = {
        "mappings": [
            {"titles": ["Special Song"], "command": "CC 9/1/0"},
            {
                "match_type": "any_song",
                "service_type_ids": [1041663],
                "command": "CC 9/4/0"
            }
        ]
    }
    
    # Exact match should take precedence
    result = communication_actions.get_camera_command_for_item(
        "Special Song",
        camera_config,
        service_type_id=1041663,
        is_song=True
    )
    assert result == "CC 9/1/0"
    
    # Other songs should match any_song mapping
    result = communication_actions.get_camera_command_for_item(
        "Regular Song",
        camera_config,
        service_type_id=1041663,
        is_song=True
    )
    assert result == "CC 9/4/0"


def test_any_song_without_service_restriction():
    """Test any_song mapping without service_type_ids matches all services"""
    camera_config = {
        "mappings": [
            {
                "match_type": "any_song",
                "command": "CC 9/0/0"
            }
        ]
    }
    
    # Should match songs in any service
    result = communication_actions.get_camera_command_for_item(
        "Song Title",
        camera_config,
        service_type_id=1041663,
        is_song=True
    )
    assert result == "CC 9/0/0"
    
    result = communication_actions.get_camera_command_for_item(
        "Another Song",
        camera_config,
        service_type_id=78127,
        is_song=True
    )
    assert result == "CC 9/0/0"


def test_backward_compatibility_with_exact_mappings():
    """Test that existing exact title mappings still work"""
    camera_config = {
        "mappings": [
            {"titles": ["Prayer", "Prayers"], "command": "CC 9/3/0"},
            {"titles": ["Scripture Reading"], "command": "CC 9/2/1"}
        ]
    }
    
    # Should match exact titles
    result = communication_actions.get_camera_command_for_item(
        "Prayer",
        camera_config
    )
    assert result == "CC 9/3/0"
    
    result = communication_actions.get_camera_command_for_item(
        "Scripture Reading",
        camera_config
    )
    assert result == "CC 9/2/1"
