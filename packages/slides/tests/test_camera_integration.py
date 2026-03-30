"""
Tests for camera control integration in make_pro.py
"""
import sys
import tempfile
from pathlib import Path
import json
from unittest.mock import Mock, patch, MagicMock

# Ensure slides_app is importable
SLIDES_DIR = Path(__file__).resolve().parent.parent
if str(SLIDES_DIR) not in sys.path:
    sys.path.insert(0, str(SLIDES_DIR))

# Ensure protobuf modules are importable
PROTO_DIR = SLIDES_DIR / "ProPresenter7_Proto" / "generated"
if PROTO_DIR.exists() and str(PROTO_DIR) not in sys.path:
    sys.path.insert(0, str(PROTO_DIR))

# Mock the config module before importing make_pro
sys.modules['church_automation_shared.config'] = MagicMock()

from slides_app import make_pro
import presentation_pb2
import action_pb2


def test_camera_action_inserted_when_mapping_exists(tmp_path):
    """Test that camera control action is inserted when title has mapping"""
    # Create minimal slides config
    slides = [
        {"text": "First slide text", "style": "normal", "is_bold": False}
    ]
    
    parsed = {
        "title": "Prayer",
        "text_chunks": ["First slide text"],
        "item_id": "12345"
    }
    
    camera_config = {
        "enabled": True,
        "device": {
            "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
            "name": "Companion"
        },
        "command": {
            "format": "CC x",
            "replacement_range": {"start": 3, "end": 4}
        },
        "mappings": [
            {"titles": ["Prayer"], "command": "CC 9/3/0"}
        ]
    }
    
    filename = tmp_path / "test_output.pro"
    
    # Call make_pro_for_items with camera config
    make_pro.make_pro_for_items(
        slides,
        parsed,
        str(filename.name),
        plan_date="2026-03-30",
        camera_config=camera_config
    )
    
    # Read the generated .pro file
    output_dir = make_pro.SLIDES_OUTPUTS_DIR / "2026-03-30"
    output_file = output_dir / filename.name
    
    assert output_file.exists(), "Output file should be created"
    
    # Parse the protobuf
    presentation = presentation_pb2.Presentation()
    with open(output_file, 'rb') as f:
        presentation.ParseFromString(f.read())
    
    # Verify first cue has at least 2 actions (camera + slide)
    assert len(presentation.cues) > 0, "Should have at least one cue"
    first_cue = presentation.cues[0]
    assert len(first_cue.actions) >= 2, "First cue should have camera action + slide action"
    
    # Verify first action is communication type
    camera_action = first_cue.actions[0]
    assert camera_action.type == action_pb2.Action.ACTION_TYPE_COMMUNICATION
    assert camera_action.communication.device_identification.parameter_uuid.string == "DA2125C2-2809-4822-85BE-A614022530BC"
    assert len(camera_action.communication.commands) == 1
    assert camera_action.communication.commands[0].value == "CC 9/3/0"


def test_no_camera_action_when_disabled(tmp_path):
    """Test that no camera action is inserted when camera control is disabled"""
    slides = [
        {"text": "First slide text", "style": "normal", "is_bold": False}
    ]
    
    parsed = {
        "title": "Prayer",
        "text_chunks": ["First slide text"],
        "item_id": "12345"
    }
    
    camera_config = {
        "enabled": False,  # Disabled
        "mappings": [
            {"titles": ["Prayer"], "command": "CC 9/3/0"}
        ]
    }
    
    filename = tmp_path / "test_output_disabled.pro"
    
    # Call make_pro_for_items with disabled camera config
    make_pro.make_pro_for_items(
        slides,
        parsed,
        str(filename.name),
        plan_date="2026-03-30",
        camera_config=camera_config
    )
    
    # Read the generated .pro file
    output_dir = make_pro.SLIDES_OUTPUTS_DIR / "2026-03-30"
    output_file = output_dir / filename.name
    
    presentation = presentation_pb2.Presentation()
    with open(output_file, 'rb') as f:
        presentation.ParseFromString(f.read())
    
    # Should only have slide action, no camera action
    first_cue = presentation.cues[0]
    assert len(first_cue.actions) == 1, "Should only have slide action when camera disabled"
    
    # Verify it's NOT a communication action
    assert first_cue.actions[0].type != action_pb2.Action.ACTION_TYPE_COMMUNICATION


