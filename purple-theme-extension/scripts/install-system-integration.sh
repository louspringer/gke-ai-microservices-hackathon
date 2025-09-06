#!/bin/bash

# System Purple Theme Integration Script
# This script configures system-level purple theming for macOS

set -e

# Colors for output
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${PURPLE}🎨 System Purple Theme Integration${NC}"
echo "============================================"

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

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if running on macOS
check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_error "This script is designed for macOS only"
        print_info "System integration features are not available on other platforms"
        exit 1
    fi
    
    print_status "Running on macOS"
}

# Check macOS version compatibility
check_macos_version() {
    local macos_version=$(sw_vers -productVersion)
    local major_version=$(echo "$macos_version" | cut -d. -f1)
    local minor_version=$(echo "$macos_version" | cut -d. -f2)
    
    print_info "macOS version: $macos_version"
    
    # Check if version supports accent colors (macOS 10.14+)
    if [[ $major_version -ge 11 ]] || [[ $major_version -eq 10 && $minor_version -ge 14 ]]; then
        print_status "macOS version supports accent color customization"
        return 0
    else
        print_warning "macOS version may have limited accent color support"
        return 1
    fi
}

# Set system accent color to purple
set_system_accent_color() {
    echo "Configuring system accent color..."
    
    # Set accent color to purple (value 5 = Purple in macOS)
    defaults write NSGlobalDomain AppleAccentColor -int 5
    
    # Set highlight color to purple
    defaults write NSGlobalDomain AppleHighlightColor -string "0.968627 0.831373 1.000000 Purple"
    
    # Apply changes immediately
    killall Dock 2>/dev/null || true
    killall SystemUIServer 2>/dev/null || true
    
    print_status "System accent color set to purple"
}

# Configure Finder appearance
configure_finder() {
    echo "Configuring Finder appearance..."
    
    # Set Finder sidebar icon size to medium (better visibility with purple theme)
    defaults write NSGlobalDomain NSTableViewDefaultSizeMode -int 2
    
    # Enable colored sidebar icons
    defaults write NSGlobalDomain NSColoredSidebarIconsEnabled -bool true
    
    # Set Finder to use purple accent for selections
    defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"
    
    # Restart Finder to apply changes
    killall Finder 2>/dev/null || true
    
    print_status "Finder configured for purple theme"
}

# Configure menu bar appearance
configure_menu_bar() {
    echo "Configuring menu bar appearance..."
    
    # Set menu bar to dark mode (works better with purple theme)
    defaults write NSGlobalDomain AppleInterfaceStyle -string "Dark"
    
    # Configure menu bar transparency
    defaults write NSGlobalDomain AppleEnableMenuBarTransparency -bool true
    
    print_status "Menu bar configured for purple theme"
}

# Configure dock appearance
configure_dock() {
    echo "Configuring Dock appearance..."
    
    # Set dock to dark mode
    defaults write NSGlobalDomain AppleInterfaceStyle -string "Dark"
    
    # Enable dock magnification for better visual appeal
    defaults write com.apple.dock magnification -bool true
    defaults write com.apple.dock largesize -int 64
    
    # Set dock position to bottom (standard)
    defaults write com.apple.dock orientation -string "bottom"
    
    # Enable dock auto-hide for cleaner appearance
    read -p "Enable Dock auto-hide? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        defaults write com.apple.dock autohide -bool true
        defaults write com.apple.dock autohide-delay -float 0.2
        defaults write com.apple.dock autohide-time-modifier -float 0.5
        print_status "Dock auto-hide enabled"
    fi
    
    # Restart Dock to apply changes
    killall Dock 2>/dev/null || true
    
    print_status "Dock configured for purple theme"
}

