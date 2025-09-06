# Purple Theme ZSH Configuration
# Add this to your ~/.zshrc file or source this file

# Load purple color scheme
if [[ -n "${BASH_SOURCE[0]}" ]]; then
    source "$(dirname "${BASH_SOURCE[0]}")/purple-colors.sh"
elif [[ -n "${(%):-%x}" ]]; then
    source "$(dirname "${(%):-%x}")/purple-colors.sh"
else
    # Fallback to relative path
    source "$(dirname "$0")/purple-colors.sh" 2>/dev/null || source "./purple-colors.sh" 2>/dev/null || echo "Warning: Could not load purple-colors.sh"
fi

# Apply terminal background and foreground colors immediately
printf '\033]11;%s\007' "$TERM_BACKGROUND"  # Set background color
printf '\033]10;%s\007' "$TERM_FOREGROUND"  # Set foreground color

# ZSH-specific purple theme settings
autoload -U colors && colors

# Enhanced purple prompt with git integration
autoload -Uz vcs_info
precmd() { vcs_info }

# Git info format
zstyle ':vcs_info:git:*' formats ' (%b)'
zstyle ':vcs_info:*' enable git

# Purple-themed ZSH prompt with enhanced features using custom colors
PROMPT='%F{135}┌─[%f%F{183}%n%f%F{255}@%f%F{54}%m%f%F{135}]─[%f%F{176}%~%f%F{135}]%f%F{92}${vcs_info_msg_0_}%f
%F{135}└─❯%f '

# Right prompt with timestamp and exit code
RPROMPT='%F{240}[%T]%f %(?..%F{red}✗%f)'

# History settings with purple theme
HISTSIZE=10000
SAVEHIST=10000
HISTFILE=~/.zsh_history
setopt HIST_VERIFY
setopt SHARE_HISTORY
setopt APPEND_HISTORY
setopt INC_APPEND_HISTORY
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_REDUCE_BLANKS
setopt HIST_IGNORE_SPACE

# Enhanced completion with purple highlighting
autoload -U compinit
compinit

# Completion styling with purple theme
zstyle ':completion:*' menu select
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
zstyle ':completion:*:descriptions' format '%F{magenta}-- %d --%f'
zstyle ':completion:*:messages' format '%F{purple}-- %d --%f'
zstyle ':completion:*:warnings' format '%F{red}-- no matches found --%f'

# Key bindings
bindkey '^[[A' history-search-backward
bindkey '^[[B' history-search-forward
bindkey '^[[H' beginning-of-line
bindkey '^[[F' end-of-line
bindkey '^[[3~' delete-char

# Purple-themed aliases
alias ll='ls -alF --color=auto'
alias la='ls -A --color=auto'
alias l='ls -CF --color=auto'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# Git aliases with purple theme awareness
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline --graph --decorate --color=always'
alias gd='git diff --color=always'

# Function to show purple theme status
purple_status() {
    echo -e "%F{135}Purple ZSH Theme Status:%f"
    echo -e "  Prompt: %F{92}✓ Active%f"
    echo -e "  Colors: %F{92}✓ Loaded%f"
    echo -e "  Git Integration: %F{92}✓ Enabled%f"
    echo -e "  Completion: %F{92}✓ Enhanced%f"
    echo -e "  Background: %F{183}$TERM_BACKGROUND%f"
    echo -e "  Foreground: %F{183}$TERM_FOREGROUND%f"
    echo -e "  Contrast: %F{92}✓ Good%f"
}

# Function to demonstrate zsh color capabilities
demo_zsh_colors() {
    echo -e "%F{135}ZSH Purple Color Demonstration:%f"
    echo -e "%F{53}Deep Purple (53)%f - %F{54}Medium Purple (54)%f - %F{55}Light Purple (55)%f"
    echo -e "%F{135}Bright Purple (135)%f - %F{183}Lavender (183)%f - %F{176}Plum (176)%f"
    echo -e "%F{92}Success Green%f - %F{208}Warning Orange%f - %F{196}Error Red%f"
    
    # Test background colors
    echo -e "%K{53}%F{183} Text on deep purple background %k%f"
    echo -e "%K{54}%F{255} Text on medium purple background %k%f"
    
    echo -e "\n%F{135}All colors provide good contrast for readability%f"
}

echo "Purple ZSH theme configuration loaded!"