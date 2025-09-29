# Ollama TTY Chat

A full-screen terminal-based chat interface written in C, using ANSI escape sequences for rendering. Supports keyboard input, mouse wheel scrolling, slash commands (e.g., `/quit`), and graceful exit on Ctrl+C.

## Features
- Scrollable chat view with status bar and input line.
- Basic mouse wheel support (xterm-256color compatible).
- Slash commands: `/quit` to exit.
- Simulated bot responses for testing.
- Handles terminal resizing.
- No external libraries (pure standard C).

## Building
Uses GNUmakefile for debug/release builds.

```bash
make          # Release build
make debug    # Debug build
make clean    # Clean
```

Compile with GCC (C99).

## Running
```bash
./chat
```

- Type messages and press Enter.
- Use up/down arrows or mouse wheel to scroll.
- `/quit` or Ctrl+C to exit.

## Repository
- GitHub: [mbt/ollama-tty](https://github.com/mbt/ollama-tty)
- License: MIT (add if desired)

## Dependencies
- Standard C library (POSIX compliant, tested on macOS).

## Known Limitations
- Mouse support is basic (wheel only).
- No persistent message storage.
- Simple bot simulation—extend for real integration (e.g., Ollama API).

Extend with more commands, colors, or networking as needed.