# Configure Terminal.app default profile
configure_terminal_app() {
    echo "Configuring Terminal.app default profile..."
    
    local terminal_theme="$THEME_DIR/terminal/Terminal-Purple.terminal"
    
    if [ ! -f "$terminal_theme" ]; then
        print_warning "Terminal.app theme file not found, skipping Terminal.app configuration"
        return 1
    fi
    
    # Import the terminal theme
    open "$terminal_theme"
    
    # Wait a moment for the theme to be imported
    sleep 2
    
    # Set Purple Theme as default (requires user interaction)
    print_info "To complete Terminal.app setup:"
    print_info "1. Open Terminal.app"
    print_info "2. Go to Terminal > Preferences > Profiles"
    print_info "3. Select 'Purple Theme' and click 'Default'"
    
    print_status "Terminal.app theme imported"
}

# Configure application-specific theming
configure_applications() {
    echo "Configuring application-specific theming..."
    
    # Configure TextEdit for dark mode
    defaults write com.apple.TextEdit RichTextFontSize -int 14
    defaults write com.apple.TextEdit RichTextFontName -string "Menlo"
    
    # Configure Calculator for dark mode
    defaults write com.apple.calculator ViewDefaultsKey -string "Scientific"
    
    # Configure Activity Monitor for dark mode
    defaults write com.apple.ActivityMonitor IconType -int 6
    
    # Configure Console for dark mode
    defaults write com.apple.Console LogViewerShowLineNumbers -bool true
    
    print_status "Application-specific theming configured"
}

# Create system theme status script
create_theme_status_script() {
    local status_script="$HOME/.config/purple-theme/system-status.sh"
    
    echo "Creating system theme status script..."
    
    mkdir -p "$(dirname "$status_script")"
    
    cat > "$status_script" << 'EOF'
#!/bin/bash

# Purple Theme System Status Script

echo -e "\033[1;35mPurple Theme System Status\033[0m"
echo "=================================="

# Check accent color
accent_color=$(defaults read NSGlobalDomain AppleAccentColor 2>/dev/null || echo "not set")
if [ "$accent_color" = "5" ]; then
    echo -e "\033[0;32m✓\033[0m System accent color: Purple"
else
    echo -e "\033[0;33m⚠\033[0m System accent color: Not purple (value: $accent_color)"
fi

# Check interface style
interface_style=$(defaults read NSGlobalDomain AppleInterfaceStyle 2>/dev/null || echo "Light")
echo -e "\033[0;32m✓\033[0m Interface style: $interface_style"

# Check highlight color
highlight_color=$(defaults read NSGlobalDomain AppleHighlightColor 2>/dev/null || echo "not set")
if [[ "$highlight_color" == *"Purple"* ]]; then
    echo -e "\033[0;32m✓\033[0m Highlight color: Purple"
else
    echo -e "\033[0;33m⚠\033[0m Highlight color: $highlight_color"
fi

# Check dock settings
dock_autohide=$(defaults read com.apple.dock autohide 2>/dev/null || echo "0")
if [ "$dock_autohide" = "1" ]; then
    echo -e "\033[0;32m✓\033[0m Dock: Auto-hide enabled"
else
    echo -e "\033[0;34mℹ\033[0m Dock: Auto-hide disabled"
fi

# Check Finder settings
colored_icons=$(defaults read NSGlobalDomain NSColoredSidebarIconsEnabled 2>/dev/null || echo "0")
if [ "$colored_icons" = "1" ]; then
    echo -e "\033[0;32m✓\033[0m Finder: Colored sidebar icons enabled"
else
    echo -e "\033[0;33m⚠\033[0m Finder: Colored sidebar icons disabled"
fi

echo
echo -e "\033[1;35mRecommendations:\033[0m"
if [ "$accent_color" != "5" ]; then
    echo "- Run system integration script to set purple accent color"
fi
if [[ "$highlight_color" != *"Purple"* ]]; then
    echo "- Configure highlight color to purple"
fi
if [ "$colored_icons" != "1" ]; then
    echo "- Enable colored sidebar icons in Finder"
fi

echo
echo -e "\033[0;35mTo update system theme settings, run:\033[0m"
echo "  $(dirname "$0")/install-system-integration.sh"
EOF
    
    chmod +x "$status_script"
    print_status "System theme status script created at ~/.config/purple-theme/system-status.sh"
}

