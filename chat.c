/* Pure C implementation of TTY chat interface */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <termios.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <signal.h>
#include <string.h>
#include <fcntl.h>

#define MAX_MESSAGES 100
#define MAX_LINE_LEN 256

char messages[MAX_MESSAGES][MAX_LINE_LEN];
int num_messages = 0;
int scroll_offset = 0;

int input_len = 0;
char input_buffer[MAX_LINE_LEN] = {0};

int rows, cols;
struct winsize term_size;
struct termios orig_termios;

/* Function prototypes */
void get_term_size(void);
void enable_raw_mode(void);
void disable_raw_mode(void);
void setup_terminal(void);
void restore_terminal(void);
void draw_interface(void);
void draw_status(void);
void draw_chat(void);
void draw_input(void);
void add_message(const char* msg);
void process_input(const char* buf, ssize_t n);
void scroll_up(int amount);
void scroll_down(int amount);
void resize_handler(int sig);

void get_term_size(void) {
    ioctl(STDIN_FILENO, TIOCGWINSZ, &term_size);
    rows = term_size.ws_row;
    cols = term_size.ws_col;
}

void enable_raw_mode(void) {
    struct termios raw = orig_termios;

    tcgetattr(STDIN_FILENO, &orig_termios);
    raw = orig_termios;

    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    raw.c_oflag &= ~(OPOST);
    raw.c_cflag |= (CS8);
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    raw.c_cc[VMIN] = 1;
    raw.c_cc[VTIME] = 0;

    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
}

void disable_raw_mode(void) {
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &orig_termios);
}

void setup_terminal(void) {
    printf("\033[?25l");  /* Hide cursor */
    printf("\033[2J");    /* Clear screen */
    printf("\033[?1000h"); /* Enable mouse reporting */
    printf("\033[?1002h"); /* Button events */
    printf("\033[?1006h"); /* SGR mouse encoding */
    fflush(stdout);
}

void restore_terminal(void) {
    printf("\033[?25h");  /* Show cursor */
    printf("\033[?1000l"); /* Disable mouse */
    printf("\033[?1002l");
    printf("\033[?1006l");
    fflush(stdout);
    disable_raw_mode();
}

void draw_status(void) {
    printf("\033[1;1H");  /* Top left */
    printf("\033[1mStatus: Chat App | Messages: %d\033[0m", num_messages);
    /* Clear rest of line */
    printf("\033[K");
    /* Pad if needed, but \033[K clears */
}

void draw_chat(void) {
    int chat_start_row = 2;
    int chat_height = rows - 3;
    int visible_lines = chat_height;

    /* Clear chat area */
    for(int r = chat_start_row; r < chat_start_row + visible_lines; r++) {
        printf("\033[%d;1H\033[K", r);
    }

    int start_idx = num_messages - visible_lines + scroll_offset;
    if (start_idx < 0) start_idx = 0;
    int end_idx = start_idx + visible_lines;
    if (end_idx > num_messages) end_idx = num_messages;

    for(int i = 0; i < visible_lines && (start_idx + i) < num_messages; i++) {
        int msg_idx = start_idx + i;
        printf("\033[%d;1H%s\033[K", chat_start_row + i, messages[msg_idx]);
    }
}

void draw_input(void) {
    int input_row = rows - 1;
    printf("\033[%d;1H\033[K", input_row);
    printf("\033[%d;1H> %s", input_row, input_buffer);
    /* Move cursor to end of input */
    printf("\033[%d;%dH", input_row, 3 + input_len);
}

void add_message(const char* msg) {
    if (num_messages < MAX_MESSAGES) {
        strncpy(messages[num_messages], msg, MAX_LINE_LEN - 1);
        messages[num_messages][MAX_LINE_LEN - 1] = '\0';
        num_messages++;
        /* Auto scroll to bottom unless already scrolled up */
        int chat_height = rows - 3;
        if (scroll_offset == 0 || num_messages <= chat_height) {
            scroll_offset = 0;
        } else {
            scroll_offset = num_messages - chat_height;
        }
    }
}

void process_input(const char* buf, ssize_t n) {
    if (n <= 0) return;

    char c = buf[0];
    if (c == 3) {  /* Ctrl+C */
        add_message("Goodbye! (Ctrl+C)");
        draw_interface();
        fflush(stdout);
        restore_terminal();
        exit(0);
    } else if (c == 127 || c == 8) {  /* Backspace */
        if (input_len > 0) {
            input_len--;
            input_buffer[input_len] = '\0';
        }
    } else if (c == '\n' || c == '\r') {
        if (input_len > 0) {
            if (input_buffer[0] == '/') {
                // Command handling
                if (strncmp(input_buffer, "/quit", 5) == 0 && (input_len == 5 || input_buffer[5] == ' ')) {
                    add_message("Goodbye!");  // Optional farewell
                    restore_terminal();
                    exit(0);
                } else {
                    // Unknown command
                    add_message("Unknown command. Type /quit to exit.");
                }
                input_len = 0;
                input_buffer[0] = '\0';
            } else {
                // Normal message
                add_message(input_buffer);
                char response[512];
                snprintf(response, sizeof(response), "Bot: You said: %s", input_buffer);
                add_message(response);
                input_len = 0;
                input_buffer[0] = '\0';
            }
        }
    } else if (c >= 32 && c <= 126 && input_len < MAX_LINE_LEN - 1) {
        input_buffer[input_len++] = c;
        input_buffer[input_len] = '\0';
    } else if (c == 27) {  /* ESC sequence */
        /* For simplicity, assume single char after, but need better parsing */
        /* In main, we read more for sequences */
        /* Here, handle if arrow or mouse */
        /* But since buf may have more, check */
        if (n > 1 && buf[1] == '[') {
            if (n > 2) {
                if (buf[2] == 'A') {  /* Up arrow - scroll up */
                    scroll_up(1);
                } else if (buf[2] == 'B') {  /* Down */
                    scroll_down(1);
                } else if (buf[2] == 'M') {  /* Mouse event in SGR */
                    /* Parse: after [ is button_char x_char y_char M */
                    /* Chars are position + 32, button as is with bits */
                    if (n > 4) {
                        unsigned char button = (unsigned char)buf[3];
                        /* For wheel: button 64 (up), 65 (down) */
                        if (button == 64) {
                            scroll_up(3);
                        } else if (button == 65) {
                            scroll_down(3);
                        }
                        /* Ignore other buttons for now */
                    }
                }
            }
        }
    }
    draw_interface();
}

void scroll_up(int amount) {
    if (scroll_offset > amount) {
        scroll_offset -= amount;
    } else {
        scroll_offset = 0;
    }
}

void scroll_down(int amount) {
    int max_scroll = (num_messages > (rows - 3)) ? num_messages - (rows - 3) : 0;
    if (scroll_offset + amount > max_scroll) {
        scroll_offset = max_scroll;
    } else {
        scroll_offset += amount;
    }
}

void resize_handler(int sig) {
    get_term_size();
    draw_interface();
}

void draw_interface(void) {
    draw_status();
    draw_chat();
    draw_input();
    fflush(stdout);
}

int main(void) {
    /* Sample messages */
    add_message("Welcome to TTY Chat!");
    add_message("Type messages below and press Enter.");
    add_message("Use arrow keys or mouse wheel to scroll.");

    signal(SIGWINCH, resize_handler);

    get_term_size();
    enable_raw_mode();
    setup_terminal();
    draw_interface();

    char buf[32];  /* Larger for sequences */
    while (1) {
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(STDIN_FILENO, &fds);
        struct timeval tv = {0, 100000};  /* 100ms */

        int ret = select(STDIN_FILENO + 1, &fds, NULL, NULL, &tv);
        if (ret > 0 && FD_ISSET(STDIN_FILENO, &fds)) {
            ssize_t n = read(STDIN_FILENO, buf, sizeof(buf));
            process_input(buf, n);
        }
    }

    return 0;
}

/* Compile with: gcc -o chat chat.c */
/* Run: ./chat */
/* Note: Mouse wheel support is basic; for full mouse, more parsing needed. Handles basic scrolling with keyboard and approximate mouse wheel. */
