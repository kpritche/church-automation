# Church Automation - Slides Generator

Generate ProPresenter `.pro` slide files from Planning Center liturgy items.

## Installation

```bash
# Install shared utilities first
pip install -e ../shared

# Install slides package
pip install -e .
```

## Setup

### 1. Configure Environment

Add Planning Center credentials to your `.env` file:
```bash
PCO_CLIENT_ID=your_client_id
PCO_SECRET=your_secret
```

### 2. Configure Service Types

Create or edit `slides_config.json`:
```json
{
  "service_type_ids": [1041663, 78127]
}
```

Find your service type IDs in Planning Center:
- Navigate to Services → Service Types
- The ID is in the URL: `https://services.planningcenteronline.com/service_types/[ID]`

### 3. Templates

ProPresenter templates are included in `templates/`:
- `white_template.pro` - White background slides
- `yellow_template.pro` - Yellow background slides
- `blank_template.pro` - Blank slides for special content

You can add your own templates by exporting from ProPresenter.

## Usage

### Command Line

```bash
# Run the generator
make-slides

# Or use module syntax
python -m slides_app.make_pro
```

### Output

Generated files are saved to `output/YYYY-MM-DD/YYYY-MM-DD-ServiceName-ItemTitle.pro`

The `.pro` files are automatically uploaded as attachments to their corresponding Planning Center items.

## Features

- **Planning Center Integration** - Fetches service plans for the next 7 days
- **Smart Text Parsing** - Breaks long text into appropriately-sized slide chunks
- **Template Cloning** - Duplicates existing `.pro` templates and replaces text
- **RTF Text Formatting** - Properly encodes text with formatting preservation
- **Scripture References** - Parses and formats Bible verse references
- **Automatic Upload** - Attaches generated files to Planning Center items
- **Color-Coded Templates** - Different templates for different item types

## How It Works

### 1. Fetch Service Plans

The generator connects to Planning Center and retrieves all service plans scheduled within the next 7 days for configured service types.

### 2. Parse Items

Each service item is parsed to extract:
- Title
- Description  
- HTML details
- Scripture references
- Item type (determines template)

### 3. Text Chunking

Long text is intelligently split into slides:
- Respects paragraph boundaries
- Maintains proper line breaks
- Ensures text fits within slide dimensions

### 4. Generate `.pro` Files

For each item:
1. Load the appropriate template (white/yellow/blank)
2. Clone the template using protobuf deep copy
3. Replace placeholder text with actual content
4. Update text colors and formatting
5. Serialize to `.pro` file format

### 5. Upload to Planning Center

Generated files are:
1. Uploaded to Planning Center media library
2. Attached to their corresponding service items
3. Available for use in ProPresenter

## ProPresenter Protocol Buffers

`.pro` files are serialized Google Protocol Buffer messages. The protobuf definitions are in `ProPresenter7_Proto/`.

### Key Protobuf Modules

- `presentation_pb2` - Main presentation structure
- `cue_pb2` - Cue and timeline data
- `slide_pb2` - Individual slide definitions
- `graphicsData_pb2` - Text and element data
- `action_pb2` - Slide actions and transitions

### Decoding `.pro` Files

```bash
protoc -I="ProPresenter7_Proto/Proto19beta" \
  --decode rv.data.Presentation propresenter.proto \
  < "output.pro" > decoded.txt
```

## Item Type Mapping

| Item Title Pattern | Template Used |
|-------------------|---------------|
| Contains "prayer" | White template |
| Contains "scripture" | Yellow template |
| Contains "centering" | Yellow template |
| Default | White template |

## Configuration

### Text Limits

Configured in `slide_utils.py`:
- Maximum characters per slide
- Line wrap behavior
- Font size considerations

### Template Selection

Edit `make_pro.py` to customize template selection logic based on item titles or types.

## Dependencies

- `pypco` - Planning Center Online API
- `protobuf` - Protocol buffer serialization
- `requests` - HTTP client for uploads
- `church-automation-shared` - Common utilities

## Included Libraries

### ProPresenter7_Proto

Forked from [greyshirtguy/ProPresenter7-Proto](https://github.com/greyshirtguy/ProPresenter7-Proto) - Reverse-engineered ProPresenter 7 protocol buffer definitions.

See `ProPresenter7_Proto/README.md` for details on the protobuf schema and how to work with `.pro` files programmatically.
