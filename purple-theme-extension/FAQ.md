# Purple Development Theme - Frequently Asked Questions

## 🎨 General Questions

### Q: What is the Purple Development Theme?
**A:** The Purple Development Theme is a comprehensive theming solution that transforms your entire development environment with a cohesive purple color palette. It includes VS Code themes, terminal configurations, and system integration for macOS.

### Q: What platforms are supported?
**A:** 
- **Full support**: macOS (VS Code + Terminal + System integration)
- **Partial support**: Linux (VS Code + Terminal)
- **Limited support**: Windows (VS Code + Windows Terminal)

### Q: Is this theme free?
**A:** Yes, the Purple Development Theme is completely free and open source under the MIT license.

### Q: Can I use this theme commercially?
**A:** Yes, the MIT license allows commercial use without restrictions.

## 🚀 Installation Questions

### Q: How do I install the theme?
**A:** Run the installation script:
```bash
git clone https://github.com/your-username/purple-development-theme.git
cd purple-development-theme
./install.sh
```

### Q: Can I install only specific components?
**A:** Yes, you can install components individually:
```bash
# VS Code theme only
./scripts/install-vscode-theme.sh

# Terminal configuration only
./scripts/install-terminal-config.sh

# System integration only (macOS)
./scripts/install-system-integration.sh
```

### Q: Do I need administrator privileges to install?
**A:** No, the theme installs to user directories and doesn't require sudo or administrator access.

### Q: What happens to my existing themes and configurations?
**A:** The installer automatically creates backups of your existing configurations before making changes. You can restore them using the rollback script.

### Q: How do I uninstall the theme?
**A:** Run the rollback script created during installation:
```bash
~/.config/purple-theme/rollback.sh
```

## 🎨 VS Code Questions

### Q: Why doesn't the theme appear in my VS Code theme list?
**A:** This usually happens if:
1. VS Code wasn't restarted after installation
2. The extension wasn't installed correctly
3. VS Code extensions directory has permission issues

**Solution**: Restart VS Code completely and check the theme list again.

### Q: Can I use this theme with VS Code Insiders?
**A:** Yes, but you may need to manually copy the theme to the VS Code Insiders extensions directory:
```bash
cp -r ~/.vscode/extensions/purple-development-theme-* ~/.vscode-insiders/extensions/
```

### Q: How do I switch between the purple theme and other themes?
**A:** Use the VS Code command palette:
1. Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Preferences: Color Theme"
3. Select your desired theme

### Q: Can I customize the colors in the VS Code theme?
**A:** Yes, you can modify the `themes/purple-theme.json` file or create custom variants. See the [CUSTOMIZATION.md](CUSTOMIZATION.md) guide for details.

### Q: Does the theme work with all VS Code extensions?
**A:** The theme is designed to work with most extensions, but some extensions may override certain colors. Popular extensions like GitLens, Bracket Pair Colorizer, and language-specific extensions should work well.

### Q: Why do some syntax elements not have purple colors?
**A:** The theme focuses on readability while maintaining the purple aesthetic. Not all syntax elements use purple to ensure proper contrast and code readability.

## 🖥️ Terminal Questions

### Q: Which terminals are supported?
**A:** 
- **macOS**: Terminal.app, iTerm2, Hyper
- **Linux**: gnome-terminal, konsole, xterm, and most modern terminals
- **Windows**: Windows Terminal, PowerShell, WSL terminals

### Q: Why aren't my terminal colors changing?
**A:** Common causes:
1. Terminal doesn't support 256 colors
2. Shell configuration wasn't sourced
3. Terminal application needs restart

**Solution**: Restart your terminal completely and run `source ~/.zshrc` or `source ~/.bashrc`.

### Q: Can I use the theme with Fish shell?
**A:** The current version supports Zsh and Bash. Fish support can be added by creating a Fish-specific configuration file.

### Q: How do I test if the terminal theme is working?
**A:** Run the test script:
```bash
~/.config/purple-theme/test-shell-config.sh
```

### Q: Can I use the terminal theme without the VS Code theme?
**A:** Yes, you can install only the terminal configuration:
```bash
./scripts/install-terminal-config.sh
```

### Q: Why doesn't my prompt show git information?
**A:** Ensure git is installed and you're in a git repository. The git integration requires git to be available in your PATH.

## 🍎 macOS System Integration Questions

### Q: What system changes does the theme make on macOS?
**A:** The system integration:
- Sets the system accent color to purple
- Configures Dock appearance
- Adjusts Finder sidebar colors
- Sets highlight colors system-wide

### Q: Why didn't my system accent color change?
**A:** You may need to:
1. Log out and back in
2. Restart affected applications (Dock, Finder)
3. Check system permissions

### Q: Can I revert the system changes?
**A:** Yes, the rollback script restores all system settings to their original values.

### Q: Does the theme work with macOS Dark Mode?
**A:** Yes, the theme is optimized for Dark Mode but also works with Light Mode.

