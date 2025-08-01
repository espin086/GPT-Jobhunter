#!/usr/bin/env python3
"""
Script to generate OpenAPI JSON specification from FastAPI app.
This script imports the FastAPI app and exports its OpenAPI schema to openapi.json.
"""

import json
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from jobhunter.backend.api import app
    
    def generate_openapi_spec():
        """Generate OpenAPI specification and save to openapi.json"""
        
        # Get the OpenAPI schema from FastAPI
        openapi_schema = app.openapi()
        
        # Create output path (in project root)
        output_file = project_root / "openapi.json"
        
        # Write the schema to file with pretty formatting
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        
        print(f"✅ OpenAPI specification generated successfully: {output_file}")
        print(f"📊 Found {len(openapi_schema.get('paths', {}))} endpoints")
        print(f"🏷️  API Title: {openapi_schema.get('info', {}).get('title', 'N/A')}")
        print(f"📖 API Version: {openapi_schema.get('info', {}).get('version', 'N/A')}")
        
        return output_file

    if __name__ == "__main__":
        try:
            generate_openapi_spec()
        except Exception as e:
            print(f"❌ Error generating OpenAPI spec: {e}")
            sys.exit(1)
            
except ImportError as e:
    print(f"❌ Failed to import FastAPI app: {e}")
    print("Make sure you have installed all dependencies with 'poetry install' or 'pip install -r requirements.txt'")
    sys.exit(1) 