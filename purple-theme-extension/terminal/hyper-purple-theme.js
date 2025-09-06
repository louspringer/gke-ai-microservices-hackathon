// Purple Theme for Hyper Terminal
// Add this configuration to your ~/.hyper.js file

module.exports = {
  config: {
    // Purple color scheme
    foregroundColor: '#E6E6FA', // Lavender
    backgroundColor: '#1A0D26', // Deep purple
    selectionColor: 'rgba(61, 42, 79, 0.3)', // Light purple with transparency
    borderColor: '#3D2A4F', // Medium purple
    cursorColor: '#9370DB', // Medium slate blue
    cursorAccentColor: '#1A0D26', // Deep purple (cursor text)
    
    // ANSI colors
    colors: {
      black: '#1A0D26',        // Deep purple
      red: '#8B3A62',          // Purple-tinted red
      green: '#9370DB',        // Medium slate blue (purple-green)
      yellow: '#DDA0DD',       // Plum (purple-yellow)
      blue: '#9370DB',         // Medium slate blue
      magenta: '#9370DB',      // Medium slate blue
      cyan: '#BA55D3',         // Medium orchid
      white: '#E6E6FA',        // Lavender
      lightBlack: '#2D1B3D',   // Medium purple
      lightRed: '#ED94C0',     // Light purple-red
      lightGreen: '#BA55D3',   // Medium orchid
      lightYellow: '#DDA0DD',  // Plum
      lightBlue: '#BA55D3',    // Medium orchid
      lightMagenta: '#ED94C0', // Light purple-magenta
      lightCyan: '#E6E6FA',    // Lavender
      lightWhite: '#E6E6FA'    // Lavender
    },
    
    // Terminal styling
    css: `
      .hyper_main {
        border: 2px solid #3D2A4F !important;
      }
      
      .header_header {
        background-color: #2D1B3D !important;
        border-bottom: 1px solid #3D2A4F !important;
      }
      
      .tab_tab {
        background-color: #2D1B3D !important;
        border-right: 1px solid #3D2A4F !important;
        color: #E6E6FA !important;
      }
      
      .tab_tab.tab_active {
        background-color: #1A0D26 !important;
        color: #9370DB !important;
      }
      
      .tab_tab:hover {
        background-color: #3D2A4F !important;
      }
      
      .splitpane_divider {
        background-color: #3D2A4F !important;
      }
      
      .term_term {
        background-color: #1A0D26 !important;
      }
      
      /* Scrollbar styling */
      .term_term::-webkit-scrollbar {
        width: 8px;
      }
      
      .term_term::-webkit-scrollbar-track {
        background: #2D1B3D;
      }
      
      .term_term::-webkit-scrollbar-thumb {
        background: #9370DB;
        border-radius: 4px;
      }
      
      .term_term::-webkit-scrollbar-thumb:hover {
        background: #BA55D3;
      }
    `,
    
    // Font configuration
    fontFamily: '"Menlo", "DejaVu Sans Mono", "Lucida Console", monospace',
    fontSize: 12,
    fontWeight: 'normal',
    fontWeightBold: 'bold',
    lineHeight: 1.0,
    letterSpacing: 0,
    
    // Cursor configuration
    cursorShape: 'BLOCK',
    cursorBlink: false,
    
    // Shell configuration
    shell: process.env.SHELL || '/bin/zsh',
    shellArgs: ['--login'],
    
    // Window configuration
    windowSize: [540, 380],
    padding: '12px 14px',
    
    // Other settings
    bell: 'SOUND',
    copyOnSelect: false,
    defaultSSHApp: true,
    quickEdit: false,
    macOptionSelectionMode: 'vertical',
    webGLRenderer: true,
  },
  
  // Plugins
  plugins: [
    'hyper-search',
    'hyper-pane',
    'hyperterm-paste',
    'hyperterm-safepaste'
  ],
  
  // Local plugins
  localPlugins: [],
  
  // Keymaps
  keymaps: {
    'window:devtools': 'cmd+alt+o',
    'window:reload': 'cmd+alt+r',
    'window:reloadFull': 'cmd+alt+shift+r',
    'window:preferences': 'cmd+,',
    'zoom:reset': 'cmd+0',
    'zoom:in': 'cmd+plus',
    'zoom:out': 'cmd+-',
    'window:new': 'cmd+shift+n',
    'window:minimize': 'cmd+m',
    'window:zoom': 'cmd+alt+m',
    'window:toggleFullScreen': 'cmd+ctrl+f',
    'window:close': 'cmd+w',
    'tab:new': 'cmd+t',
    'tab:next': 'cmd+shift+]',
    'tab:prev': 'cmd+shift+[',
    'tab:jump:prefix': 'cmd',
    'pane:next': 'cmd+alt+right',
    'pane:prev': 'cmd+alt+left',
    'pane:splitVertical': 'cmd+d',
    'pane:splitHorizontal': 'cmd+shift+d',
    'pane:close': 'cmd+w',
    'editor:undo': 'cmd+z',
    'editor:redo': 'cmd+shift+z',
    'editor:cut': 'cmd+x',
    'editor:copy': 'cmd+c',
    'editor:paste': 'cmd+v',
    'editor:selectAll': 'cmd+a',
    'editor:movePreviousWord': 'alt+left',
    'editor:moveNextWord': 'alt+right',
    'editor:moveBeginningLine': 'cmd+left',
    'editor:moveEndLine': 'cmd+right',
    'editor:deletePreviousWord': 'alt+backspace',
    'editor:deleteNextWord': 'alt+delete',
    'editor:deleteBeginningLine': 'cmd+backspace',
    'editor:deleteEndLine': 'cmd+delete',
    'editor:clear': 'cmd+k'
  }
};