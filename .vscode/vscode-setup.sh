#!/bin/bash
# VS Code Setup Script

echo "Setting up VS Code configuration..."

# Install recommended extensions
code --install-extension ms-python.python
code --install-extension ms-vscode.vscode-typescript-next
code --install-extension esbenp.prettier-vscode
code --install-extension dbaeumer.vscode-eslint

echo "VS Code setup completed!"
