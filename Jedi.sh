#!/bin/bash

# Check if Python 3.9 is installed
if ! python3.9 --version &>/dev/null; then
    echo "Python 3.9 is not installed. Installing Python 3.9..."
    sudo apt update
    sudo apt install -y python3.9
else
    echo "Python 3.9 is already installed."
fi

# Check if pip for Python 3.9 is installed
if ! python3.9 -m pip --version &>/dev/null; then
    echo "Pip is not installed. Installing pip..."
    python3.9 -m ensurepip --upgrade
else
    echo "Pip is already installed."
fi

# Install requirements from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    python3.9 -m pip install -r requirements.txt
else
    echo "requirements.txt not found."
fi

# Run the Python script (replace 'your_game.py' with the actual script name)
echo "Running Python script..."
python3.9 jedi.py

# Close the terminal (this works for most terminals)
exit
