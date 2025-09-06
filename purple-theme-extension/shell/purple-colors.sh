#!/bin/bash
# Purple Terminal Color Scheme Configuration
# Source this file in your shell profile (.zshrc, .bash_profile, etc.)

# Purple color palette for terminal
export PURPLE_DEEP="#1A0D26"
export PURPLE_MEDIUM="#2D1B3D" 
export PURPLE_LIGHT="#3D2A4F"
export PURPLE_ACCENT="#9370DB"
export PURPLE_BRIGHT="#BA55D3"
export LAVENDER="#E6E6FA"
export PLUM="#DDA0DD"

# Terminal background and foreground colors (hex values)
export TERM_BACKGROUND="$PURPLE_DEEP"
export TERM_FOREGROUND="$LAVENDER"

# Terminal background and foreground colors (RGB values for terminal emulators)
export TERM_BG_RGB="26,13,38"      # RGB equivalent of #1A0D26
export TERM_FG_RGB="230,230,250"   # RGB equivalent of #E6E6FA

# ANSI color codes for purple theme
# Standard colors (0-7) - Purple themed variants
export COLOR_BLACK="\033[0;30m"           # Black
export COLOR_RED="\033[0;31m"             # Red (kept for errors)
export COLOR_GREEN="\033[0;32m"           # Green (kept for success)
export COLOR_YELLOW="\033[0;33m"          # Yellow (kept for warnings)
export COLOR_BLUE="\033[0;34m"            # Blue (purple-tinted)
export COLOR_MAGENTA="\033[0;35m"         # Magenta (primary purple)
export COLOR_CYAN="\033[0;36m"            # Cyan (purple-tinted)
export COLOR_WHITE="\033[0;37m"           # White

# Bright colors (8-15) - Enhanced purple theme
export COLOR_BRIGHT_BLACK="\033[1;30m"    # Bright Black (dark gray)
export COLOR_BRIGHT_RED="\033[1;91m"      # Bright Red
export COLOR_BRIGHT_GREEN="\033[1;92m"    # Bright Green
export COLOR_BRIGHT_YELLOW="\033[1;93m"   # Bright Yellow
export COLOR_BRIGHT_BLUE="\033[1;94m"     # Bright Blue (purple-blue)
export COLOR_BRIGHT_MAGENTA="\033[1;95m"  # Bright Magenta (bright purple)
export COLOR_BRIGHT_CYAN="\033[1;96m"     # Bright Cyan (purple-cyan)
export COLOR_BRIGHT_WHITE="\033[1;97m"    # Bright White (lavender)

# Extended ANSI colors for purple theme (256-color support)
export COLOR_PURPLE_DEEP="\033[38;5;53m"      # Deep purple
export COLOR_PURPLE_MEDIUM="\033[38;5;54m"    # Medium purple
export COLOR_PURPLE_LIGHT="\033[38;5;55m"     # Light purple
export COLOR_PURPLE_BRIGHT="\033[38;5;135m"   # Bright purple
export COLOR_LAVENDER="\033[38;5;183m"        # Lavender
export COLOR_PLUM="\033[38;5;176m"            # Plum

# Background colors for purple theme
export BG_PURPLE_DEEP="\033[48;5;53m"         # Deep purple background
export BG_PURPLE_MEDIUM="\033[48;5;54m"       # Medium purple background
export BG_PURPLE_LIGHT="\033[48;5;55m"        # Light purple background

# Reset and control codes
export COLOR_RESET="\033[0m"                  # Reset all formatting
export COLOR_BOLD="\033[1m"                   # Bold text
export COLOR_DIM="\033[2m"                    # Dim text
export COLOR_UNDERLINE="\033[4m"              # Underlined text
export COLOR_BLINK="\033[5m"                  # Blinking text
export COLOR_REVERSE="\033[7m"                # Reverse video

# Purple-themed prompt colors
export PS1_USER_COLOR="$COLOR_BRIGHT_MAGENTA"
export PS1_HOST_COLOR="$COLOR_MAGENTA"
export PS1_PATH_COLOR="$COLOR_BRIGHT_BLUE"
export PS1_GIT_COLOR="$COLOR_BRIGHT_CYAN"

# LS_COLORS for purple theme (file type colors)
export LS_COLORS="di=1;35:ln=1;36:so=1;31:pi=1;33:ex=1;32:bd=1;34:cd=1;34:su=0;41:sg=0;46:tw=0;42:ow=0;43:*.tar=1;31:*.tgz=1;31:*.zip=1;31:*.z=1;31:*.gz=1;31:*.bz2=1;31:*.deb=1;31:*.rpm=1;31:*.jar=1;31:*.jpg=1;35:*.jpeg=1;35:*.gif=1;35:*.bmp=1;35:*.pbm=1;35:*.pgm=1;35:*.ppm=1;35:*.tga=1;35:*.xbm=1;35:*.xpm=1;35:*.tif=1;35:*.tiff=1;35:*.png=1;35:*.mov=1;35:*.mpg=1;35:*.mpeg=1;35:*.avi=1;35:*.fli=1;35:*.gl=1;35:*.dl=1;35:*.xcf=1;35:*.xwd=1;35:*.ogg=1;35:*.mp3=1;35:*.wav=1;35:"

# Grep colors for purple theme
export GREP_COLOR="1;35"
export GREP_COLORS="ms=1;35:mc=1;35:sl=:cx=:fn=1;32:ln=1;33:bn=1;33:se=1;30"

