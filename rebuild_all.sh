#!/bin/bash

# GPT-Jobhunter Embedding Rebuilding Script
# This script provides a convenient way to rebuild all embeddings and recalculate
# similarities for all resumes in the database.

echo "====== GPT-JOBHUNTER EMBEDDING REBUILDER ======"
echo "This script will rebuild all job embeddings and recalculate resume similarities."

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY environment variable is not set."
    echo "Please set your OpenAI API key first with:"
    echo "export OPENAI_API_KEY=your-openai-api-key"
    exit 1
fi

# Show the masked API key for verification
MASKED_KEY="${OPENAI_API_KEY:0:4}...${OPENAI_API_KEY: -4}"
echo "✅ Using OpenAI API key: $MASKED_KEY"

# Confirm before proceeding
echo ""
echo "⚠️ WARNING: This process may use a significant amount of your OpenAI API quota."
echo "Depending on the number of jobs and resumes, costs could be substantial."
read -p "Do you want to proceed? (y/n): " choice
if [[ ! "$choice" =~ ^[Yy]$ ]]; then
    echo "Operation cancelled."
    exit 0
fi

# Run the rebuild script
echo ""
echo "🔄 Starting embedding rebuilding process..."
echo "============================================="

if command -v poetry &> /dev/null; then
    # If poetry is available, use it
    poetry run python -m jobhunter.rebuild_embeddings
else
    # Fall back to regular python if poetry isn't installed
    python -m jobhunter.rebuild_embeddings
fi

echo ""
echo "Process completed!"
echo "If you're running the Streamlit app, you may need to restart it for changes to take effect." 