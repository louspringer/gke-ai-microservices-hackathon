#!/bin/bash

# Purple Development Theme - Comprehensive Installation Script
# This master script orchestrates all theme installations with error handling and rollback

set -e

# Colors for output
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Installation state tracking
INSTALLATION_LOG="$HOME/.config/purple-theme/installation.log"
ROLLBACK_SCRIPT="$HOME/.config/purple-theme/rollback.sh"
INSTALLATION_STATE="$HOME/.config/purple-theme/install-state.json"

# Component installation flags
VSCODE_INSTALLED=false
TERMINAL_INSTALLED=false
SYSTEM_INSTALLED=false

echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}║           🎨 Purple Development Theme Installer 🎨           ║${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}║    Comprehensive purple theming for your development        ║${NC}"
echo -e "${PURPLE}║    environment: VS Code, Terminal, and System integration   ║${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

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

print_progress() {
    echo -e "${CYAN}▶${NC} $1"
}

print_section() {
    echo
    echo -e "${PURPLE}═══ $1 ═══${NC}"
}

# Initialize installation logging
init_logging() {
    local config_dir="$HOME/.config/purple-theme"
    mkdir -p "$config_dir"
    
    # Create installation log
    echo "Purple Theme Installation Log - $(date)" > "$INSTALLATION_LOG"
    echo "=============================================" >> "$INSTALLATION_LOG"
    
    # Initialize installation state
    cat > "$INSTALLATION_STATE" << 'EOF'
{
  "installation_date": "",
  "components": {
    "vscode": false,
    "terminal": false,
    "system": false
  },
  "backups": [],
  "version": "1.0.0"
}
EOF
    
    print_status "Installation logging initialized"
}

# Log installation step
log_step() {
    local step="$1"
    local status="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $step: $status" >> "$INSTALLATION_LOG"
}

# Update installation state
update_state() {
    local component="$1"
    local status="$2"
    
    # Use Python to update JSON state (more reliable than shell JSON manipulation)
    python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('$INSTALLATION_STATE', 'r') as f:
        state = json.load(f)
    
    state['components']['$component'] = $status
    if '$component' == 'all' and $status:
        state['installation_date'] = datetime.now().isoformat()
    
    with open('$INSTALLATION_STATE', 'w') as f:
        json.dump(state, f, indent=2)
        
except Exception as e:
    print(f'Error updating state: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || {
    print_warning "Could not update installation state (Python not available)"
}
}

# Check prerequisites
check_prerequisites() {
    print_section "Checking Prerequisites"
    
    local missing_deps=()
    
    # Check for required commands
    if ! command -v python3 &> /dev/null; then
        print_warning "Python 3 not found - some features may be limited"
    else
        print_status "Python 3 available"
    fi
    
    # Check operating system
    case "$OSTYPE" in
        "darwin"*)
            print_status "Running on macOS - full feature support available"
            ;;
        "linux-gnu"*)
            print_status "Running on Linux - VS Code and terminal theming available"
            print_warning "System integration features limited on Linux"
            ;;
        *)
            print_warning "Running on $OSTYPE - limited feature support"
            ;;
    esac
    
    # Check disk space (need at least 10MB)
    local available_space=$(df -m "$HOME" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 10 ]; then
        print_error "Insufficient disk space (need at least 10MB)"
        return 1
    else
        print_status "Sufficient disk space available"
    fi
    
    return 0
}

# Show installation options
show_installation_options() {
    print_section "Installation Options"
    
    echo "Available components:"
    echo
    echo "  1. VS Code Purple Theme"
    echo "     • Custom purple color scheme for VS Code"
    echo "     • Syntax highlighting optimized for purple palette"
    echo "     • Automatic theme activation"
    echo
    echo "  2. Terminal Purple Configuration"
    echo "     • Shell configuration (Zsh/Bash)"
    echo "     • Terminal emulator themes (Terminal.app, iTerm2)"
    echo "     • Purple color scheme and prompts"
    echo
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  3. System Integration (macOS only)"
        echo "     • System accent color configuration"
        echo "     • Dock and Finder theming"
        echo "     • Menu bar and interface styling"
        echo
    fi
    
    echo "Installation modes:"
    echo "  [F]ull    - Install all available components"
    echo "  [C]ustom  - Choose specific components"
    echo "  [Q]uit    - Exit installer"
    echo
}

# Get user installation choice
get_installation_choice() {
    while true; do
        read -p "Select installation mode [F/C/Q]: " -n 1 -r choice
        echo
        
        case "$choice" in
            [Ff])
                return 0  # Full installation
                ;;
            [Cc])
                return 1  # Custom installation
                ;;
            [Qq])
                print_info "Installation cancelled by user"
                exit 0
                ;;
            *)
                print_warning "Invalid choice. Please select F, C, or Q."
                ;;
        esac
    done
}

