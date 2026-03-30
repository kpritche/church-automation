# Example: Using service-specific any_song camera mappings

## Problem
You have different camera presets for songs in different services, but song titles change every week.

## Solution
Use the `match_type: "any_song"` mapping with `service_type_ids` to map ALL songs in specific services to camera commands.

## Configuration Example

```json
{
  "camera_control": {
    "enabled": true,
    "device": {
      "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
      "name": "Companion"
    },
    "command": {
      "format": "CC x",
      "replacement_range": {"start": 3, "end": 4}
    },
    "mappings": [
      // Exact title mappings (checked first)
      {"titles": ["Prayer", "Prayers"], "command": "CC 9/3/0"},
      {"titles": ["Scripture Reading"], "command": "CC 9/2/1"},
      
      // Service-specific any_song mappings
      {
        "match_type": "any_song",
        "service_type_ids": [1041663],
        "command": "CC 9/4/0"
      },
      {
        "match_type": "any_song",
        "service_type_ids": [78127, 1145553],
        "command": "CC 9/5/0"
      }
    ]
  }
}
```

## How it works

1. **Exact mappings are checked first**: If a song title exactly matches an entry in a `titles` array, that command is used
2. **Then any_song mappings are checked**: If no exact match, and the item is a song, check if it's in a service with an `any_song` mapping
3. **Service filtering**: `any_song` mappings only apply to songs in the specified `service_type_ids`

## Mapping Priority

Given this configuration:
```json
"mappings": [
  {"titles": ["Special Hymn"], "command": "CC 9/1/0"},
  {"match_type": "any_song", "service_type_ids": [1041663], "command": "CC 9/4/0"}
]
```

- Song titled "Special Hymn" in service 1041663 → CC 9/1/0 (exact match wins)
- Song titled "Amazing Grace" in service 1041663 → CC 9/4/0 (any_song fallback)
- Song titled "Special Hymn" in service 78127 → No match (different service)

## To configure for your services:

Replace the "First Up Song" and "Celebrate Song" mappings in your slides_config.json:

**Before:**
```json
{"titles": ["First Up Song"], "command": "CC 9/4/0"},
{"titles": ["Celebrate Song"], "command": "CC 9/5/0"}
```

**After:**
```json
{
  "match_type": "any_song",
  "service_type_ids": [1041663],  // Replace with your service ID
  "command": "CC 9/4/0"
},
{
  "match_type": "any_song",
  "service_type_ids": [78127, 1145553],  // Replace with your service IDs
  "command": "CC 9/5/0"
}
```

## Multiple services can share the same camera preset:

```json
{
  "match_type": "any_song",
  "service_type_ids": [78127, 1145553],  // Both use same camera command
  "command": "CC 9/5/0"
}
```

## Global any_song (no service restriction):

```json
{
  "match_type": "any_song",
  // No service_type_ids = applies to songs in ALL services
  "command": "CC 9/0/0"
}
```
