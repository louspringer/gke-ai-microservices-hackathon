# Purple Development Theme 🎨

A comprehensive purple theming solution that transforms your entire development environment with a cohesive purple color palette. This theme provides VS Code theming, terminal configuration, and system integration for a complete purple development experience.

![Purple Theme Preview](https://via.placeholder.com/800x400/1A0D26/E6E6FA?text=Purple+Development+Theme+Preview)

## ✨ Features

### 🎯 Complete Environment Theming
- **VS Code**: Custom purple theme with syntax highlighting
- **Terminal**: Purple color schemes for all major terminal emulators
- **System Integration**: macOS accent colors and system theming
- **Cross-Platform**: Support for macOS, Linux, and Windows terminals

### 🎨 Visual Excellence
- Dark purple backgrounds optimized for reduced eye strain
- High contrast syntax highlighting with carefully selected purple tones
- Consistent color palette across all development tools
- Professional appearance suitable for presentations and streaming

### 🚀 Easy Installation
- One-command installation with automatic configuration
- Comprehensive error handling and rollback functionality
- Backup and restore capabilities for safe installation
- Modular installation - choose only the components you need

## 📦 Quick Installation

### Automatic Installation (Recommended)
```bash
# Clone or download the theme
git clone https://github.com/your-username/purple-development-theme.git
cd purple-development-theme

# Run the installer
./install.sh
```

### Manual Installation
See [INSTALL.md](INSTALL.md) for detailed manual installation instructions.

## 🎨 Color Palette

Our carefully crafted purple palette ensures optimal readability and visual appeal:

| Element | Color | Hex Code | Usage |
|---------|-------|----------|-------|
| **Primary Background** | Deep Purple | `#1A0D26` | Editor background, main surfaces |
| **Secondary Background** | Medium Purple | `#2D1B3D` | Activity bar, panels |
| **Sidebar** | Lighter Purple | `#3D2A4F` | File explorer, sidebar |
| **Text** | Lavender | `#E6E6FA` | Primary text, code |
| **Keywords** | Medium Slate Blue | `#9370DB` | Language keywords |
| **Strings** | Plum | `#DDA0DD` | String literals |
| **Comments** | Blue Violet | `#8A2BE2` | Code comments |
| **Functions** | Medium Orchid | `#BA55D3` | Function names |
| **Variables** | Orchid | `#DA70D6` | Variable names |
| **Accent** | Dark Magenta | `#8B008B` | Highlights, selections |

### Color Accessibility
- **WCAG AA Compliant**: All text meets minimum contrast ratios
- **Color Blind Friendly**: Tested with various color vision deficiencies
- **Reduced Eye Strain**: Optimized for long coding sessions

## 📸 Screenshots

### VS Code Theme
![VS Code with Purple Theme](https://via.placeholder.com/800x500/1A0D26/E6E6FA?text=VS+Code+Purple+Theme)

*VS Code editor with purple theme showing syntax highlighting*

### Terminal Configuration
![Terminal with Purple Theme](https://via.placeholder.com/800x300/1A0D26/E6E6FA?text=Terminal+Purple+Theme)

*Terminal with purple color scheme and enhanced prompt*

### System Integration (macOS)
![macOS System Integration](https://via.placeholder.com/800x400/3D2A4F/E6E6FA?text=macOS+Purple+Integration)

*macOS system with purple accent colors*

## 🛠️ Components

### 1. VS Code Theme Extension
- **File**: `themes/purple-theme.json`
- **Features**: Complete VS Code color theme with syntax highlighting
- **Compatibility**: VS Code 1.74.0+
- **Installation**: Automatic via installer or manual extension installation

### 2. Terminal Configuration
- **Files**: `terminal/` directory with multiple terminal configurations
- **Supported Terminals**:
  - macOS Terminal.app
  - iTerm2
  - Hyper Terminal
  - Windows Terminal
  - Linux terminals (gnome-terminal, konsole, etc.)
- **Shell Support**: Zsh, Bash, Fish

### 3. System Integration (macOS)
- **Features**: System accent colors, Dock theming, Finder integration
- **Requirements**: macOS 10.14+
- **Permissions**: May require system preferences access

## ⚙️ Customization

### Modifying Colors
1. **VS Code Theme**: Edit `themes/purple-theme.json`
2. **Terminal Colors**: Modify `shell/purple-colors.sh`
3. **System Colors**: Adjust `scripts/install-system-integration.sh`

### Creating Color Variants
```bash
# Copy the base theme
cp themes/purple-theme.json themes/purple-light-theme.json

# Edit the new theme file
# Update the "name" field and color values
# Add to package.json contributes.themes array
```

### Custom Installation
```bash
# Install only VS Code theme
./scripts/install-vscode-theme.sh

# Install only terminal configuration
./scripts/install-terminal-config.sh

# Install only system integration (macOS)
./scripts/install-system-integration.sh
```

## 🔧 Troubleshooting

### Common Issues

#### VS Code Theme Not Applied
**Problem**: Theme doesn't appear or isn't applied after installation

**Solutions**:
1. **Restart VS Code completely**
   ```bash
   # Kill all VS Code processes
   pkill -f "Visual Studio Code"
   # Restart VS Code
   code
   ```

2. **Manual theme selection**
   - Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
   - Type "Preferences: Color Theme"
   - Select "Purple Development Theme"

3. **Check extension installation**
   ```bash
   # Verify theme files exist
   ls -la ~/.vscode/extensions/purple-development-theme-*/
   
   # Check VS Code extension list
   code --list-extensions | grep purple
   ```

4. **Reinstall VS Code theme only**
   ```bash
   ./scripts/install-vscode-theme.sh --force
   ```

#### Terminal Colors Not Working
**Problem**: Terminal doesn't show purple colors or prompt changes

**Solutions**:
1. **Restart terminal application**
   - Close all terminal windows
   - Quit terminal application completely
   - Reopen terminal

2. **Source shell configuration**
   ```bash
   # For Zsh users
   source ~/.zshrc
   
   # For Bash users
   source ~/.bashrc
   # or
   source ~/.bash_profile
   ```

3. **Check color support**
   ```bash
   # Test terminal color support
   echo $TERM
   tput colors
   
   # Should show 256 or higher
   ```

4. **Test color configuration**
   ```bash
   # Run color test script
   ~/.config/purple-theme/test-shell-config.sh
   ```

5. **Manual terminal theme import**
   - **Terminal.app**: Double-click `terminal/Terminal-Purple.terminal`
   - **iTerm2**: Import `terminal/Purple-Theme.itermcolors` via Preferences

#### System Integration Issues (macOS)
**Problem**: System colors or accent colors not applied

**Solutions**:
1. **Check system permissions**
   - Go to System Preferences > Security & Privacy > Privacy
   - Ensure Terminal has "Full Disk Access" if needed

2. **Log out and back in**
   - Some system changes require a fresh login session
   - Log out of macOS and log back in

3. **Manual system preference changes**
   ```bash
   # Check current accent color
   defaults read -g AppleAccentColor
   
   # Set purple accent manually
   defaults write -g AppleAccentColor -int 5
   ```

4. **Check system status**
   ```bash
   ~/.config/purple-theme/system-status.sh
   ```

#### Installation Fails
**Problem**: Installation script encounters errors

**Solutions**:
1. **Check installation log**
   ```bash
   cat ~/.config/purple-theme/installation.log
   ```

2. **Run with verbose output**
   ```bash
   ./install.sh --verbose
   ```

3. **Check permissions**
   ```bash
   # Ensure script is executable
   chmod +x install.sh
   
   # Check write permissions
   ls -la ~/.vscode/extensions/
   ls -la ~/.config/
   ```

4. **Clean installation**
   ```bash
   # Remove any partial installation
   ~/.config/purple-theme/rollback.sh
   
   # Try installation again
   ./install.sh
   ```

5. **Component-specific installation**
   ```bash
   # Try installing components individually
   ./scripts/install-vscode-theme.sh
   ./scripts/install-terminal-config.sh
   ./scripts/install-system-integration.sh
   ```

### Advanced Troubleshooting

#### VS Code Extension Development Mode
```bash
# Link extension for development
ln -s "$(pwd)" ~/.vscode/extensions/purple-development-theme-dev

# Reload VS Code window
# Press Cmd+R (macOS) or Ctrl+R (Windows/Linux)
```

#### Terminal Color Debugging
```bash
# Test ANSI colors
for i in {0..255}; do
    printf "\x1b[48;5;%sm%3d\e[0m " "$i" "$i"
    if (( i == 15 )) || (( i > 15 )) && (( (i-15) % 6 == 0 )); then
        printf "\n"
    fi
done
```

#### System Integration Debugging (macOS)
```bash
# Check system preferences
defaults read -g | grep -i accent
defaults read -g | grep -i appearance

# Reset system preferences (use with caution)
defaults delete -g AppleAccentColor
defaults delete -g AppleInterfaceStyle
```

## 🗑️ Uninstallation

### Complete Removal
```bash
# Run the rollback script created during installation
~/.config/purple-theme/rollback.sh
```

### Manual Removal
```bash
# Remove VS Code extension
rm -rf ~/.vscode/extensions/purple-development-theme-*

# Remove terminal configuration
# Edit ~/.zshrc or ~/.bashrc and remove purple theme lines

# Remove system integration (macOS)
defaults delete -g AppleAccentColor

# Clean up installation files
rm -rf ~/.config/purple-theme/
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Reporting Issues
1. Check existing issues first
2. Provide detailed reproduction steps
3. Include system information (OS, terminal, VS Code version)
4. Attach screenshots if applicable

### Adding Terminal Support
1. Create configuration file in `terminal/` directory
2. Add installation logic to `scripts/install-terminal-config.sh`
3. Update documentation
4. Test on target platform

### Color Palette Improvements
1. Ensure WCAG AA compliance
2. Test with color vision simulators
3. Maintain consistency across components
4. Document color usage rationale

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Color palette inspired by various purple themes in the community
- Terminal configuration techniques from popular shell frameworks
- VS Code theme structure based on official theme guidelines

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/purple-development-theme/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/purple-development-theme/discussions)
- **Email**: support@purple-theme.dev

---

**Enjoy your purple development environment! 🎨✨**