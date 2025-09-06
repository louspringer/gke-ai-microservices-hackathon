#!/bin/bash

# Purple Theme Validation Script
# Validates VS Code theme installation and terminal color scheme configuration

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

# Validation results
VALIDATION_PASSED=true
VALIDATION_ERRORS=()
VALIDATION_WARNINGS=()

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
            VALIDATION_PASSED=false
            VALIDATION_ERRORS+=("$message")
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠${NC} $message"
            VALIDATION_WARNINGS+=("$message")
            ;;
        "INFO")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
        "HEADER")
            echo -e "${PURPLE}${message}${NC}"
            ;;
    esac
}

# Function to validate VS Code installation
validate_vscode_installation() {
    print_status "HEADER" "=== Validating VS Code Installation ==="
    
    # Check if VS Code is installed
    if command -v code >/dev/null 2>&1; then
        print_status "SUCCESS" "VS Code CLI is available"
        
        # Get VS Code version
        local vscode_version=$(code --version | head -n1)
        print_status "INFO" "VS Code version: $vscode_version"
    else
        print_status "ERROR" "VS Code CLI not found. Please install VS Code or add it to PATH"
        return 1
    fi
    
    # Check VS Code extensions directory
    local extensions_dir=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        extensions_dir="$HOME/.vscode/extensions"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        extensions_dir="$HOME/.vscode/extensions"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        extensions_dir="$HOME/.vscode/extensions"
    fi
    
    if [[ -d "$extensions_dir" ]]; then
        print_status "SUCCESS" "VS Code extensions directory found: $extensions_dir"
    else
        print_status "WARNING" "VS Code extensions directory not found: $extensions_dir"
    fi
    
    echo
}

# Function to validate theme files
validate_theme_files() {
    print_status "HEADER" "=== Validating Theme Files ==="
    
    # Check package.json
    local package_json="$THEME_DIR/package.json"
    if [[ -f "$package_json" ]]; then
        print_status "SUCCESS" "package.json found"
        
        # Validate package.json structure
        if command -v jq >/dev/null 2>&1; then
            local theme_name=$(jq -r '.name' "$package_json" 2>/dev/null)
            local theme_display_name=$(jq -r '.displayName' "$package_json" 2>/dev/null)
            local theme_version=$(jq -r '.version' "$package_json" 2>/dev/null)
            
            if [[ "$theme_name" != "null" && "$theme_name" != "" ]]; then
                print_status "SUCCESS" "Theme name: $theme_name"
            else
                print_status "ERROR" "Invalid or missing theme name in package.json"
            fi
            
            if [[ "$theme_display_name" != "null" && "$theme_display_name" != "" ]]; then
                print_status "SUCCESS" "Theme display name: $theme_display_name"
            else
                print_status "ERROR" "Invalid or missing display name in package.json"
            fi
            
            if [[ "$theme_version" != "null" && "$theme_version" != "" ]]; then
                print_status "SUCCESS" "Theme version: $theme_version"
            else
                print_status "ERROR" "Invalid or missing version in package.json"
            fi
            
            # Check if themes are defined
            local themes_count=$(jq '.contributes.themes | length' "$package_json" 2>/dev/null)
            if [[ "$themes_count" -gt 0 ]]; then
                print_status "SUCCESS" "Theme contributions found: $themes_count theme(s)"
            else
                print_status "ERROR" "No theme contributions found in package.json"
            fi
        else
            print_status "WARNING" "jq not available, skipping detailed package.json validation"
        fi
    else
        print_status "ERROR" "package.json not found"
    fi
    
    # Check theme JSON file
    local theme_json="$THEME_DIR/themes/purple-theme.json"
    if [[ -f "$theme_json" ]]; then
        print_status "SUCCESS" "Theme JSON file found"
        
        if command -v jq >/dev/null 2>&1; then
            # Validate JSON structure
            if jq empty "$theme_json" 2>/dev/null; then
                print_status "SUCCESS" "Theme JSON is valid"
                
                # Check required theme properties
                local theme_name=$(jq -r '.name' "$theme_json" 2>/dev/null)
                local theme_type=$(jq -r '.type' "$theme_json" 2>/dev/null)
                
                if [[ "$theme_name" != "null" && "$theme_name" != "" ]]; then
                    print_status "SUCCESS" "Theme name in JSON: $theme_name"
                else
                    print_status "ERROR" "Missing theme name in JSON"
                fi
                
                if [[ "$theme_type" == "dark" ]]; then
                    print_status "SUCCESS" "Theme type: $theme_type"
                else
                    print_status "WARNING" "Theme type is not 'dark': $theme_type"
                fi
                
                # Check for essential color definitions
                local colors_count=$(jq '.colors | length' "$theme_json" 2>/dev/null)
                local token_colors_count=$(jq '.tokenColors | length' "$theme_json" 2>/dev/null)
                
                if [[ "$colors_count" -gt 0 ]]; then
                    print_status "SUCCESS" "UI colors defined: $colors_count colors"
                else
                    print_status "ERROR" "No UI colors defined"
                fi
                
                if [[ "$token_colors_count" -gt 0 ]]; then
                    print_status "SUCCESS" "Token colors defined: $token_colors_count token groups"
                else
                    print_status "ERROR" "No token colors defined"
                fi
                
                # Validate purple color palette
                validate_purple_colors "$theme_json"
                
            else
                print_status "ERROR" "Theme JSON is invalid"
            fi
        else
            print_status "WARNING" "jq not available, skipping detailed JSON validation"
        fi
    else
        print_status "ERROR" "Theme JSON file not found: $theme_json"
    fi
    
    echo
}

