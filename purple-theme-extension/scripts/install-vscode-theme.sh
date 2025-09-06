#!/bin/bash

# VS Code Purple Theme Installation Script
# This script installs the Purple Development Theme for VS Code

set -e

# Colors for output
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${PURPLE}🎨 Purple Development Theme Installer${NC}"
echo "=================================================="

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if VS Code is installed
check_vscode() {
    if command -v code &> /dev/null; then
        print_status "VS Code CLI found"
        return 0
    elif [ -d "/Applications/Visual Studio Code.app" ]; then
        print_status "VS Code application found"
        # Add VS Code CLI to PATH if not already there
        if ! command -v code &> /dev/null; then
            print_warning "VS Code CLI not in PATH. You may need to install it via Command Palette > 'Shell Command: Install code command in PATH'"
        fi
        return 0
    else
        print_error "VS Code not found. Please install VS Code first."
        return 1
    fi
}

# Get VS Code extensions directory
get_vscode_extensions_dir() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "$HOME/.vscode/extensions"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "$HOME/.vscode/extensions"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "$APPDATA/Code/User/extensions"
    else
        echo "$HOME/.vscode/extensions"
    fi
}

# Get VS Code settings directory
get_vscode_settings_dir() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "$HOME/Library/Application Support/Code/User"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "$HOME/.config/Code/User"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "$APPDATA/Code/User"
    else
        echo "$HOME/.config/Code/User"
    fi
}

# Install theme extension
install_theme() {
    local extensions_dir=$(get_vscode_extensions_dir)
    local theme_extension_dir="$extensions_dir/purple-theme-dev.purple-development-theme-1.0.0"
    
    echo "Installing theme to: $theme_extension_dir"
    
    # Create extensions directory if it doesn't exist
    mkdir -p "$extensions_dir"
    
    # Remove existing installation if present
    if [ -d "$theme_extension_dir" ]; then
        print_warning "Removing existing theme installation"
        rm -rf "$theme_extension_dir"
    fi
    
    # Create theme extension directory
    mkdir -p "$theme_extension_dir"
    mkdir -p "$theme_extension_dir/themes"
    
    # Copy theme files
    cp "$THEME_DIR/package.json" "$theme_extension_dir/"
    cp "$THEME_DIR/themes/purple-theme.json" "$theme_extension_dir/themes/"
    
    # Create README for the extension
    cat > "$theme_extension_dir/README.md" << 'EOF'
# Purple Development Theme

A comprehensive purple color theme for VS Code with dark purple backgrounds and carefully crafted syntax highlighting.

## Features

- Dark purple background with excellent contrast
- Carefully selected purple color palette
- Optimized syntax highlighting for multiple languages
- Consistent theming across all VS Code UI elements

## Color Palette

- Primary Background: #1A0D26 (deep purple)
- Secondary Background: #2D1B3D (medium purple)
- Sidebar: #3D2A4F (lighter purple)
- Text: #E6E6FA (lavender)
- Keywords: #9370DB (medium slate blue)
- Strings: #DDA0DD (plum)
- Comments: #8A2BE2 (blue violet)
- Functions: #BA55D3 (medium orchid)
- Variables: #DA70D6 (orchid)
- Accent: #8B008B (dark magenta)
EOF
    
    print_status "Theme files copied successfully"
}

# Update VS Code settings to activate theme
activate_theme() {
    local settings_dir=$(get_vscode_settings_dir)
    local settings_file="$settings_dir/settings.json"
    
    echo "Updating VS Code settings: $settings_file"
    
    # Create settings directory if it doesn't exist
    mkdir -p "$settings_dir"
    
    # Backup existing settings if they exist
    if [ -f "$settings_file" ]; then
        cp "$settings_file" "$settings_file.backup.$(date +%Y%m%d_%H%M%S)"
        print_status "Existing settings backed up"
    fi
    
    # Read existing settings or create empty object
    local existing_settings="{}"
    if [ -f "$settings_file" ]; then
        existing_settings=$(cat "$settings_file")
    fi
    
    # Use Python to merge settings (more reliable than shell JSON manipulation)
    python3 -c "
import json
import sys

try:
    # Read existing settings
    existing = json.loads('$existing_settings')
except:
    existing = {}

# Update theme settings
existing['workbench.colorTheme'] = 'Purple Development Theme'
existing['workbench.preferredDarkColorTheme'] = 'Purple Development Theme'

# Write updated settings
with open('$settings_file', 'w') as f:
    json.dump(existing, f, indent=2)

print('Settings updated successfully')
" 2>/dev/null || {
        # Fallback if Python is not available
        print_warning "Python not available, using manual settings update"
        
        # Simple JSON merge for the theme setting
        if [ -f "$settings_file" ] && [ -s "$settings_file" ]; then
            # Remove the last closing brace and add our settings
            sed -i.bak '$s/}$//' "$settings_file"
            echo '  "workbench.colorTheme": "Purple Development Theme",' >> "$settings_file"
            echo '  "workbench.preferredDarkColorTheme": "Purple Development Theme"' >> "$settings_file"
            echo '}' >> "$settings_file"
        else
            # Create new settings file
            cat > "$settings_file" << 'EOF'
{
  "workbench.colorTheme": "Purple Development Theme",
  "workbench.preferredDarkColorTheme": "Purple Development Theme"
}
EOF
        fi
    }
    
    print_status "VS Code settings updated to use Purple Development Theme"
}

# Reload VS Code extensions
reload_vscode() {
    if command -v code &> /dev/null; then
        print_status "Reloading VS Code extensions..."
        # The --list-extensions command will trigger extension reload
        code --list-extensions > /dev/null 2>&1 || true
    else
        print_warning "Please restart VS Code to see the new theme"
    fi
}

# Main installation process
main() {
    echo "Starting VS Code Purple Theme installation..."
    echo
    
    # Check prerequisites
    if ! check_vscode; then
        exit 1
    fi
    
    # Install theme
    echo
    echo "Installing theme extension..."
    install_theme
    
    # Activate theme
    echo
    echo "Activating theme in VS Code settings..."
    activate_theme
    
    # Reload extensions
    echo
    reload_vscode
    
    echo
    echo -e "${GREEN}🎉 Installation completed successfully!${NC}"
    echo
    echo "The Purple Development Theme has been installed and activated."
    echo "If VS Code is currently running, please restart it to see the changes."
    echo
    echo "To manually select the theme:"
    echo "1. Open VS Code"
    echo "2. Press Cmd+Shift+P (or Ctrl+Shift+P on Linux/Windows)"
    echo "3. Type 'Preferences: Color Theme'"
    echo "4. Select 'Purple Development Theme'"
    echo
}

# Run main function
main "$@"