def test_no_camera_action_when_no_mapping(tmp_path):
    """Test that no camera action is inserted when title has no mapping"""
    slides = [
        {"text": "First slide text", "style": "normal", "is_bold": False}
    ]
    
    parsed = {
        "title": "Unmapped Item",  # No mapping for this title
        "text_chunks": ["First slide text"],
        "item_id": "12345"
    }
    
    camera_config = {
        "enabled": True,
        "device": {
            "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
            "name": "Companion"
        },
        "command": {
            "format": "CC x",
            "replacement_range": {"start": 3, "end": 4}
        },
        "mappings": [
            {"titles": ["Prayer"], "command": "CC 9/3/0"}
        ]
    }
    
    filename = tmp_path / "test_output_unmapped.pro"
    
    make_pro.make_pro_for_items(
        slides,
        parsed,
        str(filename.name),
        plan_date="2026-03-30",
        camera_config=camera_config
    )
    
    # Read the generated .pro file
    output_dir = make_pro.SLIDES_OUTPUTS_DIR / "2026-03-30"
    output_file = output_dir / filename.name
    
    presentation = presentation_pb2.Presentation()
    with open(output_file, 'rb') as f:
        presentation.ParseFromString(f.read())
    
    # Should only have slide action since no mapping exists
    first_cue = presentation.cues[0]
    assert len(first_cue.actions) == 1, "Should only have slide action when no mapping found"


def test_camera_action_with_multiple_title_variations(tmp_path):
    """Test that camera action works with multiple title variations"""
    slides = [
        {"text": "First slide text", "style": "normal", "is_bold": False}
    ]
    
    # Use a variation of the title
    parsed = {
        "title": "Prayers",  # Variation of "Prayer"
        "text_chunks": ["First slide text"],
        "item_id": "12345"
    }
    
    camera_config = {
        "enabled": True,
        "device": {
            "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
            "name": "Companion"
        },
        "command": {
            "format": "CC x",
            "replacement_range": {"start": 3, "end": 4}
        },
        "mappings": [
            {"titles": ["Prayer", "Prayers", "Prayer of Confession"], "command": "CC 9/3/0"}
        ]
    }
    
    filename = tmp_path / "test_output_variation.pro"
    
    make_pro.make_pro_for_items(
        slides,
        parsed,
        str(filename.name),
        plan_date="2026-03-30",
        camera_config=camera_config
    )
    
    # Read the generated .pro file
    output_dir = make_pro.SLIDES_OUTPUTS_DIR / "2026-03-30"
    output_file = output_dir / filename.name
    
    presentation = presentation_pb2.Presentation()
    with open(output_file, 'rb') as f:
        presentation.ParseFromString(f.read())
    
    # Verify camera action was inserted
    first_cue = presentation.cues[0]
    assert len(first_cue.actions) >= 2, "Should have camera + slide actions"
    camera_action = first_cue.actions[0]
    assert camera_action.type == action_pb2.Action.ACTION_TYPE_COMMUNICATION
    assert camera_action.communication.commands[0].value == "CC 9/3/0"


def test_camera_action_not_inserted_when_no_config(tmp_path):
    """Test that no camera action is inserted when camera_config is None"""
    slides = [
        {"text": "First slide text", "style": "normal", "is_bold": False}
    ]
    
    parsed = {
        "title": "Prayer",
        "text_chunks": ["First slide text"],
        "item_id": "12345"
    }
    
    filename = tmp_path / "test_output_no_config.pro"
    
    # Call without camera_config
    make_pro.make_pro_for_items(
        slides,
        parsed,
        str(filename.name),
        plan_date="2026-03-30",
        camera_config=None
    )
    
    # Read the generated .pro file
    output_dir = make_pro.SLIDES_OUTPUTS_DIR / "2026-03-30"
    output_file = output_dir / filename.name
    
    presentation = presentation_pb2.Presentation()
    with open(output_file, 'rb') as f:
        presentation.ParseFromString(f.read())
    
    # Should only have slide action
    first_cue = presentation.cues[0]
    assert len(first_cue.actions) == 1, "Should only have slide action when no camera config"
