# Purple Development Theme - Troubleshooting Guide

This comprehensive troubleshooting guide covers common issues and their solutions for the Purple Development Theme installation and usage.

## 🚨 Emergency Recovery

### Complete Theme Removal
If you need to quickly remove all theme components:
```bash
# Run the automatic rollback script
~/.config/purple-theme/rollback.sh

# If rollback script is missing, manual cleanup:
rm -rf ~/.vscode/extensions/purple-development-theme-*
# Edit ~/.zshrc or ~/.bashrc to remove purple theme lines
defaults delete -g AppleAccentColor  # macOS only
rm -rf ~/.config/purple-theme/
```

## 🔍 Diagnostic Commands

### System Information
```bash
# Check operating system
uname -a

# Check shell
echo $SHELL

# Check VS Code version
code --version

# Check terminal color support
echo $TERM
tput colors
```

### Installation Status Check
```bash
# Check if installation files exist
ls -la ~/.config/purple-theme/

# Check VS Code extension
ls -la ~/.vscode/extensions/ | grep purple

# Check shell configuration
grep -n "purple" ~/.zshrc ~/.bashrc 2>/dev/null
```

## 🎨 VS Code Issues

### Issue: Theme Not Visible in Theme List
**Symptoms**: Purple Development Theme doesn't appear in VS Code theme selector

**Diagnosis**:
```bash
# Check if extension directory exists
ls -la ~/.vscode/extensions/purple-development-theme-*

# Check package.json
cat ~/.vscode/extensions/purple-development-theme-*/package.json
```

**Solutions**:
1. **Reinstall extension**:
   ```bash
   ./scripts/install-vscode-theme.sh --force
   ```

2. **Manual installation**:
   ```bash
   # Copy extension to VS Code extensions directory
   cp -r purple-theme-extension ~/.vscode/extensions/purple-development-theme-1.0.0
   ```

3. **Check VS Code extensions directory permissions**:
   ```bash
   chmod -R 755 ~/.vscode/extensions/
   ```

### Issue: Theme Applied But Colors Wrong
**Symptoms**: Theme is selected but colors don't match expected purple palette

**Diagnosis**:
```bash
# Check theme file content
cat ~/.vscode/extensions/purple-development-theme-*/themes/purple-theme.json | head -20
```

**Solutions**:
1. **Reload VS Code window**: Press `Cmd+R` (macOS) or `Ctrl+R` (Windows/Linux)

2. **Clear VS Code cache**:
   ```bash
   # Close VS Code completely
   pkill -f "Visual Studio Code"
   
   # Clear cache (backup first!)
   mv ~/.vscode/User/workspaceStorage ~/.vscode/User/workspaceStorage.backup
   
   # Restart VS Code
   code
   ```

3. **Check for conflicting extensions**:
   - Disable other theme extensions temporarily
   - Check for extensions that modify colors

### Issue: Syntax Highlighting Not Working
**Symptoms**: Code appears in single color or default colors

**Solutions**:
1. **Check file language mode**: Ensure VS Code recognizes the file type
2. **Reload window**: `Cmd+Shift+P` → "Developer: Reload Window"
3. **Check theme token colors**:
   ```bash
   # Verify tokenColors section exists in theme
   grep -A 10 "tokenColors" ~/.vscode/extensions/purple-development-theme-*/themes/purple-theme.json
   ```

## 🖥️ Terminal Issues

### Issue: Terminal Colors Not Applied
**Symptoms**: Terminal still shows default colors after installation

**Diagnosis**:
```bash
# Check if purple colors are sourced
grep -n "purple-colors" ~/.zshrc ~/.bashrc 2>/dev/null

# Test color variables
echo $PURPLE_BG
echo $PURPLE_FG
```

**Solutions**:
1. **Source configuration manually**:
   ```bash
   source ~/.config/purple-theme/shell/purple-colors.sh
   source ~/.zshrc  # or ~/.bashrc
   ```

2. **Check shell configuration file**:
   ```bash
   # For Zsh
   tail -10 ~/.zshrc
   
   # For Bash
   tail -10 ~/.bashrc
   ```

3. **Restart terminal completely**:
   - Quit terminal application
   - Reopen terminal

### Issue: Prompt Not Showing Purple Theme
**Symptoms**: Colors work but prompt doesn't show purple styling

**Solutions**:
1. **Check prompt configuration**:
   ```bash
   echo $PS1
   echo $PROMPT  # For Zsh
   ```

2. **Test prompt function**:
   ```bash
   # Check if purple prompt function exists
   type purple_prompt 2>/dev/null || echo "Function not found"
   ```

3. **Manually apply prompt**:
   ```bash
   # For Zsh
   source ~/.config/purple-theme/shell/zshrc-purple.sh
   
   # For Bash
   source ~/.config/purple-theme/shell/bashrc-purple.sh
   ```

### Issue: Git Integration Not Working
**Symptoms**: Git status doesn't show in purple prompt

**Solutions**:
1. **Check Git installation**:
   ```bash
   git --version
   which git
   ```

2. **Test in Git repository**:
   ```bash
   cd /path/to/git/repo
   git status
   # Prompt should show git information
   ```

3. **Check Git prompt functions**:
   ```bash
   type __git_ps1 2>/dev/null || echo "Git prompt function not found"
   ```

## 🍎 macOS System Integration Issues

### Issue: System Accent Color Not Changed
**Symptoms**: macOS system still shows default accent color

**Diagnosis**:
```bash
# Check current accent color
defaults read -g AppleAccentColor

# Check if purple accent is set (should be 5)
```

