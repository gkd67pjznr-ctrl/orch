# Package: @mariozechner/pi-tui — Terminal UI Framework

## Overview

A sophisticated terminal UI framework with differential rendering, synchronized output, and support for modern terminal protocols. Provides a component-based architecture for building rich terminal interfaces.

**Location**: `packages/tui/`
**Size**: ~10,600 lines

---

## Architecture

```
ProcessTerminal (stdin/stdout I/O, raw mode, protocol detection)
    |
    v
TUI (main orchestrator, extends Container)
    |
    +---> render loop (per-frame)
    +---> differential comparison (3 strategies)
    +---> overlay compositing (modal stack)
    +---> hardware cursor positioning (for IME)
    |
    v
Components (hierarchical tree)
    +---> Text, Markdown, Input, Editor, SelectList, etc.
```

---

## Differential Rendering Engine (`src/tui.ts`)

### Three Rendering Strategies

**Strategy 1 — First Render**: Output all lines without clearing scrollback.

**Strategy 2 — Full Re-render**: Triggered on width/height change or content above viewport. Uses `\x1b[2J\x1b[H\x1b[3J` (clear screen + home + clear scrollback).

**Strategy 3 — Differential Update**: Finds first and last changed lines, moves cursor to first change, renders only changed lines. Clears trailing empty lines if content shrinks.

### Synchronized Output

All rendering wrapped in synchronized output brackets to prevent flicker:
```
\x1b[?2026h  (begin synchronized output)
<render content>
\x1b[?2026l  (end synchronized output)
```

Supported by: Kitty, Ghostty, WezTerm, tmux >3.2, iTerm2, VSCode.

### Overlay System

- Overlay stack with `focusOrder` (higher = on top)
- 9 anchor positions (top-left through bottom-right, plus center)
- Percentage-based sizing: `width: "50%"`, `maxHeight: "75%"`
- Absolute positioning: `row: 5, col: 10`
- `nonCapturing` flag prevents auto-focus
- `visible` callback for conditional rendering per-frame
- Focus restored to previous component when overlay closes

---

## Width Calculation (`src/utils.ts`)

### `visibleWidth(str: string): number`

Grapheme-accurate width calculation:

1. **Fast path**: Pure ASCII printable → string.length
2. **Cache**: 512-entry LRU
3. **Strip ANSI**: CSI, OSC, APC sequences removed
4. **Per-grapheme**:
   - `get-east-asian-width` for CJK (width 2)
   - RGI Emoji regex (width 2)
   - Regional indicators U+1F1E6-1F1FF (conservative width 2)
   - Zero-width: control chars, marks

### Text Wrapping: `wrapTextWithAnsi(text, width): string[]`

Word-wrapping that preserves ANSI codes across line breaks:
- `AnsiCodeTracker` maintains active SGR codes (bold, italic, colors)
- `getActiveCodes()` rebuilds SGR string when resuming on new line
- `getLineEndReset()` returns selective underline-off only (preserves background)
- Long words broken at grapheme granularity

### Truncation: `truncateToWidth(text, maxWidth, ellipsis, pad): string`

Handles ANSI codes and wide characters:
- Detects ANSI during truncation, reattaches to next visible character
- Always appends `\x1b[0m` and OSC 8 reset at line end
- Optional space padding to exact width

---

## Input Handling

### Keyboard Protocol (`src/keys.ts`)

Supports Kitty keyboard protocol (CSI-u sequences): `\x1b[<codepoint>;<flags>u`

```typescript
type KeyId =
  | BaseKey          // "a", "1", "escape", "enter"
  | `ctrl+${key}`
  | `shift+${key}`
  | `alt+${key}`
  | `ctrl+shift+${key}`
  // ... all modifier combos
```

Fallback to xterm `modifyOtherKeys` mode 2 for terminals without Kitty protocol.

### Input Buffering (`src/stdin-buffer.ts`)

Handles partial escape sequences arriving across multiple stdin events:
- Accumulates until complete sequence detected
- Validates CSI, OSC, SGR mouse sequences
- Bracketed paste: accumulates between `\x1b[200~` and `\x1b[201~`

---

## Component API

```typescript
interface Component {
  render(width: number): string[];    // Lines must not exceed width
  handleInput?(data: string): void;   // Keyboard input when focused
  wantsKeyRelease?: boolean;          // Opt-in for Kitty release events
  invalidate(): void;                 // Clear rendering cache
}

interface Focusable {
  focused: boolean;
}

const CURSOR_MARKER = "\x1b_pi:c\x07";  // APC sequence for IME cursor positioning
```

---

## Built-in Components

