# Purple Development Theme Installation Guide

Welcome to the comprehensive installation guide for the Purple Development Theme! This guide will help you set up a complete purple development environment.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation Options](#installation-options)
- [Step-by-Step Installation](#step-by-step-installation)
- [Post-Installation](#post-installation)
- [Troubleshooting](#troubleshooting)
- [Additional Resources](#additional-resources)

## 🚀 Quick Start

For most users, the automatic installation is the fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/your-username/purple-development-theme.git
cd purple-development-theme

# Run the installer
./install.sh
```

The installer will guide you through the process and automatically configure all components.

## ✅ Prerequisites

Before installation, ensure you have:

### Required
- **macOS 10.14+**, **Linux**, or **Windows 10+**
- **VS Code 1.74.0+** (for VS Code theme)
- **Terminal application** (Terminal.app, iTerm2, Windows Terminal, etc.)
- **Bash or Zsh shell** (for terminal configuration)

### Optional
- **Git** (for enhanced terminal prompts with git integration)
- **Python 3** (for advanced JSON processing during installation)
- **10MB free disk space**

### Platform-Specific Requirements

#### macOS
- **Full feature support** including system integration
- **Terminal.app** or **iTerm2** recommended
- **Zsh** (default in macOS 10.15+) or **Bash**

#### Linux
- **VS Code and terminal theming** (system integration not available)
- **256-color terminal support** required
- **Package manager access** for installing dependencies

#### Windows
- **Windows Terminal** recommended for best experience
- **WSL** (Windows Subsystem for Linux) for full terminal features
- **PowerShell 5.1+** or **PowerShell Core 7+**

## 🎯 Installation Options

The installer provides flexible installation modes:

### 1. Full Installation (Recommended)
Installs all available components for your platform:
- ✅ VS Code Purple Theme
- ✅ Terminal Purple Configuration  
- ✅ System Integration (macOS only)
- ✅ Automatic backups and rollback script

### 2. Custom Installation
Choose specific components based on your needs:
- **VS Code Only**: Just the editor theme
- **Terminal Only**: Shell and terminal configuration
- **System Only**: macOS system integration (macOS only)

### 3. Development Installation
For theme developers and contributors:
- **Symlinked installation** for easy development
- **Debug mode** with verbose logging
- **Validation tools** for testing changes

## Components

### 1. VS Code Purple Theme
- Custom purple color scheme optimized for development
- Syntax highlighting with carefully selected purple palette
- Automatic theme activation in VS Code settings
- Compatible with all VS Code versions

### 2. Terminal Purple Configuration
- Shell configuration for Zsh and Bash
- Purple color schemes and enhanced prompts
- Terminal emulator themes (Terminal.app, iTerm2)
- Cross-platform compatibility (macOS, Linux)

### 3. System Integration (macOS only)
- System accent color set to purple
- Dock and Finder theming
- Menu bar and interface styling
- Application-specific purple theming

## Prerequisites

- **macOS**: Full feature support including system integration
- **Linux**: VS Code and terminal theming (system integration not available)
- **Python 3**: Recommended for advanced JSON handling (optional)
- **Disk Space**: At least 10MB free space

## Installation Process

1. **Prerequisites Check**: Verifies system compatibility and requirements
2. **Component Selection**: Choose full or custom installation
3. **Backup Creation**: Automatically backs up existing configurations
4. **Component Installation**: Installs selected components with progress feedback
5. **Rollback Script Creation**: Creates uninstall script for easy removal

## Error Handling

The installer includes comprehensive error handling:

- **Automatic Backups**: All existing configurations are backed up before changes
- **Rollback on Failure**: Option to automatically undo changes if installation fails
- **Continue on Error**: Option to continue installing other components if one fails
- **Detailed Logging**: Complete installation log saved to `~/.config/purple-theme/installation.log`

## Post-Installation

After installation, you may need to:

### VS Code
- Restart VS Code to see the purple theme
- Theme should be automatically activated
- Manual activation: File > Preferences > Color Theme > Purple Development Theme

### Terminal
- Restart terminal or run: `source ~/.zshrc` (or `~/.bashrc`)
- For Terminal.app: Set 'Purple Theme' as default in Preferences
- For iTerm2: Select 'Purple Theme' color preset in Preferences

### System (macOS)
- Most changes apply immediately
- Some changes may require logging out and back in
- Terminal.app profile must be set manually in preferences

## Utilities

After installation, several utility scripts are available:

```bash
# Uninstall all components and restore backups
~/.config/purple-theme/rollback.sh

# Check system theme status (macOS only)
~/.config/purple-theme/system-status.sh

# Test terminal colors and configuration
~/.config/purple-theme/test-shell-config.sh
```

## Troubleshooting

### Installation Fails
1. Check the installation log: `~/.config/purple-theme/installation.log`
2. Ensure you have sufficient permissions
3. Try custom installation to isolate problematic components
4. Use rollback script to clean up partial installations

### VS Code Theme Not Applied
1. Restart VS Code completely
2. Manually select theme: Command Palette > "Preferences: Color Theme"
3. Check if extension was installed: `~/.vscode/extensions/`

### Terminal Colors Not Working
1. Restart terminal application
2. Source shell configuration: `source ~/.zshrc`
3. Check if color files exist: `~/.config/purple-theme/`
4. Test colors: `~/.config/purple-theme/test-shell-config.sh`

### System Integration Issues (macOS)
1. Check system permissions for modifying preferences
2. Log out and back in to apply all changes
3. Check status: `~/.config/purple-theme/system-status.sh`

## Uninstallation

To completely remove the Purple Development Theme:

```bash
~/.config/purple-theme/rollback.sh
```

This will:
- Remove all installed theme files
- Restore original configurations from backups
- Clean up installation state and logs
- Revert system changes (macOS)

## Manual Installation

If the automated installer doesn't work, you can run individual component installers:

```bash
# VS Code theme only
./scripts/install-vscode-theme.sh

# Terminal configuration only
./scripts/install-terminal-config.sh

# System integration only (macOS)
./scripts/install-system-integration.sh
```

## 📚 Additional Resources

### Documentation
- **[README.md](README.md)** - Main project overview with features and screenshots
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Comprehensive troubleshooting guide
- **[CUSTOMIZATION.md](CUSTOMIZATION.md)** - Complete customization and theming guide
- **[FAQ.md](FAQ.md)** - Frequently asked questions and answers

### Component Documentation
- **[terminal/README.md](terminal/README.md)** - Terminal-specific configuration details
- **Individual script documentation** in the `scripts/` directory

### Quick Reference
- **Installation Log**: `~/.config/purple-theme/installation.log`
- **Rollback Script**: `~/.config/purple-theme/rollback.sh`
- **Test Scripts**: `~/.config/purple-theme/test-*.sh`

## 📞 Support

### Self-Help Resources
1. **[FAQ.md](FAQ.md)** - Check frequently asked questions first
2. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Comprehensive problem-solving guide
3. **Installation log** - Check `~/.config/purple-theme/installation.log` for detailed error messages
4. **Component-specific docs** - Review documentation in the `scripts/` directory

### Getting Help
1. **GitHub Issues** - For bugs and feature requests
2. **GitHub Discussions** - For questions and community support
3. **Email Support** - support@purple-theme.dev for direct assistance

### Before Reporting Issues
Please include:
- Operating system and version
- Terminal application and version
- VS Code version (if applicable)
- Installation log contents
- Steps to reproduce the issue

## 🎨 Color Palette Reference

The Purple Development Theme uses this carefully crafted color palette designed for optimal readability and visual appeal:

### Base Colors
- **Primary Background**: `#1A0D26` (deep purple) - Main editor and terminal background
- **Secondary Background**: `#2D1B3D` (medium purple) - Activity bar, panels
- **Tertiary Background**: `#3D2A4F` (lighter purple) - Sidebar, file explorer
- **Primary Text**: `#E6E6FA` (lavender) - Main text and code
- **Accent Color**: `#8B008B` (dark magenta) - Highlights, selections, borders

### Syntax Colors
- **Keywords**: `#9370DB` (medium slate blue) - Language keywords, control structures
- **Strings**: `#DDA0DD` (plum) - String literals, text content
- **Comments**: `#8A2BE2` (blue violet) - Code comments, documentation
- **Functions**: `#BA55D3` (medium orchid) - Function names, method calls
- **Variables**: `#DA70D6` (orchid) - Variable names, identifiers

### Accessibility Features
- **WCAG AA Compliant**: All color combinations meet accessibility standards
- **High Contrast Options**: Available for users with visual impairments
- **Color Blind Friendly**: Tested with various color vision deficiencies

## 🔄 Keeping Your Theme Updated

### Automatic Updates
The theme includes an update mechanism:
```bash
# Check for updates
./scripts/check-updates.sh

# Update to latest version
./scripts/update-theme.sh
```

### Manual Updates
```bash
# Pull latest changes
git pull origin main

# Reinstall with updates
./install.sh --update
```

### Preserving Customizations
Your customizations are preserved during updates. The installer:
- Backs up existing configurations
- Merges custom changes where possible
- Provides conflict resolution for incompatible changes

---

**Ready to transform your development environment? Let's get started! 🎨✨**