# Get custom component selection
get_custom_components() {
    local components=()
    
    echo "Select components to install:"
    echo
    
    # VS Code component
    read -p "Install VS Code Purple Theme? [Y/n]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        components+=("vscode")
    fi
    
    # Terminal component
    read -p "Install Terminal Purple Configuration? [Y/n]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        components+=("terminal")
    fi
    
    # System component (macOS only)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        read -p "Install System Integration? [Y/n]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            components+=("system")
        fi
    fi
    
    if [ ${#components[@]} -eq 0 ]; then
        print_warning "No components selected for installation"
        exit 0
    fi
    
    echo "${components[@]}"
}

# Create rollback script
create_rollback_script() {
    print_progress "Creating rollback script..."
    
    cat > "$ROLLBACK_SCRIPT" << 'EOF'
#!/bin/bash

# Purple Theme Rollback Script
# This script reverts all purple theme installations

set -e

PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${PURPLE}Purple Theme Rollback Utility${NC}"
echo "================================="

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check installation state
STATE_FILE="$HOME/.config/purple-theme/install-state.json"
if [ ! -f "$STATE_FILE" ]; then
    print_error "No installation state found"
    exit 1
fi

echo "Checking installed components..."

# Rollback VS Code theme
if python3 -c "import json; state=json.load(open('$STATE_FILE')); exit(0 if state['components']['vscode'] else 1)" 2>/dev/null; then
    echo "Rolling back VS Code theme..."
    
    # Remove theme extension
    VSCODE_EXT_DIR="$HOME/.vscode/extensions/purple-theme-dev.purple-development-theme-1.0.0"
    if [ -d "$VSCODE_EXT_DIR" ]; then
        rm -rf "$VSCODE_EXT_DIR"
        print_status "VS Code theme extension removed"
    fi
    
    # Restore VS Code settings backup
    SETTINGS_DIR="$HOME/Library/Application Support/Code/User"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        SETTINGS_DIR="$HOME/.config/Code/User"
    fi
    
    SETTINGS_FILE="$SETTINGS_DIR/settings.json"
    BACKUP_FILE=$(ls "$SETTINGS_FILE.backup."* 2>/dev/null | tail -1)
    
    if [ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
        cp "$BACKUP_FILE" "$SETTINGS_FILE"
        print_status "VS Code settings restored from backup"
    fi
fi

# Rollback terminal configuration
if python3 -c "import json; state=json.load(open('$STATE_FILE')); exit(0 if state['components']['terminal'] else 1)" 2>/dev/null; then
    echo "Rolling back terminal configuration..."
    
    # Restore shell configuration backups
    for shell_config in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
        if [ -f "$shell_config" ]; then
            BACKUP_FILE=$(ls "$shell_config.backup."* 2>/dev/null | tail -1)
            if [ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
                cp "$BACKUP_FILE" "$shell_config"
                print_status "Restored $(basename "$shell_config") from backup"
            fi
        fi
    done
    
    # Remove purple theme configuration directory
    if [ -d "$HOME/.config/purple-theme" ]; then
        # Keep rollback script but remove other files
        find "$HOME/.config/purple-theme" -name "*.sh" ! -name "rollback.sh" -delete 2>/dev/null || true
        print_status "Purple theme configuration files removed"
    fi
fi

# Rollback system integration (macOS only)
if [[ "$OSTYPE" == "darwin"* ]] && python3 -c "import json; state=json.load(open('$STATE_FILE')); exit(0 if state['components']['system'] else 1)" 2>/dev/null; then
    echo "Rolling back system integration..."
    
    # Run system uninstall script if it exists
    SYSTEM_UNINSTALL="$HOME/.config/purple-theme/uninstall-system.sh"
    if [ -f "$SYSTEM_UNINSTALL" ]; then
        bash "$SYSTEM_UNINSTALL"
        print_status "System integration reverted"
    fi
fi

# Clean up installation state
rm -f "$STATE_FILE" 2>/dev/null || true

echo
echo -e "${GREEN}🎉 Purple theme rollback completed!${NC}"
echo
echo "All purple theme components have been removed and original"
echo "configurations have been restored from backups."
echo
echo "You may need to restart your terminal and VS Code to see the changes."
EOF
    
    chmod +x "$ROLLBACK_SCRIPT"
    print_status "Rollback script created at ~/.config/purple-theme/rollback.sh"
}

# Install VS Code component
install_vscode_component() {
    print_section "Installing VS Code Purple Theme"
    
    log_step "VS Code installation" "started"
    
    local vscode_script="$SCRIPT_DIR/scripts/install-vscode-theme.sh"
    
    if [ ! -f "$vscode_script" ]; then
        print_error "VS Code installation script not found: $vscode_script"
        log_step "VS Code installation" "failed - script not found"
        return 1
    fi
    
    print_progress "Running VS Code theme installer..."
    
    if bash "$vscode_script"; then
        VSCODE_INSTALLED=true
        update_state "vscode" true
        log_step "VS Code installation" "completed successfully"
        print_status "VS Code purple theme installed successfully"
        return 0
    else
        log_step "VS Code installation" "failed"
        print_error "VS Code theme installation failed"
        return 1
    fi
}

# Install Terminal component
install_terminal_component() {
    print_section "Installing Terminal Purple Configuration"
    
    log_step "Terminal installation" "started"
    
    local terminal_script="$SCRIPT_DIR/scripts/install-terminal-config.sh"
    
    if [ ! -f "$terminal_script" ]; then
        print_error "Terminal installation script not found: $terminal_script"
        log_step "Terminal installation" "failed - script not found"
        return 1
    fi
    
    print_progress "Running terminal configuration installer..."
    
    if bash "$terminal_script"; then
        TERMINAL_INSTALLED=true
        update_state "terminal" true
        log_step "Terminal installation" "completed successfully"
        print_status "Terminal purple configuration installed successfully"
        return 0
    else
        log_step "Terminal installation" "failed"
        print_error "Terminal configuration installation failed"
        return 1
    fi
}

# Install System component
install_system_component() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_warning "System integration is only available on macOS"
        return 0
    fi
    
    print_section "Installing System Integration"
    
    log_step "System integration" "started"
    
    local system_script="$SCRIPT_DIR/scripts/install-system-integration.sh"
    
    if [ ! -f "$system_script" ]; then
        print_error "System integration script not found: $system_script"
        log_step "System integration" "failed - script not found"
        return 1
    fi
    
    print_progress "Running system integration installer..."
    
    if bash "$system_script"; then
        SYSTEM_INSTALLED=true
        update_state "system" true
        log_step "System integration" "completed successfully"
        print_status "System integration installed successfully"
        return 0
    else
        log_step "System integration" "failed"
        print_error "System integration installation failed"
        return 1
    fi
}

# Handle installation failure
handle_installation_failure() {
    local failed_component="$1"
    
    print_error "Installation of $failed_component failed!"
    echo
    
    print_warning "Options:"
    echo "  [C]ontinue - Continue with remaining components"
    echo "  [R]ollback - Undo all changes and exit"
    echo "  [Q]uit     - Exit without rollback (manual cleanup required)"
    echo
    
    while true; do
        read -p "What would you like to do? [C/R/Q]: " -n 1 -r choice
        echo
        
        case "$choice" in
            [Cc])
                print_info "Continuing with remaining components..."
                return 0
                ;;
            [Rr])
                print_info "Rolling back all changes..."
                if [ -f "$ROLLBACK_SCRIPT" ]; then
                    bash "$ROLLBACK_SCRIPT"
                fi
                exit 1
                ;;
            [Qq])
                print_warning "Exiting without rollback"
                print_info "Use ~/.config/purple-theme/rollback.sh to undo changes later"
                exit 1
                ;;
            *)
                print_warning "Invalid choice. Please select C, R, or Q."
                ;;
        esac
    done
}

