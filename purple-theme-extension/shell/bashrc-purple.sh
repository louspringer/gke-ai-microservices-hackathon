# Purple Theme Bash Configuration
# Add this to your ~/.bashrc or ~/.bash_profile file or source this file

# Load purple color scheme
source "$(dirname "${BASH_SOURCE[0]}")/purple-colors.sh"

# Bash-specific purple theme settings

# Enhanced git prompt function
git_prompt() {
    local git_status git_branch
    git_branch=$(git branch 2>/dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/')
    
    if [ -n "$git_branch" ]; then
        git_status=$(git status --porcelain 2>/dev/null)
        if [ -n "$git_status" ]; then
            echo -e " \033[1;33m($git_branch*)\033[0m"
        else
            echo -e " \033[1;32m($git_branch)\033[0m"
        fi
    fi
}

# Purple-themed bash prompt with git integration
PS1='\[\033[1;35m\]┌─[\[\033[0m\]\[\033[1;36m\]\u\[\033[0m\]\[\033[1;37m\]@\[\033[0m\]\[\033[1;34m\]\h\[\033[0m\]\[\033[1;35m\]]─[\[\033[0m\]\[\033[1;33m\]\w\[\033[0m\]\[\033[1;35m\]]\[\033[0m\]$(git_prompt)\n\[\033[1;35m\]└─❯\[\033[0m\] '

# History settings
HISTSIZE=10000
HISTFILESIZE=20000
HISTCONTROL=ignoreboth
shopt -s histappend
shopt -s checkwinsize

# Enhanced completion
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# Purple-themed aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline --graph --decorate --color=always'
alias gd='git diff --color=always'

# Function to show current directory with purple highlighting
pwd_purple() {
    echo -e "\033[1;35mCurrent directory:\033[0m \033[1;36m$(pwd)\033[0m"
}

# Function to show purple theme status
purple_status() {
    echo -e "\033[1;35mPurple Bash Theme Status:\033[0m"
    echo -e "  Prompt: \033[1;32m✓ Active\033[0m"
    echo -e "  Colors: \033[1;32m✓ Loaded\033[0m"
    echo -e "  Git Integration: \033[1;32m✓ Enabled\033[0m"
    echo -e "  History: \033[1;32m✓ Enhanced\033[0m"
}

# Welcome message
echo -e "\033[1;35mPurple Bash theme configuration loaded!\033[0m"
echo -e "Run '\033[1;36mpurple_status\033[0m' to check theme status"