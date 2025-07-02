#!/bin/bash
# Quick format script to run Black and isort before committing

echo "🎨 Running Black formatter..."
black . --line-length=88

echo "📦 Running isort..."
isort . --profile black --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width=88

echo "✅ Formatting complete! Ready to commit."
