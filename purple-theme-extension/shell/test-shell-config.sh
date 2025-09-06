#!/bin/bash
# Test script to verify shell color scheme configuration

echo "Testing Purple Shell Color Scheme Configuration..."
echo "=================================================="

# Test 1: Load color scheme
echo "Test 1: Loading color scheme..."
source "$(dirname "$0")/purple-colors.sh"
if [ $? -eq 0 ]; then
    echo "✓ Color scheme loaded successfully"
else
    echo "✗ Failed to load color scheme"
    exit 1
fi

# Test 2: Verify terminal background and foreground exports
echo -e "\nTest 2: Verifying terminal background and foreground exports..."
if [ -n "$TERM_BACKGROUND" ] && [ -n "$TERM_FOREGROUND" ]; then
    echo "✓ Terminal background: $TERM_BACKGROUND"
    echo "✓ Terminal foreground: $TERM_FOREGROUND"
    echo "✓ Background RGB: $TERM_BG_RGB"
    echo "✓ Foreground RGB: $TERM_FG_RGB"
else
    echo "✗ Terminal background/foreground not properly exported"
    exit 1
fi

# Test 3: Verify ANSI color codes
echo -e "\nTest 3: Verifying ANSI color codes..."
if [ -n "$COLOR_PURPLE_DEEP" ] && [ -n "$COLOR_LAVENDER" ] && [ -n "$COLOR_RESET" ]; then
    echo "✓ ANSI color codes exported"
    echo "✓ Deep Purple: $COLOR_PURPLE_DEEP"
    echo "✓ Lavender: $COLOR_LAVENDER"
    echo "✓ Reset: $COLOR_RESET"
else
    echo "✗ ANSI color codes not properly exported"
    exit 1
fi

# Test 4: Test color contrast
echo -e "\nTest 4: Testing color contrast..."
test_purple_contrast > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Color contrast test passed"
else
    echo "✗ Color contrast test failed"
    exit 1
fi

# Test 5: Test ZSH configuration
echo -e "\nTest 5: Testing ZSH configuration..."
zsh_output=$(zsh -c 'cd "$(dirname "$0")" && source ./zshrc-purple.sh && echo "ZSH_TEST_SUCCESS"' "$0" 2>&1)
if echo "$zsh_output" | grep -q "ZSH_TEST_SUCCESS"; then
    echo "✓ ZSH configuration loaded successfully"
else
    echo "✗ ZSH configuration failed to load"
    echo "Debug output: $zsh_output"
    exit 1
fi

echo -e "\n=================================================="
echo "All tests passed! Shell color scheme configuration is working correctly."
echo "Requirements met:"
echo "✓ Shell configuration for zsh with purple ANSI color codes"
echo "✓ Color export statements for terminal background and foreground"
echo "✓ Terminal purple color scheme with good contrast"