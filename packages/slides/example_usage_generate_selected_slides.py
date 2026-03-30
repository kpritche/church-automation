"""
Example usage of generate_selected_slides() function.

This demonstrates how to generate slides for specific selected plans,
similar to the bulletins generate_selected_bulletins() pattern.
"""

from slides_app.make_pro import generate_selected_slides

def example_usage():
    """Example: Generate slides for specific selected plans."""
    
    # Define selected plans - these would come from the web UI selection
    selected_plans = [
        {
            "service_type_id": "123456",  # From PCO service type
            "plan_id": "789012",          # From PCO plan
            "plan_date": "2026-04-05",    # ISO date format
            "service_name": "SundayService"  # Human-readable name
        },
        {
            "service_type_id": "123456",
            "plan_id": "789013",
            "plan_date": "2026-04-12",
            "service_name": "SundayService"
        }
    ]
    
    # Generate slides for selected plans
    # This will:
    # 1. Load config from slides_config.json
    # 2. Initialize PCO client
    # 3. Process each plan's items
    # 4. Generate .pro files
    # 5. Upload to PCO
    # 6. Return list of uploaded file names
    uploaded_files = generate_selected_slides(selected_plans)
    
    print(f"Generated and uploaded {len(uploaded_files)} slide files:")
    for filename in uploaded_files:
        print(f"  - {filename}")

if __name__ == "__main__":
    # NOTE: This requires:
    # 1. PCO_CLIENT_ID and PCO_SECRET environment variables
    # 2. Valid service_type_id and plan_id values
    # 3. slides_config.json configuration file
    
    # Uncomment to run (with valid credentials and plan IDs):
    # example_usage()
    
    print("See example_usage() function for usage pattern")
    print("This function follows the same pattern as bulletins' generate_selected_bulletins()")