### Q: Will the theme affect other applications?
**A:** The system integration primarily affects system UI elements. Most third-party applications won't be affected unless they specifically use system accent colors.

## 🔧 Troubleshooting Questions

### Q: The installation failed. What should I do?
**A:** 
1. Check the installation log: `cat ~/.config/purple-theme/installation.log`
2. Ensure you have write permissions to your home directory
3. Try installing components individually
4. See the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide

### Q: How do I report a bug?
**A:** 
1. Check the troubleshooting guide first
2. Collect system information and error logs
3. Create an issue on GitHub with detailed information
4. Include your OS version, terminal type, and VS Code version

### Q: Can I get help with customization?
**A:** Yes! Check the [CUSTOMIZATION.md](CUSTOMIZATION.md) guide or ask in GitHub Discussions.

### Q: The theme looks different than the screenshots. Why?
**A:** This can happen due to:
- Different VS Code version
- Other extensions modifying colors
- Terminal not supporting full color range
- System display settings

## 🎯 Performance Questions

### Q: Does the theme slow down VS Code?
**A:** No, color themes have minimal performance impact. If you experience slowness, it's likely due to other factors.

### Q: Does the terminal configuration affect shell startup time?
**A:** The theme adds minimal overhead. If you experience slow startup, check what other shell configurations you have.

### Q: How much disk space does the theme use?
**A:** The complete theme package uses less than 5MB of disk space.

## 🔄 Updates and Maintenance Questions

### Q: How do I update the theme?
**A:** 
1. Pull the latest changes from the repository
2. Run the installation script again
3. The installer will update existing installations

### Q: Will updates overwrite my customizations?
**A:** The installer preserves custom modifications in separate files. However, it's recommended to backup your customizations before updating.

### Q: How often is the theme updated?
**A:** Updates are released as needed for bug fixes, new features, and compatibility improvements.

### Q: Can I contribute to the theme development?
**A:** Yes! Contributions are welcome. See the contributing guidelines in the repository.

## 🎨 Customization Questions

### Q: Can I change the purple colors to different shades?
**A:** Yes, you can modify any colors in the theme files. See the [CUSTOMIZATION.md](CUSTOMIZATION.md) guide for detailed instructions.

### Q: Can I create a light version of the theme?
**A:** Yes, you can create light variants by modifying the color values. The customization guide includes examples.

### Q: How do I add support for a new terminal emulator?
**A:** 
1. Create a configuration file for the terminal
2. Add installation logic to the terminal installation script
3. Test thoroughly and submit a pull request

### Q: Can I use different colors for different programming languages?
**A:** Yes, you can customize token colors for specific languages in the VS Code theme file.

## 🔒 Security Questions

### Q: Is it safe to run the installation script?
**A:** Yes, the script only modifies user configuration files and doesn't require elevated privileges. You can review the script before running it.

### Q: Does the theme collect any data?
**A:** No, the theme doesn't collect, transmit, or store any user data.

### Q: Can I audit the theme files?
**A:** Yes, all theme files are plain text (JSON, shell scripts) that you can inspect and modify.

## 🌍 Compatibility Questions

### Q: Does the theme work with older versions of VS Code?
**A:** The theme requires VS Code 1.74.0 or later. For older versions, you may need to manually install the theme files.

### Q: Is the theme compatible with VS Code Remote Development?
**A:** Yes, the theme works with VS Code Remote Development extensions.

### Q: Can I use the theme with Vim/Neovim?
**A:** The current version is designed for VS Code and terminals. A Vim/Neovim version could be created as a separate project.

### Q: Does the theme work with code-server (VS Code in the browser)?
**A:** Yes, you can manually install the theme files in your code-server extensions directory.

## 📱 Mobile and Remote Questions

### Q: Can I use the theme with VS Code on iPad?
**A:** VS Code for iPad doesn't support custom themes, but you can use the terminal configuration if you have a terminal app that supports custom color schemes.

### Q: Does the theme work over SSH?
**A:** The terminal colors will work over SSH if your local terminal supports them. VS Code themes work with VS Code Remote SSH extension.

## 🎓 Learning Questions

### Q: How can I learn to create my own themes?
**A:** 
1. Study the theme files in this project
2. Read VS Code theme documentation
3. Experiment with color modifications
4. Check out the customization guide

### Q: What tools do you recommend for color selection?
**A:** 
- Adobe Color for palette creation
- Contrast checkers for accessibility
- VS Code's built-in color picker
- Online hex color tools

### Q: How do I understand the VS Code theme structure?
**A:** The VS Code documentation has comprehensive guides on theme development, and you can examine existing themes for reference.

---

## 📞 Still Have Questions?

If your question isn't answered here:

1. **Check the documentation**: [README.md](README.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [CUSTOMIZATION.md](CUSTOMIZATION.md)
2. **Search existing issues**: Check if someone else has asked the same question
3. **GitHub Discussions**: Ask the community
4. **Create an issue**: For bugs or feature requests
5. **Email support**: support@purple-theme.dev

**We're here to help make your purple development environment perfect! 💜**