"""Server runner for web UI"""

import uvicorn


def run():
    """Run the web UI server"""
    print("✓ Starting Church Automation Web UI on http://localhost:8080")
    uvicorn.run(
        "web_ui_app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False
    )


if __name__ == "__main__":
    run()
