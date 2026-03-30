"""
Communication actions module for ProPresenter camera control via BitFocus Companion.

This module handles:
- Loading camera control configuration
- Matching PCO item titles to camera commands
- Creating ProPresenter communication action protobuf structures
"""
import sys
import uuid as uuid_module
from pathlib import Path
from typing import Optional, Dict, List, Any

# Ensure protobuf modules are importable
SLIDES_DIR = Path(__file__).resolve().parent.parent
PROTO_DIR = SLIDES_DIR / "ProPresenter7_Proto" / "generated"
if PROTO_DIR.exists() and str(PROTO_DIR) not in sys.path:
    sys.path.insert(0, str(PROTO_DIR))

# Import protobuf modules
import action_pb2
import basicTypes_pb2


def load_camera_control_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Load camera control configuration from slides config.
    
    Args:
        config: The slides configuration dictionary
    
    Returns:
        Camera control config dict or None if disabled/not present
    """
    camera_config = config.get("camera_control", {})
    
    if not camera_config.get("enabled", False):
        return None
    
    return camera_config


def get_camera_command_for_item(
    title: str, 
    camera_config: Dict[str, Any],
    service_type_id: Optional[int] = None,
    is_song: bool = False
) -> Optional[str]:
    """
    Match a PCO item title to a camera command.
    
    Supports multiple title variations per command mapping.
    Supports service-specific "any_song" mappings.
    Matching is case-insensitive and strips whitespace.
    
    Args:
        title: The PCO item title
        camera_config: Camera control configuration
        service_type_id: The service type ID (optional)
        is_song: Whether the item is a song (optional)
    
    Returns:
        Command string (e.g., "CC 9/1/0") or None if no match
    """
    if not camera_config:
        return None
    
    mappings = camera_config.get("mappings", [])
    title_normalized = title.strip().lower()
    
    for mapping in mappings:
        match_type = mapping.get("match_type", "exact")
        
        # Handle "any_song" match type
        if match_type == "any_song":
            # Only match if this is actually a song
            if not is_song:
                continue
            
            # Check if service_type_id matches (if specified)
            mapping_service_ids = mapping.get("service_type_ids", [])
            if mapping_service_ids and service_type_id:
                if service_type_id in mapping_service_ids:
                    return mapping.get("command")
            elif not mapping_service_ids:
                # No service restriction, matches all songs
                return mapping.get("command")
            continue
        
        # Handle exact title matching (default)
        titles = mapping.get("titles", [])
        for variant in titles:
            if variant.strip().lower() == title_normalized:
                return mapping.get("command")
    
    return None


def create_communication_action(command: str, camera_config: Dict[str, Any]) -> action_pb2.Action:
    """
    Create a ProPresenter communication action protobuf.
    
    Args:
        command: The command string (e.g., "CC 9/1/0")
        camera_config: Camera control configuration
    
    Returns:
        Configured Action protobuf object
    """
    # Create new action
    action = action_pb2.Action()
    
    # Set action UUID
    action_uuid = uuid_module.uuid4()
    action.uuid.string = str(action_uuid).upper()
    
    # Set action properties
    action.isEnabled = True
    action.type = action_pb2.Action.ACTION_TYPE_COMMUNICATION
    action.name = "Custom Control"
    
    # Get device info from config
    device = camera_config.get("device", {})
    device_uuid = device.get("uuid", "")
    device_name = device.get("name", "Companion")
    
    # Set device identification
    action.communication.device_identification.parameter_uuid.string = device_uuid
    action.communication.device_identification.parameter_name = device_name
    
    # Get command format from config
    command_config = camera_config.get("command", {})
    format_str = command_config.get("format", "CC x")
    replacement_range = command_config.get("replacement_range", {"start": 3, "end": 4})
    
    # Set communication properties
    action.communication.format = format_str
    action.communication.description = "Executes camera control command."
    
    # Add command with replacement range
    cmd = action.communication.commands.add()
    cmd.name = "Custom Control"
    cmd.value = command
    cmd.replacement_range.start = replacement_range["start"]
    cmd.replacement_range.end = replacement_range["end"]
    
    return action