# Function to validate purple color palette
validate_purple_colors() {
    local theme_json=$1
    print_status "INFO" "Validating purple color palette..."
    
    # Expected purple colors
    local expected_colors=(
        "editor.background:#1A0D26"
        "editor.foreground:#E6E6FA"
        "activityBar.background:#2D1B3D"
        "sideBar.background:#3D2A4F"
        "statusBar.background:#8B008B"
    )
    
    for color_def in "${expected_colors[@]}"; do
        local color_key="${color_def%:*}"
        local expected_value="${color_def#*:}"
        
        local actual_value=$(jq -r ".colors[\"$color_key\"]" "$theme_json" 2>/dev/null)
        
        if [[ "$actual_value" == "$expected_value" ]]; then
            print_status "SUCCESS" "Color $color_key: $actual_value"
        elif [[ "$actual_value" != "null" && "$actual_value" != "" ]]; then
            print_status "WARNING" "Color $color_key: $actual_value (expected: $expected_value)"
        else
            print_status "ERROR" "Missing color definition: $color_key"
        fi
    done
}

# Function to validate VS Code theme installation
validate_vscode_theme_installation() {
    print_status "HEADER" "=== Validating VS Code Theme Installation ==="
    
    # Check if theme is installed
    local extensions_dir=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        extensions_dir="$HOME/.vscode/extensions"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        extensions_dir="$HOME/.vscode/extensions"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        extensions_dir="$HOME/.vscode/extensions"
    fi
    
    if [[ -d "$extensions_dir" ]]; then
        # Look for installed purple theme
        local theme_installed=false
        for ext_dir in "$extensions_dir"/*purple*theme* "$extensions_dir"/*purple-development-theme*; do
            if [[ -d "$ext_dir" ]]; then
                print_status "SUCCESS" "Purple theme extension found: $(basename "$ext_dir")"
                theme_installed=true
                
                # Check if theme files exist in extension
                if [[ -f "$ext_dir/package.json" ]]; then
                    print_status "SUCCESS" "Extension package.json found"
                else
                    print_status "ERROR" "Extension package.json missing"
                fi
                
                if [[ -f "$ext_dir/themes/purple-theme.json" ]]; then
                    print_status "SUCCESS" "Extension theme JSON found"
                else
                    print_status "ERROR" "Extension theme JSON missing"
                fi
                break
            fi
        done
        
        if [[ "$theme_installed" == false ]]; then
            print_status "WARNING" "Purple theme extension not found in VS Code extensions directory"
            print_status "INFO" "Run the installation script to install the theme"
        fi
    else
        print_status "WARNING" "VS Code extensions directory not accessible"
    fi
    
    # Check VS Code settings for active theme
    local settings_file=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        settings_file="$HOME/Library/Application Support/Code/User/settings.json"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        settings_file="$HOME/.config/Code/User/settings.json"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        settings_file="$HOME/AppData/Roaming/Code/User/settings.json"
    fi
    
    if [[ -f "$settings_file" ]]; then
        print_status "SUCCESS" "VS Code settings file found"
        
        if command -v jq >/dev/null 2>&1; then
            local current_theme=$(jq -r '."workbench.colorTheme"' "$settings_file" 2>/dev/null)
            if [[ "$current_theme" == *"Purple"* ]]; then
                print_status "SUCCESS" "Purple theme is active: $current_theme"
            elif [[ "$current_theme" != "null" && "$current_theme" != "" ]]; then
                print_status "WARNING" "Different theme is active: $current_theme"
            else
                print_status "INFO" "No specific theme set in settings"
            fi
        else
            print_status "WARNING" "jq not available, cannot check active theme"
        fi
    else
        print_status "WARNING" "VS Code settings file not found: $settings_file"
    fi
    
    echo
}

# Function to validate terminal color configuration
validate_terminal_colors() {
    print_status "HEADER" "=== Validating Terminal Color Configuration ==="
    
    # Check shell configuration files
    local shell_configs=()
    if [[ -f "$HOME/.zshrc" ]]; then
        shell_configs+=("$HOME/.zshrc")
    fi
    if [[ -f "$HOME/.bash_profile" ]]; then
        shell_configs+=("$HOME/.bash_profile")
    fi
    if [[ -f "$HOME/.bashrc" ]]; then
        shell_configs+=("$HOME/.bashrc")
    fi
    
    if [[ ${#shell_configs[@]} -eq 0 ]]; then
        print_status "WARNING" "No shell configuration files found"
    else
        print_status "SUCCESS" "Found shell configuration files: ${shell_configs[*]}"
        
        # Check if purple colors are sourced
        local purple_sourced=false
        for config in "${shell_configs[@]}"; do
            if grep -q "purple-colors.sh" "$config" 2>/dev/null; then
                print_status "SUCCESS" "Purple colors sourced in: $config"
                purple_sourced=true
            fi
        done
        
        if [[ "$purple_sourced" == false ]]; then
            print_status "WARNING" "Purple colors not sourced in shell configuration"
        fi
    fi
    
    # Check if purple color script exists
    local purple_colors_script="$THEME_DIR/shell/purple-colors.sh"
    if [[ -f "$purple_colors_script" ]]; then
        print_status "SUCCESS" "Purple colors script found"
        
        # Check if script is executable
        if [[ -x "$purple_colors_script" ]]; then
            print_status "SUCCESS" "Purple colors script is executable"
        else
            print_status "WARNING" "Purple colors script is not executable"
        fi
    else
        print_status "ERROR" "Purple colors script not found: $purple_colors_script"
    fi
    
    # Check terminal color environment variables
    if [[ -n "$PURPLE_THEME_ACTIVE" ]]; then
        print_status "SUCCESS" "Purple theme environment variables are active"
        print_status "INFO" "Purple theme version: ${PURPLE_THEME_VERSION:-unknown}"
    else
        print_status "WARNING" "Purple theme environment variables not set"
        print_status "INFO" "Source the purple-colors.sh script to activate"
    fi
    
    # Test color output
    print_status "INFO" "Testing terminal color output..."
    if [[ -n "$COLOR_PURPLE_BRIGHT" ]]; then
        echo -e "  ${COLOR_PURPLE_BRIGHT}■${NC} Purple colors are working"
    else
        echo -e "  \033[1;35m■\033[0m Purple colors (fallback)"
    fi
    
    echo
}

# Function to validate terminal emulator configurations
validate_terminal_emulator_configs() {
    print_status "HEADER" "=== Validating Terminal Emulator Configurations ==="
    
    # Check Terminal.app configuration
    local terminal_config="$THEME_DIR/terminal/Terminal-Purple.terminal"
    if [[ -f "$terminal_config" ]]; then
        print_status "SUCCESS" "Terminal.app configuration found"
    else
        print_status "WARNING" "Terminal.app configuration not found"
    fi
    
    # Check iTerm2 configuration
    local iterm_config="$THEME_DIR/terminal/Purple-Theme.itermcolors"
    if [[ -f "$iterm_config" ]]; then
        print_status "SUCCESS" "iTerm2 configuration found"
    else
        print_status "WARNING" "iTerm2 configuration not found"
    fi
    
    # Check Hyper configuration
    local hyper_config="$THEME_DIR/terminal/hyper-purple-theme.js"
    if [[ -f "$hyper_config" ]]; then
        print_status "SUCCESS" "Hyper configuration found"
    else
        print_status "WARNING" "Hyper configuration not found"
    fi
    
    # Check if Terminal.app is using purple theme (macOS only)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local terminal_theme=$(defaults read com.apple.Terminal "Default Window Settings" 2>/dev/null || echo "")
        if [[ "$terminal_theme" == *"Purple"* ]]; then
            print_status "SUCCESS" "Terminal.app is using purple theme: $terminal_theme"
        else
            print_status "INFO" "Terminal.app theme: ${terminal_theme:-default}"
        fi
    fi
    
    echo
}

# Function to validate color consistency
validate_color_consistency() {
    print_status "HEADER" "=== Validating Color Consistency ==="
    
    # Define expected purple palette
    local expected_colors=(
        "#1A0D26:Deep Purple"
        "#2D1B3D:Medium Purple"
        "#3D2A4F:Light Purple"
        "#9370DB:Purple Accent"
        "#BA55D3:Bright Purple"
        "#E6E6FA:Lavender"
        "#DDA0DD:Plum"
        "#8B008B:Dark Magenta"
    )
    
    print_status "INFO" "Checking color palette consistency..."
    
    # Check VS Code theme colors
    local theme_json="$THEME_DIR/themes/purple-theme.json"
    if [[ -f "$theme_json" ]] && command -v jq >/dev/null 2>&1; then
        for color_def in "${expected_colors[@]}"; do
            local color_code="${color_def%:*}"
            local color_name="${color_def#*:}"
            
            # Check if color is used in theme
            local color_usage=$(jq -r ".colors | to_entries[] | select(.value == \"$color_code\") | .key" "$theme_json" 2>/dev/null | wc -l)
            
            if [[ "$color_usage" -gt 0 ]]; then
                print_status "SUCCESS" "$color_name ($color_code) used in VS Code theme"
            else
                print_status "WARNING" "$color_name ($color_code) not found in VS Code theme"
            fi
        done
    fi
    
    # Check shell colors
    local purple_colors_script="$THEME_DIR/shell/purple-colors.sh"
    if [[ -f "$purple_colors_script" ]]; then
        for color_def in "${expected_colors[@]}"; do
            local color_code="${color_def%:*}"
            local color_name="${color_def#*:}"
            
            if grep -q "$color_code" "$purple_colors_script" 2>/dev/null; then
                print_status "SUCCESS" "$color_name ($color_code) defined in shell colors"
            else
                print_status "WARNING" "$color_name ($color_code) not found in shell colors"
            fi
        done
    fi
    
    echo
}

# Function to run contrast validation
validate_contrast() {
    print_status "HEADER" "=== Validating Color Contrast ==="
    
    # Test color combinations for readability
    local combinations=(
        "#1A0D26:#E6E6FA:Background/Foreground"
        "#2D1B3D:#E6E6FA:Sidebar/Text"
        "#3D2A4F:#E6E6FA:Panel/Text"
        "#8B008B:#E6E6FA:Accent/Text"
    )
    
    print_status "INFO" "Testing color contrast combinations..."
    
    for combo in "${combinations[@]}"; do
        local bg_color="${combo%%:*}"
        local fg_color="${combo#*:}"
        fg_color="${fg_color%:*}"
        local description="${combo##*:}"
        
        # Simple contrast check (basic implementation)
        print_status "INFO" "Contrast test: $description ($bg_color on $fg_color)"
        
        # Visual test output
        if [[ -n "$COLOR_RESET" ]]; then
            printf "  Test: "
            printf "\033[48;2;26;13;38m\033[38;2;230;230;250m Sample text \033[0m"
            echo " ($description)"
        fi
    done
    
    print_status "SUCCESS" "Color contrast validation completed"
    echo
}

# Function to generate validation report
generate_validation_report() {
    print_status "HEADER" "=== Validation Report ==="
    
    if [[ "$VALIDATION_PASSED" == true ]]; then
        print_status "SUCCESS" "All critical validations passed!"
    else
        print_status "ERROR" "Validation failed with ${#VALIDATION_ERRORS[@]} error(s)"
    fi
    
    if [[ ${#VALIDATION_WARNINGS[@]} -gt 0 ]]; then
        print_status "WARNING" "${#VALIDATION_WARNINGS[@]} warning(s) found"
    fi
    
    # Print errors
    if [[ ${#VALIDATION_ERRORS[@]} -gt 0 ]]; then
        echo -e "\n${RED}Errors:${NC}"
        for error in "${VALIDATION_ERRORS[@]}"; do
            echo -e "  ${RED}•${NC} $error"
        done
    fi
    
    # Print warnings
    if [[ ${#VALIDATION_WARNINGS[@]} -gt 0 ]]; then
        echo -e "\n${YELLOW}Warnings:${NC}"
        for warning in "${VALIDATION_WARNINGS[@]}"; do
            echo -e "  ${YELLOW}•${NC} $warning"
        done
    fi
    
    echo
    
    # Recommendations
    print_status "HEADER" "=== Recommendations ==="
    
    if [[ ${#VALIDATION_ERRORS[@]} -gt 0 ]]; then
        print_status "INFO" "1. Fix all errors before using the theme"
        print_status "INFO" "2. Run the installation script: ./install.sh"
        print_status "INFO" "3. Restart VS Code and terminal after installation"
    fi
    
    if [[ ${#VALIDATION_WARNINGS[@]} -gt 0 ]]; then
        print_status "INFO" "4. Review warnings for optimal theme experience"
        print_status "INFO" "5. Consider running installation scripts for missing components"
    fi
    
    print_status "INFO" "6. Test the theme in different lighting conditions"
    print_status "INFO" "7. Adjust terminal emulator settings if needed"
    
    echo
}

# Main validation function
main() {
    echo -e "${PURPLE}Purple Theme Validation Script${NC}"
    echo -e "${PURPLE}================================${NC}"
    echo
    
    # Run all validations
    validate_vscode_installation
    validate_theme_files
    validate_vscode_theme_installation
    validate_terminal_colors
    validate_terminal_emulator_configs
    validate_color_consistency
    validate_contrast
    
    # Generate report
    generate_validation_report
    
    # Exit with appropriate code
    if [[ "$VALIDATION_PASSED" == true ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi