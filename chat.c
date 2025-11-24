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
#include <curl/curl.h>

#define MAX_MESSAGES 100
#define MAX_LINE_LEN 256
#define MAX_RESPONSE_SIZE 8192
#define MAX_POST_DATA_SIZE 2048

/* Named constants for control characters */
#define KEY_CTRL_C 3
#define KEY_BACKSPACE_1 127
#define KEY_BACKSPACE_2 8
#define KEY_ESC 27
#define KEY_PRINTABLE_START 32
#define KEY_PRINTABLE_END 126
#define MOUSE_WHEEL_UP 64
#define MOUSE_WHEEL_DOWN 65

char messages[MAX_MESSAGES][MAX_LINE_LEN];
int num_messages = 0;
int scroll_offset = 0;

int input_len = 0;
char input_buffer[MAX_LINE_LEN] = {0};

int rows, cols;
struct winsize term_size;
struct termios orig_termios;

/* Global curl handle */
CURL *curl;

/* Response buffer structure for curl callback */
typedef struct {
    char *data;
    size_t size;
    size_t capacity;
} ResponseBuffer;

/* Escape special characters for JSON */
char* escape_json_string(const char* str) {
    size_t len = strlen(str);
    /* Worst case: every char needs escaping (e.g., all quotes) */
    char* escaped = malloc(len * 2 + 1);
    if (!escaped) return NULL;

    size_t j = 0;
    for (size_t i = 0; i < len; i++) {
        char c = str[i];
        if (c == '"' || c == '\\') {
            escaped[j++] = '\\';
            escaped[j++] = c;
        } else if (c == '\n') {
            escaped[j++] = '\\';
            escaped[j++] = 'n';
        } else if (c == '\r') {
            escaped[j++] = '\\';
            escaped[j++] = 'r';
        } else if (c == '\t') {
            escaped[j++] = '\\';
            escaped[j++] = 't';
        } else if ((unsigned char)c < 32) {
            /* Skip control characters */
            continue;
        } else {
            escaped[j++] = c;
        }
    }
    escaped[j] = '\0';
    return escaped;
}

/* Simple JSON parser stub - for response, extract "response" field roughly */
char* extract_response(const char* json) {
    const char* key = "\"response\":\"";
    char* start = strstr(json, key);
    if (start) {
        start += strlen(key);
        char* end = strchr(start, '"');
        if (end) {
            size_t len = end - start;
            char* resp = malloc(len + 1);
            if (!resp) {
                return strdup("Memory allocation failed.");
            }
            strncpy(resp, start, len);
            resp[len] = '\0';
            return resp;
        }
    }
    return strdup("Sorry, I couldn't process that.");
}

/* Callback for curl write - with proper buffer management */
size_t write_callback(void *contents, size_t size, size_t nmemb, void *userp) {
    size_t realsize = size * nmemb;
    ResponseBuffer *buffer = (ResponseBuffer *)userp;

    /* Check if we need to grow the buffer */
    if (buffer->size + realsize >= buffer->capacity) {
        size_t new_capacity = buffer->capacity * 2;
        if (new_capacity < buffer->size + realsize + 1) {
            new_capacity = buffer->size + realsize + 1;
        }
        char *new_data = realloc(buffer->data, new_capacity);
        if (!new_data) {
            return 0; /* Signal error to curl */
        }
        buffer->data = new_data;
        buffer->capacity = new_capacity;
    }

    /* Copy data to buffer */
    memcpy(buffer->data + buffer->size, contents, realsize);
    buffer->size += realsize;
    buffer->data[buffer->size] = '\0';

    return realsize;
}

/* Function to get Ollama response */
char* get_ollama_response(const char* prompt, const char* model) {
    if (!curl) return strdup("Curl not initialized.");

    /* Escape the prompt for JSON */
    char* escaped_prompt = escape_json_string(prompt);
    if (!escaped_prompt) {
        return strdup("Memory allocation failed.");
    }

    char url[256];
    snprintf(url, sizeof(url), "http://localhost:11434/api/generate");

    /* Use dynamic allocation for post data to handle large prompts */
    size_t post_data_size = strlen(escaped_prompt) + strlen(model) + 100;
    char *post_data = malloc(post_data_size);
    if (!post_data) {
        free(escaped_prompt);
        return strdup("Memory allocation failed.");
    }

    snprintf(post_data, post_data_size,
        "{\"model\":\"%s\",\"prompt\":\"%s\",\"stream\":false}", model, escaped_prompt);
    free(escaped_prompt);

    /* Initialize response buffer */
    ResponseBuffer response;
    response.data = malloc(MAX_RESPONSE_SIZE);
    if (!response.data) {
        free(post_data);
        return strdup("Memory allocation failed.");
    }
    response.size = 0;
    response.capacity = MAX_RESPONSE_SIZE;
    response.data[0] = '\0';

    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, post_data);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L); /* 30 second timeout */

    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    free(post_data);

    if (res != CURLE_OK) {
        char *err = malloc(256);
        if (err) {
            snprintf(err, 256, "Ollama error: %s", curl_easy_strerror(res));
        }
        free(response.data);
        return err ? err : strdup("Request failed.");
    }

    char *result = extract_response(response.data);
    free(response.data);
    return result;
}

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
    if (ioctl(STDIN_FILENO, TIOCGWINSZ, &term_size) == -1) {
        /* Fallback to default values on error */
        rows = 24;
        cols = 80;
        return;
    }
    rows = term_size.ws_row;
    cols = term_size.ws_col;
}

