.PHONY: all debug release clean

TARGET = chat
CFLAGS = -Wall -std=c99
LDFLAGS = -lcurl

all: release

debug: CFLAGS += -g -O0 -DDEBUG
debug: $(TARGET)

release: CFLAGS += -O2 -DNDEBUG
release: $(TARGET)

$(TARGET): chat.c
	gcc $(CFLAGS) $(LDFLAGS) -o $@ $<

clean:
	rm -f $(TARGET)

# Usage:
# make          # Builds release
# make debug    # Builds debug version
# make clean    # Cleans build artifacts
