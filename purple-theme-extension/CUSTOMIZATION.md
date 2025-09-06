# Purple Development Theme - Customization Guide

This guide explains how to customize the Purple Development Theme to match your personal preferences and workflow needs.

## 🎨 Color Palette Customization

### Understanding the Color System

The Purple Development Theme uses a systematic color palette with specific roles:

```json
{
  "base": {
    "primary": "#1A0D26",    // Deep purple - main backgrounds
    "secondary": "#2D1B3D",  // Medium purple - secondary surfaces
    "tertiary": "#3D2A4F",   // Light purple - sidebars, panels
    "text": "#E6E6FA",       // Lavender - primary text
    "accent": "#8B008B"      // Dark magenta - highlights
  },
  "syntax": {
    "keywords": "#9370DB",   // Medium slate blue
    "strings": "#DDA0DD",    // Plum
    "comments": "#8A2BE2",   // Blue violet
    "functions": "#BA55D3",  // Medium orchid
    "variables": "#DA70D6"   // Orchid
  }
}
```

### Creating Color Variants

#### 1. Light Purple Variant
Create a lighter version of the theme:

```bash
# Copy the base theme
cp themes/purple-theme.json themes/purple-light-theme.json
```

Edit the new theme file:
```json
{
  "name": "Purple Development Theme (Light)",
  "type": "light",
  "colors": {
    "editor.background": "#F5F0FF",
    "editor.foreground": "#4A0E4E",
    "activityBar.background": "#E6D7FF",
    "sideBar.background": "#DCC9FF"
  }
}
```

#### 2. High Contrast Variant
For better accessibility:

```json
{
  "name": "Purple Development Theme (High Contrast)",
  "colors": {
    "editor.background": "#000000",
    "editor.foreground": "#FFFFFF",
    "activityBar.background": "#1A0D26",
    "sideBar.background": "#2D1B3D"
  }
}
```

### Modifying Existing Colors

#### VS Code Theme Colors
Edit `themes/purple-theme.json`:

```json
{
  "colors": {
    // Editor colors
    "editor.background": "#YOUR_COLOR_HERE",
    "editor.foreground": "#YOUR_TEXT_COLOR",
    
    // UI elements
    "activityBar.background": "#YOUR_SIDEBAR_COLOR",
    "statusBar.background": "#YOUR_STATUS_COLOR",
    
    // Selection and highlights
    "editor.selectionBackground": "#YOUR_SELECTION_COLOR",
    "editor.lineHighlightBackground": "#YOUR_HIGHLIGHT_COLOR"
  }
}
```

#### Terminal Colors
Edit `shell/purple-colors.sh`:

```bash
# Background colors
export PURPLE_BG="#1A0D26"          # Main background
export PURPLE_BG_LIGHT="#2D1B3D"    # Light background
export PURPLE_BG_DARK="#0F0519"     # Dark background

# Foreground colors
export PURPLE_FG="#E6E6FA"          # Main text
export PURPLE_FG_DIM="#B19CD9"      # Dimmed text
export PURPLE_FG_BRIGHT="#FFFFFF"   # Bright text

# Accent colors
export PURPLE_ACCENT="#9370DB"      # Primary accent
export PURPLE_ACCENT_BRIGHT="#BA55D3" # Bright accent
```

## 🖥️ VS Code Customization

### Adding New Token Colors

Edit `themes/purple-theme.json` to add syntax highlighting for specific languages:

```json
{
  "tokenColors": [
    {
      "name": "Python docstrings",
      "scope": "string.quoted.docstring.multi.python",
      "settings": {
        "foreground": "#DDA0DD",
        "fontStyle": "italic"
      }
    },
    {
      "name": "JavaScript template literals",
      "scope": "string.template.js",
      "settings": {
        "foreground": "#DA70D6"
      }
    },
    {
      "name": "CSS property names",
      "scope": "support.type.property-name.css",
      "settings": {
        "foreground": "#BA55D3"
      }
    }
  ]
}
```

### Customizing UI Elements

```json
{
  "colors": {
    // Tabs
    "tab.activeBackground": "#3D2A4F",
    "tab.inactiveBackground": "#2D1B3D",
    "tab.activeForeground": "#E6E6FA",
    
    // Panels
    "panel.background": "#1A0D26",
    "panel.border": "#8B008B",
    
    // Terminal
    "terminal.background": "#1A0D26",
    "terminal.foreground": "#E6E6FA",
    "terminal.ansiPurple": "#9370DB",
    
    // Git decorations
    "gitDecoration.modifiedResourceForeground": "#DDA0DD",
    "gitDecoration.deletedResourceForeground": "#FF6B9D",
    "gitDecoration.untrackedResourceForeground": "#98FB98"
  }
}
```

### Creating Multiple Theme Variants

1. **Create variant files**:
   ```bash
   cp themes/purple-theme.json themes/purple-dark-theme.json
   cp themes/purple-theme.json themes/purple-vibrant-theme.json
   ```

2. **Update package.json**:
   ```json
   {
     "contributes": {
       "themes": [
         {
           "label": "Purple Development Theme",
           "uiTheme": "vs-dark",
           "path": "./themes/purple-theme.json"
         },
         {
           "label": "Purple Development Theme (Dark)",
           "uiTheme": "vs-dark",
           "path": "./themes/purple-dark-theme.json"
         },
         {
           "label": "Purple Development Theme (Vibrant)",
           "uiTheme": "vs-dark",
           "path": "./themes/purple-vibrant-theme.json"
         }
       ]
     }
   }
   ```

## 🖥️ Terminal Customization

### Customizing Shell Prompts

#### Zsh Prompt Customization
Edit `shell/zshrc-purple.sh`:

```bash
# Custom purple prompt with additional information
purple_prompt() {
    local purple_bg="%K{54}"    # Purple background
    local purple_fg="%F{183}"   # Light purple foreground
    local reset="%k%f"          # Reset colors
    
    # Add custom elements
    local time_info="%D{%H:%M:%S}"
    local user_info="%n@%m"
    local path_info="%~"
    local git_info="$(git_prompt_info)"
    
    # Build prompt
    PROMPT="${purple_bg}${purple_fg} ${time_info} ${user_info} ${path_info}${git_info} ${reset} "
}
```

#### Bash Prompt Customization
Edit `shell/bashrc-purple.sh`:

```bash
# Custom purple prompt for Bash
purple_prompt() {
    local purple_bg="\[\033[48;5;54m\]"
    local purple_fg="\[\033[38;5;183m\]"
    local reset="\[\033[0m\]"
    
    # Custom prompt elements
    local time_info="\t"
    local user_info="\u@\h"
    local path_info="\w"
    
    PS1="${purple_bg}${purple_fg} ${time_info} ${user_info} ${path_info} ${reset} "
}
```

### Adding Custom Aliases

Add to `shell/purple-colors.sh`:

```bash
# Purple-themed aliases
alias ll='ls -la --color=auto'
alias grep='grep --color=auto'
alias tree='tree -C'

# Git aliases with purple theme
alias gst='git status'
alias glog='git log --oneline --graph --decorate --color=always'
alias gdiff='git diff --color=always'

# Development aliases
alias code='code --color-theme "Purple Development Theme"'
alias vim='vim -c "colorscheme purple"'
```

### Terminal Emulator Specific Customization

#### iTerm2 Advanced Configuration
Create `terminal/iterm2-advanced-purple.json`:

```json
{
  "name": "Purple Theme Advanced",
  "background_color": "#1A0D26",
  "foreground_color": "#E6E6FA",
  "cursor_color": "#9370DB",
  "selection_color": "#3D2A4F",
  "bold_color": "#BA55D3",
  "link_color": "#DDA0DD",
  "ansi_colors": {
    "black": "#1A0D26",
    "red": "#FF6B9D",
    "green": "#98FB98",
    "yellow": "#FFD700",
    "blue": "#9370DB",
    "magenta": "#BA55D3",
    "cyan": "#40E0D0",
    "white": "#E6E6FA"
  },
  "bright_ansi_colors": {
    "bright_black": "#2D1B3D",
    "bright_red": "#FF8FA3",
    "bright_green": "#B3FFB3",
    "bright_yellow": "#FFED4E",
    "bright_blue": "#A78BFA",
    "bright_magenta": "#C77DFF",
    "bright_cyan": "#7FFFD4",
    "bright_white": "#FFFFFF"
  }
}
```

#### Windows Terminal Advanced Configuration
Create `terminal/windows-terminal-advanced.json`:

```json
{
  "name": "Purple Theme Advanced",
  "background": "#1A0D26",
  "foreground": "#E6E6FA",
  "cursorColor": "#9370DB",
  "selectionBackground": "#3D2A4F",
  "black": "#1A0D26",
  "red": "#FF6B9D",
  "green": "#98FB98",
  "yellow": "#FFD700",
  "blue": "#9370DB",
  "purple": "#BA55D3",
  "cyan": "#40E0D0",
  "white": "#E6E6FA",
  "brightBlack": "#2D1B3D",
  "brightRed": "#FF8FA3",
  "brightGreen": "#B3FFB3",
  "brightYellow": "#FFED4E",
  "brightBlue": "#A78BFA",
  "brightPurple": "#C77DFF",
  "brightCyan": "#7FFFD4",
  "brightWhite": "#FFFFFF"
}
```

## 🍎 macOS System Customization

### Advanced System Integration

Create `scripts/advanced-system-integration.sh`:

```bash
#!/bin/bash

# Advanced macOS purple system integration

# Set purple accent color (option 5 = purple)
defaults write -g AppleAccentColor -int 5

# Set highlight color to purple
defaults write -g AppleHighlightColor -string "0.584314 0.439216 0.859608"

# Configure Dock with purple tint
defaults write com.apple.dock tilesize -int 48
defaults write com.apple.dock magnification -bool true
defaults write com.apple.dock largesize -int 64

# Configure Finder sidebar
defaults write com.apple.finder SidebarWidth -int 200

# Set desktop picture to purple gradient (if available)
# osascript -e 'tell application "Finder" to set desktop picture to POSIX file "/path/to/purple-gradient.jpg"'

# Restart affected services
killall Dock
killall Finder
killall SystemUIServer
```

### Custom Desktop Wallpaper

Create a purple gradient wallpaper:

```bash
# Create purple gradient wallpaper using ImageMagick (if installed)
convert -size 2560x1600 gradient:'#1A0D26-#3D2A4F' ~/Desktop/purple-gradient.png

# Set as desktop wallpaper
osascript -e 'tell application "Finder" to set desktop picture to POSIX file "'$HOME'/Desktop/purple-gradient.png"'
```

## 🔧 Installation Script Customization

### Custom Installation Options

Edit `install.sh` to add custom installation modes:

```bash
# Add custom installation function
install_custom_variant() {
    local variant=$1
    echo "Installing $variant variant..."
    
    case $variant in
        "light")
            cp themes/purple-light-theme.json themes/purple-theme.json
            ;;
        "high-contrast")
            cp themes/purple-high-contrast-theme.json themes/purple-theme.json
            ;;
        "vibrant")
            cp themes/purple-vibrant-theme.json themes/purple-theme.json
            ;;
    esac
    
    # Continue with normal installation
    install_vscode_theme
}

# Add command line option parsing
while [[ $# -gt 0 ]]; do
    case $1 in
        --variant)
            VARIANT="$2"
            shift 2
            ;;
        --custom-colors)
            CUSTOM_COLORS="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
```

### Environment-Specific Configuration

```bash
# Detect environment and adjust installation
detect_environment() {
    if [[ "$TERM_PROGRAM" == "vscode" ]]; then
        echo "VS Code integrated terminal detected"
        INSTALL_VSCODE=true
        INSTALL_TERMINAL=false
    elif [[ "$TERM_PROGRAM" == "iTerm.app" ]]; then
        echo "iTerm2 detected"
        INSTALL_ITERM=true
    elif [[ "$TERM_PROGRAM" == "Apple_Terminal" ]]; then
        echo "Terminal.app detected"
        INSTALL_TERMINAL_APP=true
    fi
}
```

## 🧪 Testing Custom Themes

### Validation Script

Create `scripts/validate-custom-theme.sh`:

```bash
#!/bin/bash

# Validate custom theme configuration

validate_vscode_theme() {
    local theme_file="$1"
    
    # Check JSON syntax
    if ! jq empty "$theme_file" 2>/dev/null; then
        echo "❌ Invalid JSON in $theme_file"
        return 1
    fi
    
    # Check required fields
    if ! jq -e '.colors."editor.background"' "$theme_file" >/dev/null; then
        echo "❌ Missing editor.background color"
        return 1
    fi
    
    echo "✅ VS Code theme validation passed"
}

validate_terminal_colors() {
    # Test color variables
    source shell/purple-colors.sh
    
    if [[ -z "$PURPLE_BG" ]]; then
        echo "❌ Missing PURPLE_BG variable"
        return 1
    fi
    
    echo "✅ Terminal colors validation passed"
}

# Run validations
validate_vscode_theme "themes/purple-theme.json"
validate_terminal_colors
```

### Color Contrast Testing

```bash
# Test color contrast ratios
test_contrast() {
    local bg="$1"
    local fg="$2"
    
    # Use a contrast checking tool or online service
    echo "Testing contrast between $bg and $fg"
    # Implementation would depend on available tools
}

# Test all color combinations
test_contrast "#1A0D26" "#E6E6FA"  # Background/foreground
test_contrast "#2D1B3D" "#E6E6FA"  # Secondary background/text
```

## 📚 Advanced Customization Examples

### Corporate Branding

Adapt the theme for corporate purple branding:

```json
{
  "name": "Corporate Purple Theme",
  "colors": {
    "editor.background": "#2E1065",      // Corporate purple
    "activityBar.background": "#1A0B3D", // Darker corporate
    "statusBar.background": "#6B46C1"    // Brand accent
  }
}
```

### Accessibility Enhancements

```json
{
  "name": "Purple Theme (High Contrast)",
  "colors": {
    "editor.background": "#000000",
    "editor.foreground": "#FFFFFF",
    "editor.selectionBackground": "#FFFF00",
    "editorCursor.foreground": "#00FF00"
  }
}
```

### Language-Specific Customization

```json
{
  "tokenColors": [
    {
      "name": "Python specific",
      "scope": "source.python",
      "settings": {
        "foreground": "#E6E6FA"
      }
    },
    {
      "name": "JavaScript specific",
      "scope": "source.js",
      "settings": {
        "foreground": "#DDA0DD"
      }
    }
  ]
}
```

## 🔄 Updating and Maintaining Custom Themes

### Version Control for Customizations

```bash
# Initialize git repository for your customizations
git init
git add themes/ shell/ terminal/
git commit -m "Initial custom purple theme"

# Create branches for different variants
git checkout -b light-variant
git checkout -b high-contrast-variant
```

### Backup and Restore

```bash
# Backup current customizations
backup_customizations() {
    local backup_dir="$HOME/.config/purple-theme/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    cp -r themes/ "$backup_dir/"
    cp -r shell/ "$backup_dir/"
    cp -r terminal/ "$backup_dir/"
    
    echo "Customizations backed up to $backup_dir"
}

# Restore from backup
restore_customizations() {
    local backup_dir="$1"
    
    if [[ -d "$backup_dir" ]]; then
        cp -r "$backup_dir"/* ./
        echo "Customizations restored from $backup_dir"
    fi
}
```

---

**Happy customizing! 🎨** Remember to test your customizations thoroughly and keep backups of working configurations.