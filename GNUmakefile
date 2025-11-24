.PHONY: all debug release clean

TARGET = chat
CFLAGS = -Wall -Wextra -Wformat -Wformat-security -std=c99
LDFLAGS = -lcurl

# Security hardening flags
SECURITY_CFLAGS = -D_FORTIFY_SOURCE=2 -fstack-protector-strong -fPIE
SECURITY_LDFLAGS = -pie

all: release

debug: CFLAGS += -g -O0 -DDEBUG
debug: $(TARGET)

release: CFLAGS += -O2 -DNDEBUG $(SECURITY_CFLAGS)
release: LDFLAGS += $(SECURITY_LDFLAGS)
release: $(TARGET)

$(TARGET): chat.c
	gcc $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(TARGET)

# Usage:
# make          # Builds release with security hardening
# make debug    # Builds debug version
# make clean    # Cleans build artifacts
