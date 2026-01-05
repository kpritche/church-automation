#!/usr/bin/env python3
"""
Improved .probundle decoder that reads from central directory for accurate file sizes.
"""

import os
import sys
import struct
import json
from pathlib import Path
from google.protobuf.json_format import MessageToJson

# Add the generated protobuf modules to the path
proto_gen_path = os.path.join(os.path.dirname(__file__), 'ProPresenter7_Proto', 'generated')
sys.path.insert(0, proto_gen_path)

import presentation_pb2
try:
    from playlist_pb2 import PlaylistDocument
except ImportError:
    PlaylistDocument = None


def parse_zip64_extra(extra_data):
    """Parse ZIP64 extra field (tag 0x0001)."""
    if len(extra_data) < 4:
        return None, None
    
    header_id = struct.unpack('<H', extra_data[0:2])[0]
    data_size = struct.unpack('<H', extra_data[2:4])[0]
    
    if header_id != 0x0001:
        return None, None
    
    sizes = {}
    offset = 4
    
    # Read available ZIP64 fields
    if data_size >= 8 and offset + 8 <= len(extra_data):
        sizes['usize'] = struct.unpack('<Q', extra_data[offset:offset+8])[0]
        offset += 8
    
    if data_size >= 16 and offset + 8 <= len(extra_data):
        sizes['csize'] = struct.unpack('<Q', extra_data[offset:offset+8])[0]
        offset += 8
    
    return sizes.get('usize'), sizes.get('csize')


def extract_probundle_manual(bundle_path, extract_to=None):
    """
    Extract .probundle by reading ZIP local headers with ZIP64 support.
    """
    bundle_path = Path(bundle_path)
    
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")
    
    if extract_to is None:
        extract_to = bundle_path.parent / f"{bundle_path.stem}_extracted"
    else:
        extract_to = Path(extract_to)
    
    extract_to.mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting {bundle_path.name} to {extract_to}")
    
    with open(bundle_path, 'rb') as f:
        data = f.read()
    
    # Find all local file headers
    offset = 0
    extracted = 0
    
    while True:
        idx = data.find(b'PK\x03\x04', offset)
        if idx == -1:
            break
        
        # Parse local file header
        lfn_len = struct.unpack('<H', data[idx+26:idx+28])[0]
        extra_len = struct.unpack('<H', data[idx+28:idx+30])[0]
        
        csize = struct.unpack('<I', data[idx+18:idx+22])[0]
        usize = struct.unpack('<I', data[idx+22:idx+26])[0]
        
        filename = data[idx+30:idx+30+lfn_len].decode('utf-8', errors='ignore')
        
        # Sanitize filename
        filename = filename.lstrip('/')
        if filename.startswith('Users/'):
            parts = filename.split('/')
            filename = parts[-1]
        
        # Check for ZIP64 extra field
        if extra_len > 0 and (csize == 0xFFFFFFFF or usize == 0xFFFFFFFF):
            extra_offset = idx + 30 + lfn_len
            extra_data = data[extra_offset:extra_offset+extra_len]
            z64_usize, z64_csize = parse_zip64_extra(extra_data)
            if z64_usize is not None:
                usize = z64_usize
            if z64_csize is not None:
                csize = z64_csize
        
        if not filename or filename.endswith('/'):
            offset = idx + 4
            continue
        
        print(f"  {filename} ({usize} bytes)")
        
        # Calculate file data offset
        file_data_offset = idx + 30 + lfn_len + extra_len
        
        # Extract file if we can read it
        if file_data_offset + usize <= len(data):
            file_data = data[file_data_offset:file_data_offset+usize]
            
            out_path = extract_to / filename
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(out_path, 'wb') as out_f:
                out_f.write(file_data)
            
            extracted += 1
            print(f"    ✓ Extracted")
        else:
            print(f"    ✗ Cannot extract (size mismatch)")
        
        offset = idx + 4
    
    print(f"  Successfully extracted {extracted} files\n")
    return extract_to


def find_pro_files(directory):
    """Find all .pro files in a directory."""
    return list(Path(directory).glob('**/*.pro'))


def decode_pro_file(pro_file_path, output_format='json'):
    """Attempt to decode a .pro file by trying different message types."""
    pro_file_path = Path(pro_file_path)
    
    if not pro_file_path.exists():
        raise FileNotFoundError(f"Pro file not found: {pro_file_path}")
    
    with open(pro_file_path, 'rb') as f:
        binary_data = f.read()
    
    message_types = [
        ('Presentation', presentation_pb2.Presentation),
    ]
    
    if PlaylistDocument:
        message_types.append(('PlaylistDocument', PlaylistDocument))
    
    for type_name, message_class in message_types:
        try:
            message = message_class()
            message.ParseFromString(binary_data)
            
            if message.ByteSize() > 0:
                print(f"  ✓ Successfully decoded as: {type_name}")
                
                try:
                    if output_format == 'json':
                        decoded_str = MessageToJson(message, indent=2)
                    else:
                        decoded_str = str(message)
                    
                    return type_name, message, decoded_str
                except Exception as e:
                    print(f"  Warning: Could not convert to JSON: {e}")
                    return type_name, message, str(message)[:2000]
        except Exception as e:
            print(f"  Could not parse as {type_name}: {e}")
            continue
    
    print(f"  Could not decode with any known message type")
    return None, None, "Could not decode - unknown message type"


def decode_probundle(bundle_path, extract_to=None, output_format='json', output_file=None):
    """Full workflow: extract .probundle and decode all .pro files inside."""
    
    # Extract the bundle
    extract_dir = extract_probundle_manual(bundle_path, extract_to)
    
    # Find all .pro files
    pro_files = find_pro_files(extract_dir)
    print(f"Found {len(pro_files)} .pro file(s)\n")
    
    results = {
        'bundle': str(bundle_path),
        'extracted_to': str(extract_dir),
        'pro_files': []
    }
    
    # Decode each .pro file
    for pro_file in sorted(pro_files):
        print(f"Decoding: {pro_file.name}")
        msg_type, message, decoded = decode_pro_file(pro_file, output_format)
        
        results['pro_files'].append({
            'filename': pro_file.name,
            'path': str(pro_file),
            'message_type': msg_type,
            'decoded': decoded if output_format == 'json' else decoded[:500] + '...' if len(decoded) > 500 else decoded
        })
        
        print(f"Content preview:\n{decoded[:800]}")
        if len(decoded) > 800:
            print("... (truncated)\n")
    
    # Write to output file if specified
    if output_file:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            if output_format == 'json':
                json.dump(results, f, indent=2)
            else:
                f.write(json.dumps(results, indent=2))
        
        print(f"Results saved to: {output_file}")
    
    return results


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Decode ProPresenter .probundle files')
    parser.add_argument('bundle', help='Path to .probundle file')
    parser.add_argument('-x', '--extract-to', help='Directory to extract to')
    parser.add_argument('-f', '--format', choices=['json', 'text'], default='json', help='Output format')
    parser.add_argument('-o', '--output', help='Output file to save results')
    
    args = parser.parse_args()
    
    try:
        results = decode_probundle(
            args.bundle,
            extract_to=args.extract_to,
            output_format=args.format,
            output_file=args.output
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