# Show installation summary
show_installation_summary() {
    print_section "Installation Summary"
    
    local installed_count=0
    local total_attempted=0
    
    echo "Component installation results:"
    echo
    
    if [ "$VSCODE_INSTALLED" = true ]; then
        print_status "VS Code Purple Theme - Installed"
        ((installed_count++))
    elif [ "$VSCODE_INSTALLED" = false ] && [[ " $* " =~ " vscode " ]]; then
        print_error "VS Code Purple Theme - Failed"
    fi
    
    if [ "$TERMINAL_INSTALLED" = true ]; then
        print_status "Terminal Purple Configuration - Installed"
        ((installed_count++))
    elif [ "$TERMINAL_INSTALLED" = false ] && [[ " $* " =~ " terminal " ]]; then
        print_error "Terminal Purple Configuration - Failed"
    fi
    
    if [ "$SYSTEM_INSTALLED" = true ]; then
        print_status "System Integration - Installed"
        ((installed_count++))
    elif [ "$SYSTEM_INSTALLED" = false ] && [[ " $* " =~ " system " ]]; then
        print_error "System Integration - Failed"
    fi
    
    # Count total attempted
    for component in "$@"; do
        ((total_attempted++))
    done
    
    echo
    if [ $installed_count -eq $total_attempted ] && [ $total_attempted -gt 0 ]; then
        echo -e "${GREEN}🎉 Installation completed successfully!${NC}"
        echo -e "${GREEN}All $installed_count component(s) installed successfully.${NC}"
        update_state "all" true
    elif [ $installed_count -gt 0 ]; then
        echo -e "${YELLOW}⚠ Partial installation completed${NC}"
        echo -e "${YELLOW}$installed_count of $total_attempted component(s) installed successfully.${NC}"
    else
        echo -e "${RED}✗ Installation failed${NC}"
        echo -e "${RED}No components were installed successfully.${NC}"
        return 1
    fi
    
    return 0
}

