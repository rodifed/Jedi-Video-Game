#!/bin/bash

# Check if Python 3.9 is installed
if ! python3.9 --version &>/dev/null; then
    echo "Python 3.9 is not installed."
    read -p "Do you want to install Python 3.9? (y/n): " install_python

    if [[ "$install_python" =~ ^[Yy]$ ]]; then
        echo "Installing Python 3.9..."
        sudo apt update
        sudo apt install -y python3.9
    else
        echo "Python 3.9 is required to run this game. Exiting."
        exit 1
    fi
else
    echo "Python 3.9 is already installed."
fi

# Check if pip for Python 3.9 is installed
if ! python3.9 -m pip --version &>/dev/null; then
    echo "Pip is not installed for Python 3.9. Installing pip..."
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

# Run the Python script
echo "Running Python script..."
python3.9 Jedi.py

# Close the terminal (this works for most terminals)
exit