void enable_raw_mode(void) {
    if (tcgetattr(STDIN_FILENO, &orig_termios) == -1) {
        perror("tcgetattr");
        exit(1);
    }

    struct termios raw = orig_termios;

    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    raw.c_oflag &= ~(OPOST);
    raw.c_cflag |= (CS8);
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    raw.c_cc[VMIN] = 1;
    raw.c_cc[VTIME] = 0;

    if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) == -1) {
        perror("tcsetattr");
        exit(1);
    }
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
        /* Auto scroll to bottom if we were at the bottom before */
        int chat_height = rows - 3;
        int max_scroll = (num_messages > chat_height) ? num_messages - chat_height : 0;
        /* If we were at the bottom (scroll_offset == previous max), stay at bottom */
        if (scroll_offset >= max_scroll - 1 || num_messages <= chat_height) {
            scroll_offset = max_scroll;
        }
    }
}

void process_input(const char* buf, ssize_t n) {
    if (n <= 0) return;

    char c = buf[0];
    if (c == KEY_CTRL_C) {  /* Ctrl+C */
        add_message("Goodbye! (Ctrl+C)");
        draw_interface();
        fflush(stdout);
        restore_terminal();
        exit(0);
    } else if (c == KEY_BACKSPACE_1 || c == KEY_BACKSPACE_2) {  /* Backspace */
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
                char* bot_resp = get_ollama_response(input_buffer, "llama3.1");  /* Default model */
                add_message(bot_resp);
                free(bot_resp);
                input_len = 0;
                input_buffer[0] = '\0';
            }
        }
    } else if (c >= KEY_PRINTABLE_START && c <= KEY_PRINTABLE_END && input_len < MAX_LINE_LEN - 1) {
        input_buffer[input_len++] = c;
        input_buffer[input_len] = '\0';
    } else if (c == KEY_ESC) {  /* ESC sequence */
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
                        if (button == MOUSE_WHEEL_UP) {
                            scroll_up(3);
                        } else if (button == MOUSE_WHEEL_DOWN) {
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
    scroll_offset = (scroll_offset >= amount) ? scroll_offset - amount : 0;
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
    (void)sig; /* Unused parameter */
    get_term_size();
    draw_interface();
}

/* Cleanup handler for proper exit */
void cleanup_handler(int sig) {
    (void)sig; /* Unused parameter */
    restore_terminal();
    if (curl) {
        curl_easy_cleanup(curl);
        curl_global_cleanup();
    }
    exit(0);
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

    /* Set up signal handlers */
    signal(SIGWINCH, resize_handler);
    signal(SIGINT, cleanup_handler);
    signal(SIGTERM, cleanup_handler);

    get_term_size();
    enable_raw_mode();
    setup_terminal();

    /* Initialize curl */
    if (curl_global_init(CURL_GLOBAL_DEFAULT) != 0) {
        fprintf(stderr, "Failed to initialize curl\n");
        restore_terminal();
        return 1;
    }
    curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to create curl handle\n");
        curl_global_cleanup();
        restore_terminal();
        return 1;
    }

    draw_interface();

    char buf[64];  /* Larger buffer for complex escape sequences */
    while (1) {
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(STDIN_FILENO, &fds);
        struct timeval tv = {0, 100000};  /* 100ms */

        int ret = select(STDIN_FILENO + 1, &fds, NULL, NULL, &tv);
        if (ret < 0) {
            /* Error in select, likely interrupted by signal */
            continue;
        }
        if (ret > 0 && FD_ISSET(STDIN_FILENO, &fds)) {
            ssize_t n = read(STDIN_FILENO, buf, sizeof(buf) - 1);
            if (n > 0) {
                process_input(buf, n);
            }
        }
    }

    /* Cleanup (unreachable but good practice) */
    cleanup_handler(0);

    return 0;
}

/* Compile with: gcc -o chat chat.c -lcurl */
/* Run: ./chat */
/* Note: Mouse wheel support is basic; for full mouse, more parsing needed. Handles basic scrolling with keyboard and approximate mouse wheel. Ollama integration requires local server running. */
