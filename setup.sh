#!/bin/bash
# Setup script for the trading bot

echo "=================================="
echo "Trading Bot Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
echo ""
if [ -f ".env" ]; then
    echo ".env file already exists. Skipping..."
else
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠ IMPORTANT: Edit .env file and add your API keys!"
    echo "  1. Get Alpaca API keys from: https://app.alpaca.markets/paper/dashboard/overview"
    echo "  2. Get OpenAI API key from: https://platform.openai.com/api-keys"
fi

# Create logs directory
echo ""
if [ -d "logs" ]; then
    echo "Logs directory already exists. Skipping..."
else
    mkdir -p logs
    echo "✓ Logs directory created"
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env file and add your API keys"
echo "  2. Activate the virtual environment: source venv/bin/activate"
echo "  3. Test the Alpaca connection: python test_alpaca.py"
echo "  4. Run the bot: python main.py"
echo ""
