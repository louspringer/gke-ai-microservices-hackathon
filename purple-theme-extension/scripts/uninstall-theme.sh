#!/bin/bash

# Purple Theme Uninstallation Script
# Restores original configurations and removes installed theme files

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration and state files
CONFIG_DIR="$HOME/.config/purple-theme"
INSTALLATION_STATE="$CONFIG_DIR/install-state.json"
INSTALLATION_LOG="$CONFIG_DIR/installation.log"

# Legacy backup directory (for backward compatibility)
BACKUP_DIR="$HOME/.purple-theme-backups"

# Uninstallation results
UNINSTALL_SUCCESS=true
UNINSTALL_ERRORS=()
UNINSTALL_WARNINGS=()

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            UNINSTALL_SUCCESS=false
            UNINSTALL_ERRORS+=("$message")
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠${NC} $message"
            UNINSTALL_WARNINGS+=("$message")
            ;;
        "INFO")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
        "HEADER")
            echo -e "${PURPLE}${message}${NC}"
            ;;
    esac
}

# Function to check installation state
check_installation_state() {
    if [[ -f "$INSTALLATION_STATE" ]]; then
        print_status "SUCCESS" "Installation state found: $INSTALLATION_STATE"
        return 0
    else
        print_status "WARNING" "No installation state found"
        print_status "INFO" "Will attempt to detect and remove purple theme components"
        return 1
    fi
}