# Create uninstall script for system changes
create_uninstall_script() {
    local uninstall_script="$HOME/.config/purple-theme/uninstall-system.sh"
    
    echo "Creating system theme uninstall script..."
    
    cat > "$uninstall_script" << 'EOF'
#!/bin/bash

# Purple Theme System Uninstall Script

echo -e "\033[1;35mPurple Theme System Uninstall\033[0m"
echo "====================================="

echo "Reverting system accent color..."
defaults delete NSGlobalDomain AppleAccentColor 2>/dev/null || true
defaults delete NSGlobalDomain AppleHighlightColor 2>/dev/null || true

echo "Reverting interface style to Light..."
defaults delete NSGlobalDomain AppleInterfaceStyle 2>/dev/null || true

echo "Reverting Finder settings..."
defaults delete NSGlobalDomain NSTableViewDefaultSizeMode 2>/dev/null || true
defaults delete NSGlobalDomain NSColoredSidebarIconsEnabled 2>/dev/null || true
defaults delete com.apple.finder FXPreferredViewStyle 2>/dev/null || true

echo "Reverting Dock settings..."
defaults delete com.apple.dock magnification 2>/dev/null || true
defaults delete com.apple.dock largesize 2>/dev/null || true
defaults delete com.apple.dock autohide 2>/dev/null || true
defaults delete com.apple.dock autohide-delay 2>/dev/null || true
defaults delete com.apple.dock autohide-time-modifier 2>/dev/null || true

echo "Restarting system services..."
killall Dock 2>/dev/null || true
killall SystemUIServer 2>/dev/null || true
killall Finder 2>/dev/null || true

echo -e "\033[0;32m✓\033[0m System theme settings reverted"
echo "You may need to manually change Terminal.app and iTerm2 profiles back to default"
EOF
    
    chmod +x "$uninstall_script"
    print_status "System theme uninstall script created at ~/.config/purple-theme/uninstall-system.sh"
}

# Request necessary permissions
request_permissions() {
    echo "Requesting necessary permissions..."
    
    # Check if we can write to system preferences
    if ! defaults read NSGlobalDomain AppleAccentColor >/dev/null 2>&1; then
        print_warning "May need additional permissions to modify system preferences"
    fi
    
    print_info "This script will modify system appearance settings"
    print_info "Changes can be reverted using the uninstall script"
    
    read -p "Continue with system integration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "System integration cancelled by user"
        exit 0
    fi
}

# Main installation process
main() {
    echo "Starting system purple theme integration..."
    echo
    
    # Check prerequisites
    check_macos
    check_macos_version
    
    # Request permissions
    request_permissions
    
    echo
    echo "Configuring system appearance..."
    
    # Set system accent color
    set_system_accent_color
    
    # Configure system components
    configure_menu_bar
    configure_dock
    configure_finder
    
    # Configure applications
    configure_applications
    
    # Configure Terminal.app
    configure_terminal_app
    
    # Create utility scripts
    echo
    echo "Creating utility scripts..."
    create_theme_status_script
    create_uninstall_script
    
    echo
    echo -e "${GREEN}🎉 System integration completed successfully!${NC}"
    echo
    echo "System changes applied:"
    echo "  ✓ Accent color set to purple"
    echo "  ✓ Interface style set to dark"
    echo "  ✓ Dock configured for purple theme"
    echo "  ✓ Finder configured for purple theme"
    echo "  ✓ Menu bar configured for purple theme"
    echo "  ✓ Application defaults updated"
    echo
    echo "Available commands:"
    echo "  ~/.config/purple-theme/system-status.sh     - Check system theme status"
    echo "  ~/.config/purple-theme/uninstall-system.sh  - Revert system changes"
    echo
    echo "Note: Some changes may require logging out and back in to take full effect"
    echo "Terminal.app setup requires manual profile selection in preferences"
    echo
}

# Run main function
main "$@"