# Show post-installation instructions
show_post_installation_instructions() {
    print_section "Post-Installation Instructions"
    
    echo "To complete the purple theme setup:"
    echo
    
    if [ "$VSCODE_INSTALLED" = true ]; then
        echo "VS Code:"
        echo "  • Restart VS Code to see the purple theme"
        echo "  • The theme should be automatically activated"
        echo "  • If not, go to File > Preferences > Color Theme > Purple Development Theme"
        echo
    fi
    
    if [ "$TERMINAL_INSTALLED" = true ]; then
        echo "Terminal:"
        echo "  • Restart your terminal or run: source ~/.$(basename "$SHELL")rc"
        echo "  • For Terminal.app: Set 'Purple Theme' as default in Preferences"
        echo "  • For iTerm2: Select 'Purple Theme' color preset in Preferences"
        echo
    fi
    
    if [ "$SYSTEM_INSTALLED" = true ]; then
        echo "System (macOS):"
        echo "  • System changes are applied immediately"
        echo "  • Some changes may require logging out and back in"
        echo "  • Terminal.app profile must be set manually in preferences"
        echo
    fi
    
    echo "Available utilities:"
    echo "  ~/.config/purple-theme/rollback.sh        - Uninstall all components"
    if [ "$SYSTEM_INSTALLED" = true ]; then
        echo "  ~/.config/purple-theme/system-status.sh   - Check system theme status"
    fi
    if [ "$TERMINAL_INSTALLED" = true ]; then
        echo "  ~/.config/purple-theme/test-shell-config.sh - Test terminal colors"
    fi
    echo
    
    echo "For support or issues:"
    echo "  • Check installation log: ~/.config/purple-theme/installation.log"
    echo "  • Review component documentation in the purple-theme-extension directory"
    echo
}

# Main installation process
main() {
    local components=()
    local install_all=false
    
    # Initialize logging
    init_logging
    log_step "Installation" "started"
    
    # Check prerequisites
    if ! check_prerequisites; then
        print_error "Prerequisites check failed"
        log_step "Prerequisites" "failed"
        exit 1
    fi
    log_step "Prerequisites" "passed"
    
    # Show options and get user choice
    show_installation_options
    
    if get_installation_choice; then
        # Full installation
        install_all=true
        components=("vscode" "terminal")
        if [[ "$OSTYPE" == "darwin"* ]]; then
            components+=("system")
        fi
        print_info "Selected: Full installation (${#components[@]} components)"
    else
        # Custom installation
        components=($(get_custom_components))
        print_info "Selected: Custom installation (${#components[@]} components)"
    fi
    
    if [ ${#components[@]} -eq 0 ]; then
        print_warning "No components selected"
        exit 0
    fi
    
    echo
    print_info "Components to install: ${components[*]}"
    echo
    
    # Confirm installation
    read -p "Proceed with installation? [Y/n]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Installation cancelled by user"
        exit 0
    fi
    
    # Create rollback script before starting installation
    create_rollback_script
    
    # Install components
    local failed_components=()
    
    for component in "${components[@]}"; do
        case "$component" in
            "vscode")
                if ! install_vscode_component; then
                    failed_components+=("vscode")
                    handle_installation_failure "VS Code theme"
                fi
                ;;
            "terminal")
                if ! install_terminal_component; then
                    failed_components+=("terminal")
                    handle_installation_failure "Terminal configuration"
                fi
                ;;
            "system")
                if ! install_system_component; then
                    failed_components+=("system")
                    handle_installation_failure "System integration"
                fi
                ;;
            *)
                print_warning "Unknown component: $component"
                ;;
        esac
    done
    
    # Show installation summary
    echo
    if show_installation_summary "${components[@]}"; then
        log_step "Installation" "completed successfully"
        show_post_installation_instructions
    else
        log_step "Installation" "completed with errors"
        print_info "Check installation log for details: $INSTALLATION_LOG"
        exit 1
    fi
}

# Handle script interruption
cleanup() {
    echo
    print_warning "Installation interrupted!"
    print_info "Use ~/.config/purple-theme/rollback.sh to undo any partial changes"
    log_step "Installation" "interrupted"
    exit 130
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run main function
main "$@"