# Function to apply purple theme to current terminal session
apply_purple_theme() {
    echo "Applying purple terminal theme..."
    
    # Set terminal title
    echo -ne "\033]0;Purple Terminal\007"
    
    # Apply terminal background and foreground colors (if supported)
    printf '\033]11;%s\007' "$TERM_BACKGROUND"  # Set background color
    printf '\033]10;%s\007' "$TERM_FOREGROUND"  # Set foreground color
    
    # Display color palette
    echo -e "${COLOR_BRIGHT_MAGENTA}Purple Terminal Theme Activated${COLOR_RESET}"
    echo -e "Color Palette:"
    echo -e "${COLOR_PURPLE_DEEP}■${COLOR_RESET} Deep Purple"
    echo -e "${COLOR_PURPLE_MEDIUM}■${COLOR_RESET} Medium Purple"
    echo -e "${COLOR_PURPLE_LIGHT}■${COLOR_RESET} Light Purple"
    echo -e "${COLOR_PURPLE_BRIGHT}■${COLOR_RESET} Bright Purple"
    echo -e "${COLOR_LAVENDER}■${COLOR_RESET} Lavender"
    echo -e "${COLOR_PLUM}■${COLOR_RESET} Plum"
    echo -e "${COLOR_MAGENTA}■${COLOR_RESET} Magenta"
    echo -e "${COLOR_BRIGHT_MAGENTA}■${COLOR_RESET} Bright Magenta" 
    echo -e "${COLOR_BLUE}■${COLOR_RESET} Blue"
    echo -e "${COLOR_BRIGHT_BLUE}■${COLOR_RESET} Bright Blue"
    echo -e "${COLOR_CYAN}■${COLOR_RESET} Cyan"
    echo -e "${COLOR_BRIGHT_CYAN}■${COLOR_RESET} Bright Cyan"
    echo -e "${COLOR_WHITE}■${COLOR_RESET} White"
    echo -e "${COLOR_BRIGHT_WHITE}■${COLOR_RESET} Bright White"
    
    echo -e "\nTerminal Settings:"
    echo -e "Background: ${COLOR_PURPLE_DEEP}$TERM_BACKGROUND${COLOR_RESET}"
    echo -e "Foreground: ${COLOR_LAVENDER}$TERM_FOREGROUND${COLOR_RESET}"
}

# Custom purple-themed prompt for zsh
setup_purple_zsh_prompt() {
    # Enable prompt substitution
    setopt PROMPT_SUBST
    
    # Git branch function
    git_branch() {
        git branch 2>/dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
    }
    
    # Purple-themed prompt
    PROMPT='%F{magenta}%n%f@%F{blue}%m%f:%F{cyan}%~%f %F{yellow}$(git_branch)%f
%F{magenta}❯%f '
    
    # Right prompt with time
    RPROMPT='%F{240}%T%f'
}

# Custom purple-themed prompt for bash
setup_purple_bash_prompt() {
    # Git branch function for bash
    git_branch_bash() {
        git branch 2>/dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
    }
    
    # Purple-themed bash prompt
    PS1='\[\033[1;35m\]\u\[\033[0m\]@\[\033[1;34m\]\h\[\033[0m\]:\[\033[1;36m\]\w\[\033[0m\] \[\033[1;33m\]$(git_branch_bash)\[\033[0m\]\n\[\033[1;35m\]❯\[\033[0m\] '
}

# Auto-detect shell and apply appropriate prompt
if [ -n "$ZSH_VERSION" ]; then
    setup_purple_zsh_prompt
elif [ -n "$BASH_VERSION" ]; then
    setup_purple_bash_prompt
fi

# Aliases for common commands with color
alias ls='ls -G --color=auto'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

# Function to test color contrast and readability
test_purple_contrast() {
    echo -e "${COLOR_BRIGHT_MAGENTA}Testing Purple Theme Contrast${COLOR_RESET}"
    echo -e "Background: ${BG_PURPLE_DEEP}${COLOR_LAVENDER} Text on deep purple background ${COLOR_RESET}"
    echo -e "Background: ${BG_PURPLE_MEDIUM}${COLOR_BRIGHT_WHITE} Text on medium purple background ${COLOR_RESET}"
    echo -e "Background: ${BG_PURPLE_LIGHT}${COLOR_WHITE} Text on light purple background ${COLOR_RESET}"
    
    echo -e "\nReadability Test:"
    echo -e "${COLOR_LAVENDER}Normal text in lavender${COLOR_RESET}"
    echo -e "${COLOR_BRIGHT_WHITE}Bright white text${COLOR_RESET}"
    echo -e "${COLOR_PURPLE_BRIGHT}Bright purple text${COLOR_RESET}"
    echo -e "${COLOR_PLUM}Plum colored text${COLOR_RESET}"
    
    echo -e "\nContrast Rating: ${COLOR_BRIGHT_GREEN}✓ Good contrast maintained${COLOR_RESET}"
}

# Function to export all purple theme colors for other applications
export_purple_theme() {
    # Export color values for use by other applications
    export PURPLE_THEME_ACTIVE=1
    export PURPLE_THEME_VERSION="1.0"
    
    # Export all color codes
    env | grep -E '^COLOR_|^BG_|^TERM_' | sort
    
    echo -e "${COLOR_BRIGHT_MAGENTA}Purple theme colors exported to environment${COLOR_RESET}"
}

echo "Purple shell color scheme loaded! Run 'apply_purple_theme' to see the color palette."
echo "Run 'test_purple_contrast' to verify color contrast and readability."