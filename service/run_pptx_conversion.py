import os
import sys
from pptx_converter import PptxToProConverter

def main():
    # Example usage: python run_pptx_conversion.py "my_presentation.pptx"
    
    if len(sys.argv) < 2:
        print("Usage: python run_pptx_conversion.py <path_to_pptx>")
        # Default for testing if no arg provided
        input_file = "example.pptx"
    else:
        input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        return

    print(f"Starting conversion for: {input_file}")
    
    converter = PptxToProConverter(input_file)
    try:
        output_bundle = converter.convert()
        print("-" * 30)
        print("Conversion Complete!")
        print(f"Bundle saved to: {output_bundle}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()