**Solutions**:
1. **Set accent color manually**:
   ```bash
   defaults write -g AppleAccentColor -int 5
   killall Dock
   killall SystemUIServer
   ```

2. **Log out and back in**: Some changes require fresh login session

3. **Check system permissions**: Ensure script has permission to modify system preferences

### Issue: Dock/Finder Not Themed
**Symptoms**: System accent changed but Dock/Finder still default

**Solutions**:
1. **Restart Dock and Finder**:
   ```bash
   killall Dock
   killall Finder
   ```

2. **Check Dark Mode setting**:
   ```bash
   # Check current appearance
   defaults read -g AppleInterfaceStyle
   
   # Set to Dark mode for better purple integration
   defaults write -g AppleInterfaceStyle Dark
   ```

## 🐧 Linux-Specific Issues

### Issue: Terminal Colors Not Working on Linux
**Solutions**:
1. **Check terminal emulator**:
   ```bash
   echo $TERM
   # Should support 256 colors
   ```

2. **Install color support**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ncurses-term
   
   # CentOS/RHEL
   sudo yum install ncurses-term
   ```

3. **Set TERM variable**:
   ```bash
   export TERM=xterm-256color
   ```

## 🪟 Windows-Specific Issues

### Issue: Windows Terminal Not Themed
**Solutions**:
1. **Manual theme import**:
   - Open Windows Terminal settings (`Ctrl+,`)
   - Go to "Color schemes"
   - Click "Add new"
   - Paste contents from `terminal/windows-terminal-purple.json`

2. **Apply to profile**:
   - Go to profile settings
   - Select "Purple Theme" from color scheme dropdown

## 🔧 Installation Script Issues

### Issue: Permission Denied Errors
**Symptoms**: Installation fails with permission errors

**Solutions**:
1. **Make script executable**:
   ```bash
   chmod +x install.sh
   chmod +x scripts/*.sh
   ```

2. **Check directory permissions**:
   ```bash
   # Check VS Code extensions directory
   ls -la ~/.vscode/
   mkdir -p ~/.vscode/extensions
   chmod 755 ~/.vscode/extensions
   
   # Check config directory
   mkdir -p ~/.config
   chmod 755 ~/.config
   ```

3. **Run with appropriate permissions**: Don't use `sudo` unless specifically needed

### Issue: Installation Hangs or Freezes
**Solutions**:
1. **Run with verbose output**:
   ```bash
   ./install.sh --verbose
   ```

2. **Check for interactive prompts**: Ensure no hidden prompts are waiting for input

3. **Kill and restart**:
   ```bash
   # Kill installation process
   pkill -f install.sh
   
   # Clean up partial installation
   ~/.config/purple-theme/rollback.sh
   
   # Try again
   ./install.sh
   ```

### Issue: Rollback Script Missing
**Symptoms**: Can't find rollback script to uninstall

**Solutions**:
1. **Manual cleanup**:
   ```bash
   # Remove VS Code extension
   rm -rf ~/.vscode/extensions/purple-development-theme-*
   
   # Remove shell configuration lines
   # Edit ~/.zshrc or ~/.bashrc manually
   
   # Reset system settings (macOS)
   defaults delete -g AppleAccentColor
   
   # Clean up files
   rm -rf ~/.config/purple-theme/
   ```

## 🎯 Performance Issues

### Issue: VS Code Slow After Theme Installation
**Solutions**:
1. **Disable other extensions temporarily**: Test if theme conflicts with other extensions

2. **Check theme file size**:
   ```bash
   ls -lh ~/.vscode/extensions/purple-development-theme-*/themes/purple-theme.json
   ```

3. **Reload VS Code**: `Cmd+Shift+P` → "Developer: Reload Window"

### Issue: Terminal Slow to Start
**Solutions**:
1. **Check shell startup time**:
   ```bash
   time zsh -i -c exit
   time bash -i -c exit
   ```

2. **Optimize shell configuration**: Remove unnecessary commands from purple theme scripts

## 🔍 Advanced Debugging

### Enable Debug Logging
```bash
# Create debug version of installation
DEBUG=1 ./install.sh

# Check detailed logs
tail -f ~/.config/purple-theme/installation.log
```

### Test Individual Components
```bash
# Test VS Code theme only
./scripts/install-vscode-theme.sh --test

# Test terminal configuration only
./scripts/install-terminal-config.sh --test

# Test system integration only (macOS)
./scripts/install-system-integration.sh --test
```

### Color Testing
```bash
# Test all ANSI colors
for i in {0..255}; do
    printf "\x1b[48;5;%sm%3d\e[0m " "$i" "$i"
    if (( i == 15 )) || (( i > 15 )) && (( (i-15) % 6 == 0 )); then
        printf "\n"
    fi
done

# Test purple color variables
echo -e "${PURPLE_BG}${PURPLE_FG}Purple Theme Test${NC}"
```

## 📞 Getting Help

### Before Reporting Issues
1. **Check this troubleshooting guide**
2. **Run diagnostic commands**
3. **Try solutions in order**
4. **Collect system information**

### Reporting Issues
Include this information:
```bash
# System information
uname -a
echo $SHELL
code --version
echo $TERM
tput colors

# Installation status
ls -la ~/.config/purple-theme/
ls -la ~/.vscode/extensions/ | grep purple

# Error logs
cat ~/.config/purple-theme/installation.log
```

### Support Channels
- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and community support
- **Email**: support@purple-theme.dev for direct support

---

**Remember**: Most issues can be resolved by completely restarting the affected application (VS Code, Terminal, etc.) after making configuration changes.