# Function to get installed components from state
get_installed_components() {
    if [[ -f "$INSTALLATION_STATE" ]] && command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json
import sys

try:
    with open('$INSTALLATION_STATE', 'r') as f:
        state = json.load(f)
    
    components = state.get('components', {})
    installed = []
    
    for component, status in components.items():
        if status:
            installed.append(component)
    
    print(' '.join(installed))
except Exception as e:
    print('', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Function to confirm uninstallation
confirm_uninstallation() {
    print_status "HEADER" "Purple Theme Uninstallation"
    print_status "HEADER" "============================"
    echo
    
    # Check installation state
    local has_state=false
    if check_installation_state; then
        has_state=true
        local installed_components=($(get_installed_components))
        
        if [[ ${#installed_components[@]} -gt 0 ]]; then
            print_status "INFO" "Installed components detected:"
            for component in "${installed_components[@]}"; do
                case "$component" in
                    "vscode")
                        print_status "INFO" "  • VS Code purple theme extension"
                        ;;
                    "terminal")
                        print_status "INFO" "  • Terminal color configurations"
                        ;;
                    "system")
                        print_status "INFO" "  • System integration changes"
                        ;;
                esac
            done
        else
            print_status "INFO" "No components appear to be installed"
        fi
    else
        print_status "INFO" "Will attempt to detect and remove:"
        print_status "INFO" "  • VS Code purple theme extension"
        print_status "INFO" "  • Terminal color configurations"
        print_status "INFO" "  • Shell profile modifications"
        print_status "INFO" "  • System integration changes"
    fi
    
    echo
    print_status "WARNING" "This will remove the purple theme and restore original configurations"
    
    # Check for backup files
    local backup_found=false
    
    # Check for timestamped backups (new format)
    for config_file in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
        if ls "${config_file}.backup."* >/dev/null 2>&1; then
            if [[ "$backup_found" == false ]]; then
                print_status "SUCCESS" "Configuration backups found"
                backup_found=true
            fi
            break
        fi
    done
    
    # Check VS Code settings backups
    local vscode_settings=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        vscode_settings="$HOME/Library/Application Support/Code/User/settings.json"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        vscode_settings="$HOME/.config/Code/User/settings.json"
    fi
    
    if [[ -n "$vscode_settings" ]] && ls "${vscode_settings}.backup."* >/dev/null 2>&1; then
        if [[ "$backup_found" == false ]]; then
            print_status "SUCCESS" "Configuration backups found"
            backup_found=true
        fi
    fi
    
    # Check legacy backup directory
    if [[ -d "$BACKUP_DIR" ]]; then
        if [[ "$backup_found" == false ]]; then
            print_status "SUCCESS" "Legacy backup directory found: $BACKUP_DIR"
            backup_found=true
        fi
    fi
    
    if [[ "$backup_found" == false ]]; then
        print_status "WARNING" "No backup files found"
        print_status "WARNING" "Original configurations may not be fully restored"
    fi
    
    echo
    read -p "Do you want to continue with uninstallation? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "INFO" "Uninstallation cancelled"
        exit 0
    fi
    
    echo
}

# Function to uninstall VS Code theme
uninstall_vscode_theme() {
    print_status "HEADER" "=== Uninstalling VS Code Theme ==="
    
    # Find VS Code extensions directory
    local extensions_dir=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        extensions_dir="$HOME/.vscode/extensions"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        extensions_dir="$HOME/.vscode/extensions"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        extensions_dir="$HOME/.vscode/extensions"
    fi
    
    if [[ -d "$extensions_dir" ]]; then
        # Remove purple theme extensions (more specific pattern matching)
        local theme_removed=false
        local extension_patterns=(
            "purple-theme-dev.purple-development-theme-*"
            "*purple*development*theme*"
            "*purple*theme*"
        )
        
        for pattern in "${extension_patterns[@]}"; do
            for ext_dir in "$extensions_dir"/$pattern; do
                if [[ -d "$ext_dir" ]]; then
                    print_status "INFO" "Removing extension: $(basename "$ext_dir")"
                    if rm -rf "$ext_dir"; then
                        print_status "SUCCESS" "Extension removed successfully"
                        theme_removed=true
                    else
                        print_status "ERROR" "Failed to remove extension: $ext_dir"
                    fi
                fi
            done
        done
        
        if [[ "$theme_removed" == false ]]; then
            print_status "INFO" "No purple theme extensions found to remove"
        fi
    else
        print_status "WARNING" "VS Code extensions directory not found: $extensions_dir"
    fi
    
    # Restore VS Code settings
    local settings_file=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        settings_file="$HOME/Library/Application Support/Code/User/settings.json"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        settings_file="$HOME/.config/Code/User/settings.json"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        settings_file="$HOME/AppData/Roaming/Code/User/settings.json"
    fi
    
    if [[ -n "$settings_file" ]]; then
        # Look for timestamped backup files (newest first)
        local backup_file=$(ls "${settings_file}.backup."* 2>/dev/null | sort -r | head -1)
        
        if [[ -n "$backup_file" && -f "$backup_file" ]]; then
            print_status "INFO" "Restoring VS Code settings from backup: $(basename "$backup_file")"
            if cp "$backup_file" "$settings_file"; then
                print_status "SUCCESS" "VS Code settings restored from timestamped backup"
            else
                print_status "ERROR" "Failed to restore VS Code settings from backup"
            fi
        else
            # Check legacy backup location
            local legacy_backup="$BACKUP_DIR/vscode-settings.json"
            if [[ -f "$legacy_backup" ]]; then
                print_status "INFO" "Restoring VS Code settings from legacy backup"
                if cp "$legacy_backup" "$settings_file"; then
                    print_status "SUCCESS" "VS Code settings restored from legacy backup"
                else
                    print_status "ERROR" "Failed to restore VS Code settings from legacy backup"
                fi
            elif [[ -f "$settings_file" ]]; then
                # Remove purple theme settings if no backup exists
                print_status "INFO" "No backup found, removing purple theme settings manually"
                
                if command -v python3 >/dev/null 2>&1; then
                    # Use Python for reliable JSON manipulation
                    python3 -c "
import json
import sys

try:
    with open('$settings_file', 'r') as f:
        settings = json.load(f)
    
    # Remove purple theme related settings
    purple_keys = [
        'workbench.colorTheme',
        'workbench.preferredDarkColorTheme'
    ]
    
    removed_any = False
    for key in purple_keys:
        if key in settings:
            value = settings[key]
            if 'Purple' in str(value):
                del settings[key]
                removed_any = True
                print(f'Removed {key}: {value}', file=sys.stderr)
    
    if removed_any:
        with open('$settings_file', 'w') as f:
            json.dump(settings, f, indent=2)
        print('Settings updated successfully', file=sys.stderr)
    else:
        print('No purple theme settings found to remove', file=sys.stderr)
        
except Exception as e:
    print(f'Error updating settings: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null && print_status "SUCCESS" "Purple theme settings removed" || print_status "ERROR" "Failed to update VS Code settings"
                elif command -v jq >/dev/null 2>&1; then
                    # Fallback to jq
                    local current_theme=$(jq -r '."workbench.colorTheme"' "$settings_file" 2>/dev/null)
                    if [[ "$current_theme" == *"Purple"* ]]; then
                        print_status "INFO" "Removing purple theme from VS Code settings"
                        local temp_settings=$(mktemp)
                        jq 'del(."workbench.colorTheme", ."workbench.preferredDarkColorTheme")' "$settings_file" > "$temp_settings"
                        if mv "$temp_settings" "$settings_file"; then
                            print_status "SUCCESS" "Purple theme settings removed"
                        else
                            print_status "ERROR" "Failed to update VS Code settings"
                        fi
                    else
                        print_status "INFO" "Purple theme not active in VS Code settings"
                    fi
                else
                    print_status "WARNING" "Neither Python nor jq available, cannot modify VS Code settings automatically"
                    print_status "INFO" "Please manually remove purple theme from VS Code preferences"
                fi
            else
                print_status "INFO" "No VS Code settings file found"
            fi
        fi
    fi
    
    echo
}

# Function to restore shell configurations
restore_shell_configurations() {
    print_status "HEADER" "=== Restoring Shell Configurations ==="
    
    # Shell configuration files to check
    local shell_configs=(
        "$HOME/.zshrc"
        "$HOME/.bash_profile"
        "$HOME/.bashrc"
    )
    
    for config in "${shell_configs[@]}"; do
        if [[ -f "$config" ]]; then
            local config_name=$(basename "$config")
            
            # Look for timestamped backup files (newest first)
            local backup_file=$(ls "${config}.backup."* 2>/dev/null | sort -r | head -1)
            
            if [[ -n "$backup_file" && -f "$backup_file" ]]; then
                print_status "INFO" "Restoring $config from timestamped backup: $(basename "$backup_file")"
                if cp "$backup_file" "$config"; then
                    print_status "SUCCESS" "Restored: $config"
                else
                    print_status "ERROR" "Failed to restore: $config"
                fi
            else
                # Check legacy backup location
                local legacy_backup="$BACKUP_DIR/$config_name"
                if [[ -f "$legacy_backup" ]]; then
                    print_status "INFO" "Restoring $config from legacy backup"
                    if cp "$legacy_backup" "$config"; then
                        print_status "SUCCESS" "Restored: $config"
                    else
                        print_status "ERROR" "Failed to restore: $config"
                    fi
                else
                    # Remove purple theme lines if no backup exists
                    print_status "INFO" "No backup found, removing purple theme lines from: $config"
                    
                    # Create temporary file without purple theme lines
                    local temp_config=$(mktemp)
                    
                    # Remove purple theme configuration blocks
                    awk '
                    /^# Purple Theme.*Configuration/ { skip=1; next }
                    /^echo "Purple.*theme configuration loaded!"/ { skip=0; next }
                    skip { next }
                    /purple-colors\.sh/ { next }
                    /PURPLE_THEME/ { next }
                    /TERM_BACKGROUND/ { next }
                    /TERM_FOREGROUND/ { next }
                    /COLOR_.*PURPLE/ { next }
                    { print }
                    ' "$config" > "$temp_config"
                    
                    if mv "$temp_config" "$config"; then
                        print_status "SUCCESS" "Cleaned purple theme references from: $config"
                    else
                        print_status "ERROR" "Failed to clean: $config"
                        rm -f "$temp_config"
                    fi
                fi
            fi
        else
            print_status "INFO" "Shell configuration not found: $config"
        fi
    done
    
    # Remove purple theme configuration directory
    if [[ -d "$CONFIG_DIR" ]]; then
        print_status "INFO" "Removing purple theme configuration directory"
        
        # Preserve the uninstall script and logs
        local preserve_files=(
            "$(basename "${BASH_SOURCE[0]}")"
            "installation.log"
            "rollback.sh"
        )
        
        for file in "$CONFIG_DIR"/*; do
            if [[ -f "$file" ]]; then
                local filename=$(basename "$file")
                local preserve=false
                
                for preserve_file in "${preserve_files[@]}"; do
                    if [[ "$filename" == "$preserve_file" ]]; then
                        preserve=true
                        break
                    fi
                done
                
                if [[ "$preserve" == false ]]; then
                    if rm "$file"; then
                        print_status "SUCCESS" "Removed configuration file: $filename"
                    else
                        print_status "ERROR" "Failed to remove: $file"
                    fi
                fi
            fi
        done
    fi
    
    echo
}

# Function to restore terminal emulator configurations
restore_terminal_configurations() {
    print_status "HEADER" "=== Restoring Terminal Configurations ==="
    
    # macOS Terminal.app
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local terminal_backup="$BACKUP_DIR/terminal-settings.plist"
        
        if [[ -f "$terminal_backup" ]]; then
            print_status "INFO" "Restoring Terminal.app settings"
            if defaults import com.apple.Terminal "$terminal_backup" 2>/dev/null; then
                print_status "SUCCESS" "Terminal.app settings restored"
            else
                print_status "ERROR" "Failed to restore Terminal.app settings"
            fi
        else
            # Reset to default theme
            print_status "INFO" "Resetting Terminal.app to default theme"
            defaults write com.apple.Terminal "Default Window Settings" "Basic" 2>/dev/null || true
            defaults write com.apple.Terminal "Startup Window Settings" "Basic" 2>/dev/null || true
            print_status "SUCCESS" "Terminal.app reset to Basic theme"
        fi
        
        # Remove custom purple terminal profiles
        local profiles_dir="$HOME/Library/Preferences"
        if [[ -f "$profiles_dir/com.apple.Terminal.plist" ]]; then
            print_status "INFO" "Removing purple terminal profiles"
            # This would require more complex plist manipulation
            print_status "WARNING" "Manual removal of purple profiles may be needed"
        fi
    fi
    
    # iTerm2
    local iterm_config_dir="$HOME/Library/Preferences"
    local iterm_backup="$BACKUP_DIR/com.googlecode.iterm2.plist"
    
    if [[ -f "$iterm_backup" ]]; then
        print_status "INFO" "Restoring iTerm2 settings"
        if cp "$iterm_backup" "$iterm_config_dir/com.googlecode.iterm2.plist"; then
            print_status "SUCCESS" "iTerm2 settings restored"
        else
            print_status "ERROR" "Failed to restore iTerm2 settings"
        fi
    else
        print_status "INFO" "No iTerm2 backup found"
    fi
    
    echo
}

# Function to clean up system integration
cleanup_system_integration() {
    print_status "HEADER" "=== Cleaning Up System Integration ==="
    
    # Only run system cleanup on macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_status "INFO" "System integration cleanup skipped (not on macOS)"
        echo
        return 0
    fi
    
    # Check if system integration was installed
    local installed_components=($(get_installed_components))
    local system_installed=false
    
    for component in "${installed_components[@]}"; do
        if [[ "$component" == "system" ]]; then
            system_installed=true
            break
        fi
    done
    
    if [[ "$system_installed" == false ]]; then
        print_status "INFO" "System integration was not installed, skipping cleanup"
        echo
        return 0
    fi
    
    # Run system uninstall script if it exists
    local system_uninstall="$CONFIG_DIR/uninstall-system.sh"
    if [[ -f "$system_uninstall" ]]; then
        print_status "INFO" "Running system integration uninstall script"
        if bash "$system_uninstall"; then
            print_status "SUCCESS" "System integration uninstalled successfully"
        else
            print_status "ERROR" "System integration uninstall script failed"
        fi
    else
        # Manual system cleanup
        print_status "INFO" "Performing manual system integration cleanup"
        
        # Reset system accent color
        local current_accent=$(defaults read NSGlobalDomain AppleAccentColor 2>/dev/null || echo "")
        if [[ "$current_accent" == "5" ]]; then
            print_status "INFO" "Resetting system accent color from purple"
            defaults delete NSGlobalDomain AppleAccentColor 2>/dev/null || true
            print_status "SUCCESS" "System accent color reset to default"
        else
            print_status "INFO" "System accent color is not set to purple"
        fi
        
        # Reset highlight color
        local current_highlight=$(defaults read NSGlobalDomain AppleHighlightColor 2>/dev/null || echo "")
        if [[ "$current_highlight" == *"Purple"* ]]; then
            print_status "INFO" "Resetting system highlight color from purple"
            defaults delete NSGlobalDomain AppleHighlightColor 2>/dev/null || true
            print_status "SUCCESS" "System highlight color reset to default"
        else
            print_status "INFO" "System highlight color is not set to purple"
        fi
        
        # Reset interface style if it was changed
        local current_style=$(defaults read NSGlobalDomain AppleInterfaceStyle 2>/dev/null || echo "")
        if [[ "$current_style" == "Dark" ]]; then
            print_status "WARNING" "Interface style is set to Dark - this may have been changed by purple theme"
            read -p "Reset interface style to Light? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                defaults delete NSGlobalDomain AppleInterfaceStyle 2>/dev/null || true
                print_status "SUCCESS" "Interface style reset to Light"
            else
                print_status "INFO" "Interface style left as Dark"
            fi
        fi
        
        # Reset Finder settings
        defaults delete NSGlobalDomain NSTableViewDefaultSizeMode 2>/dev/null || true
        defaults delete NSGlobalDomain NSColoredSidebarIconsEnabled 2>/dev/null || true
        defaults delete com.apple.finder FXPreferredViewStyle 2>/dev/null || true
        
        # Reset Dock settings
        defaults delete com.apple.dock magnification 2>/dev/null || true
        defaults delete com.apple.dock largesize 2>/dev/null || true
        defaults delete com.apple.dock autohide 2>/dev/null || true
        defaults delete com.apple.dock autohide-delay 2>/dev/null || true
        defaults delete com.apple.dock autohide-time-modifier 2>/dev/null || true
        
        # Restart system services
        print_status "INFO" "Restarting system services to apply changes"
        killall Dock 2>/dev/null || true
        killall SystemUIServer 2>/dev/null || true
        killall Finder 2>/dev/null || true
        
        print_status "SUCCESS" "System integration cleanup completed"
    fi
    
    echo
}

# Function to remove environment variables
cleanup_environment_variables() {
    print_status "HEADER" "=== Cleaning Up Environment Variables ==="
    
    # Remove purple theme environment variables from current session
    local purple_vars=(
        "PURPLE_DEEP"
        "PURPLE_MEDIUM"
        "PURPLE_LIGHT"
        "PURPLE_ACCENT"
        "PURPLE_BRIGHT"
        "LAVENDER"
        "PLUM"
        "TERM_BACKGROUND"
        "TERM_FOREGROUND"
        "TERM_BG_RGB"
        "TERM_FG_RGB"
        "PURPLE_THEME_ACTIVE"
        "PURPLE_THEME_VERSION"
    )
    
    for var in "${purple_vars[@]}"; do
        if [[ -n "${!var}" ]]; then
            unset "$var"
            print_status "SUCCESS" "Unset environment variable: $var"
        fi
    done
    
    # Remove color variables
    local color_vars=($(env | grep -E '^COLOR_|^BG_' | cut -d= -f1))
    for var in "${color_vars[@]}"; do
        if [[ "$var" == *"PURPLE"* ]] || [[ "$var" == *"LAVENDER"* ]] || [[ "$var" == *"PLUM"* ]]; then
            unset "$var"
            print_status "SUCCESS" "Unset color variable: $var"
        fi
    done
    
    echo
}

# Function to clean up installation state
cleanup_installation_state() {
    print_status "HEADER" "=== Cleaning Up Installation State ==="
    
    # Remove installation state file
    if [[ -f "$INSTALLATION_STATE" ]]; then
        if rm "$INSTALLATION_STATE"; then
            print_status "SUCCESS" "Installation state file removed"
        else
            print_status "ERROR" "Failed to remove installation state file"
        fi
    else
        print_status "INFO" "No installation state file found"
    fi
    
    # Archive installation log
    if [[ -f "$INSTALLATION_LOG" ]]; then
        local log_archive="$INSTALLATION_LOG.uninstalled.$(date +%Y%m%d_%H%M%S)"
        if mv "$INSTALLATION_LOG" "$log_archive"; then
            print_status "SUCCESS" "Installation log archived to: $(basename "$log_archive")"
        else
            print_status "WARNING" "Failed to archive installation log"
        fi
    fi
    
    echo
}

# Function to remove theme files
remove_theme_files() {
    print_status "HEADER" "=== Removing Theme Files ==="
    
    # Ask if user wants to remove theme source files
    read -p "Do you want to remove the theme source files? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "WARNING" "This will remove all theme source files"
        read -p "Are you sure? This cannot be undone! (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "INFO" "Removing theme source files..."
            
            # Remove theme directory contents (but preserve this script until the end)
            local files_to_remove=(
                "$THEME_DIR/themes"
                "$THEME_DIR/terminal"
                "$THEME_DIR/shell"
                "$THEME_DIR/package.json"
                "$THEME_DIR/README.md"
                "$THEME_DIR/INSTALL.md"
                "$THEME_DIR/install.sh"
            )
            
            for item in "${files_to_remove[@]}"; do
                if [[ -e "$item" ]]; then
                    if rm -rf "$item"; then
                        print_status "SUCCESS" "Removed: $(basename "$item")"
                    else
                        print_status "ERROR" "Failed to remove: $item"
                    fi
                fi
            done
            
            # Remove installation scripts (except this one)
            if [[ -d "$THEME_DIR/scripts" ]]; then
                for script in "$THEME_DIR/scripts"/*.sh; do
                    if [[ -f "$script" ]] && [[ "$script" != "${BASH_SOURCE[0]}" ]]; then
                        if rm "$script"; then
                            print_status "SUCCESS" "Removed: $(basename "$script")"
                        else
                            print_status "ERROR" "Failed to remove: $script"
                        fi
                    fi
                done
                
                # Remove scripts directory if empty
                if rmdir "$THEME_DIR/scripts" 2>/dev/null; then
                    print_status "SUCCESS" "Removed empty scripts directory"
                fi
            fi
            
            print_status "SUCCESS" "Theme source files removed"
            print_status "INFO" "Uninstall script preserved for reference"
        else
            print_status "INFO" "Theme source files preserved"
        fi
    else
        print_status "INFO" "Theme source files preserved"
    fi
    
    echo
}

# Function to clean up backup files
cleanup_backups() {
    print_status "HEADER" "=== Cleaning Up Backup Files ==="
    
    local backup_files_found=false
    
    # Check for timestamped backup files
    local config_files=(
        "$HOME/.zshrc"
        "$HOME/.bashrc"
        "$HOME/.bash_profile"
    )
    
    # Add VS Code settings file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        config_files+=("$HOME/Library/Application Support/Code/User/settings.json")
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        config_files+=("$HOME/.config/Code/User/settings.json")
    fi
    
    # Count backup files
    local backup_count=0
    for config_file in "${config_files[@]}"; do
        if ls "${config_file}.backup."* >/dev/null 2>&1; then
            backup_count=$((backup_count + $(ls "${config_file}.backup."* 2>/dev/null | wc -l)))
            backup_files_found=true
        fi
    done
    
    # Check legacy backup directory
    if [[ -d "$BACKUP_DIR" ]]; then
        backup_files_found=true
        local legacy_count=$(find "$BACKUP_DIR" -type f 2>/dev/null | wc -l)
        backup_count=$((backup_count + legacy_count))
    fi
    
    if [[ "$backup_files_found" == true ]]; then
        print_status "INFO" "Found $backup_count backup file(s)"
        read -p "Do you want to remove backup files? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "WARNING" "This will permanently delete all backup files"
            read -p "Are you sure? This cannot be undone! (y/N): " -n 1 -r
            echo
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                # Remove timestamped backup files
                for config_file in "${config_files[@]}"; do
                    for backup_file in "${config_file}.backup."*; do
                        if [[ -f "$backup_file" ]]; then
                            if rm "$backup_file"; then
                                print_status "SUCCESS" "Removed backup: $(basename "$backup_file")"
                            else
                                print_status "ERROR" "Failed to remove backup: $backup_file"
                            fi
                        fi
                    done
                done
                
                # Remove legacy backup directory
                if [[ -d "$BACKUP_DIR" ]]; then
                    if rm -rf "$BACKUP_DIR"; then
                        print_status "SUCCESS" "Legacy backup directory removed"
                    else
                        print_status "ERROR" "Failed to remove legacy backup directory"
                    fi
                fi
                
                print_status "SUCCESS" "Backup cleanup completed"
            else
                print_status "INFO" "Backup files preserved"
            fi
        else
            print_status "INFO" "Backup files preserved"
        fi
    else
        print_status "INFO" "No backup files found to clean up"
    fi
    
    echo
}

# Function to generate uninstallation report
generate_uninstallation_report() {
    print_status "HEADER" "=== Uninstallation Report ==="
    
    if [[ "$UNINSTALL_SUCCESS" == true ]]; then
        print_status "SUCCESS" "Purple theme uninstallation completed successfully!"
    else
        print_status "ERROR" "Uninstallation completed with ${#UNINSTALL_ERRORS[@]} error(s)"
    fi
    
    if [[ ${#UNINSTALL_WARNINGS[@]} -gt 0 ]]; then
        print_status "WARNING" "${#UNINSTALL_WARNINGS[@]} warning(s) encountered"
    fi
    
    # Print errors
    if [[ ${#UNINSTALL_ERRORS[@]} -gt 0 ]]; then
        echo -e "\n${RED}Errors:${NC}"
        for error in "${UNINSTALL_ERRORS[@]}"; do
            echo -e "  ${RED}•${NC} $error"
        done
    fi
    
    # Print warnings
    if [[ ${#UNINSTALL_WARNINGS[@]} -gt 0 ]]; then
        echo -e "\n${YELLOW}Warnings:${NC}"
        for warning in "${UNINSTALL_WARNINGS[@]}"; do
            echo -e "  ${YELLOW}•${NC} $warning"
        done
    fi
    
    echo
    
    # Post-uninstallation instructions
    print_status "HEADER" "=== Post-Uninstallation Instructions ==="
    print_status "INFO" "1. Restart VS Code to apply theme changes"
    print_status "INFO" "2. Restart terminal or source shell configuration"
    print_status "INFO" "3. Log out and back in to apply system changes (macOS)"
    print_status "INFO" "4. Check terminal emulator preferences for any remaining purple profiles"
    
    if [[ ${#UNINSTALL_ERRORS[@]} -gt 0 ]]; then
        print_status "WARNING" "5. Manually address any remaining errors"
        print_status "INFO" "6. Some configurations may require manual cleanup"
    fi
    
    echo
    print_status "SUCCESS" "Thank you for using the Purple Development Theme!"
    echo
}

# Main uninstallation function
main() {
    # Confirm uninstallation
    confirm_uninstallation
    
    # Log uninstallation start
    if [[ -f "$INSTALLATION_LOG" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Uninstallation started" >> "$INSTALLATION_LOG"
    fi
    
    # Run uninstallation steps
    uninstall_vscode_theme
    restore_shell_configurations
    restore_terminal_configurations
    cleanup_system_integration
    cleanup_environment_variables
    cleanup_installation_state
    remove_theme_files
    cleanup_backups
    
    # Generate report
    generate_uninstallation_report
    
    # Log uninstallation completion
    if [[ -f "$INSTALLATION_LOG.uninstalled."* ]]; then
        local log_file=$(ls "$INSTALLATION_LOG.uninstalled."* | head -1)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Uninstallation completed" >> "$log_file"
    fi
    
    # Exit with appropriate code
    if [[ "$UNINSTALL_SUCCESS" == true ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi