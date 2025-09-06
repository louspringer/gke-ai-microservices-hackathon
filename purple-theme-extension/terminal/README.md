# Purple Terminal Theme Configurations

This directory contains purple color scheme configurations for various terminal emulators and shells.

## Color Palette

- **Background**: `#1A0D26` (Deep Purple)
- **Foreground**: `#E6E6FA` (Lavender)
- **Selection**: `#3D2A4F` (Medium Purple)
- **Cursor**: `#9370DB` (Medium Slate Blue)
- **Accent**: `#BA55D3` (Medium Orchid)

## Installation Instructions

### macOS Terminal.app

1. Double-click `Terminal-Purple.terminal` to import the theme
2. Go to Terminal > Preferences > Profiles
3. Select "Purple Theme" and click "Default"

### iTerm2

1. Go to iTerm2 > Preferences > Profiles > Colors
2. Click "Color Presets..." dropdown
3. Select "Import..." and choose `Purple-Theme.itermcolors`
4. Select the imported "Purple Theme" preset

### Hyper Terminal

1. Open your `~/.hyper.js` configuration file
2. Replace the config object with the contents from `hyper-purple-theme.js`
3. Restart Hyper terminal

### Windows Terminal

1. Open Windows Terminal settings (Ctrl+,)
2. Go to "Color schemes" in the left sidebar
3. Click "Add new" and paste the contents from `windows-terminal-purple.json`
4. Apply the "Purple Theme" to your desired profile

### Shell Configuration

#### For Zsh users:
```bash
# Add to your ~/.zshrc
source /path/to/purple-theme-extension/shell/zshrc-purple.sh
```

#### For Bash users:
```bash
# Add to your ~/.bashrc or ~/.bash_profile
source /path/to/purple-theme-extension/shell/bashrc-purple.sh
```

#### Universal shell colors:
```bash
# Add to any shell profile
source /path/to/purple-theme-extension/shell/purple-colors.sh
```

## Features

### Shell Enhancements
- Purple-themed prompts with git integration
- Custom ANSI color codes
- Enhanced completion styling
- Purple-themed aliases
- Color-coded file listings

### Terminal Features
- Consistent purple color scheme across all elements
- High contrast for readability
- Git status integration in prompts
- Custom scrollbar styling (where supported)
- Optimized for both light and dark environments

## Testing Your Installation

After installation, run these commands to test the theme:

```bash
# Test color palette
apply_purple_theme

# Test shell theme status
purple_status

# Test git integration (in a git repository)
git status
git log --oneline --graph

# Test file listings
ls -la
```

## Troubleshooting

### Colors not showing correctly
- Ensure your terminal supports 256 colors
- Check that the theme files are properly imported
- Restart your terminal application

### Prompt not updating
- Make sure you've sourced the shell configuration files
- Restart your shell session or open a new terminal tab
- Check that git is installed for git integration features

### Font rendering issues
- Install a monospace font that supports Unicode characters
- Recommended fonts: Menlo, Monaco, Consolas, or Fira Code

## Customization

You can customize the colors by editing the configuration files:

- Modify `purple-colors.sh` for shell color variables
- Edit terminal-specific files for application colors
- Adjust the color values to match your preferences

All color values use standard hex notation (`#RRGGBB`) or RGB values depending on the configuration format.