| Component | File | Purpose |
|-----------|------|---------|
| **Text** | text.ts | Multi-line text with word wrap and padding |
| **TruncatedText** | truncated-text.ts | Single-line, truncates to fit |
| **Input** | input.ts (~400 lines) | Single-line input with Emacs keybindings |
| **Editor** | editor.ts (~1000+ lines) | Multi-line editor with autocomplete, paste handling |
| **Markdown** | markdown.ts (~600 lines) | Markdown rendering with syntax highlighting and theming |
| **SelectList** | select-list.ts (~300 lines) | Interactive selection with keyboard navigation |
| **SettingsList** | settings-list.ts | Settings panel with value cycling |
| **Loader** | loader.ts | Animated Braille dot spinner (80ms frames) |
| **CancellableLoader** | cancellable-loader.ts | Loader with Escape to cancel + AbortSignal |
| **Image** | image.ts | Inline images (Kitty/iTerm2 protocols) |
| **Box** | box.ts | Container with padding and background |
| **Spacer** | spacer.ts | Empty lines for vertical spacing |

### Editor Features

- **Multi-line editing with word wrap**: `wordWrapLine()` → array of TextChunk
- **Paste handling**: Bracketed paste with large-paste markers (`[paste #1 +50 lines]`)
- **Autocomplete**: Slash commands (type `/`) and file paths (Tab)
- **Kill ring**: Emacs-style Ctrl+W/Ctrl+Y/Alt+Y
- **Undo**: structuredClone-based undo stack (Ctrl+-)
- **Vertical scrolling**: Maintains cursor visibility

### Markdown Theme

```typescript
interface MarkdownTheme {
  heading, link, linkUrl, code, codeBlock, codeBlockBorder,
  quote, quoteBorder, hr, listBullet, bold, italic,
  strikethrough, underline: (text: string) => string;
  highlightCode?: (code, lang?) => string[];
  codeBlockIndent?: string;
}
```

---

## Terminal Compatibility (`src/terminal.ts`, `src/terminal-image.ts`)

### Capability Detection

| Terminal | Images | TrueColor | Hyperlinks | Kitty KB |
|----------|--------|-----------|------------|----------|
| Kitty | kitty | yes | yes | yes |
| Ghostty | kitty | yes | yes | partial |
| WezTerm | iterm2 | yes | yes | no |
| iTerm2 | iterm2 | yes | yes | no |
| VSCode | no | yes | yes | no |
| Alacritty | no | yes | yes | no |

### Image Protocols

**Kitty Graphics Protocol**:
```
\x1b_Ga=T,f=100,i=<id>,c=<cols>,r=<rows>,m=1;<base64_chunk>\x1b\
\x1b_Gm=0;<base64_chunk>\x1b\  (last chunk)
```

**iTerm2 Inline Images**:
```
\x1b]1337;File=inline=1;width=Ncells;height=Ncells:<base64>\x07
```

### Windows VT Input

Uses `koffi` FFI to set `ENABLE_VIRTUAL_TERMINAL_INPUT` (0x0200) on Windows console. Without this, Shift+Tab and Ctrl+Arrows don't produce VT sequences.

---

## Keybinding System

### Default Bindings (Emacs-style)

**Cursor**: Arrow keys, Ctrl+A/E (home/end), Ctrl+Left/Right (word), Alt+Left/Right (word)
**Deletion**: Backspace, Delete, Ctrl+W (word back), Ctrl+U (line back), Ctrl+K (to end), Alt+D (word forward)
**Kill ring**: Ctrl+Y (yank), Alt+Y (yank-pop)
**Undo**: Ctrl+- (with structuredClone-based stack)

### Customization

```typescript
const manager = new KeybindingsManager(TUI_KEYBINDINGS, {
  "tui.input.submit": "ctrl+j",     // Override
  "tui.editor.undo": undefined,      // Disable
});
```

User config: `~/.pi/agent/keybindings.json`

---

## Key Quirks

1. **Tab = 3 spaces**: All tabs normalized to 3 spaces (not 4 or 8)
2. **Regional indicator width**: Conservative width 2 for U+1F1E6-1F1FF to prevent terminal drift
3. **Underline bleeding**: Selective `\x1b[24m` reset at line end (not full `\x1b[0m`) to preserve background
4. **Paste marker atomicity**: Large paste markers treated as single unit for cursor/word operations
5. **Empty component = `[""]`**: Must return array with empty string, not empty array
6. **Width overflow = crash**: TUI validates every line, writes crash log, throws if exceeded
7. **Overlay compositing**: Strict truncation for wide chars that would extend past boundary
8. **OSC 8 reset on every line**: `\x1b]8;;\x07` appended to close hyperlinks
9. **IME cursor via CURSOR_MARKER**: APC `\x1b_pi:c\x07` marks position, TUI extracts and positions hardware cursor
10. **Kitty key release filtering**: Components opt-in with `wantsKeyRelease = true`
