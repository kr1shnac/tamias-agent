import sys
import tty
import termios
import select
import re

def probe_terminal(sequence: str, timeout: float = 0.15) -> str:
    """Send an ANSI sequence and read the raw response from stdin."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        tty.setraw(sys.stdin.fileno())
        sys.stdout.write(sequence)
        sys.stdout.flush()
        
        response = ""
        # Poll for response with timeout
        while True:
            r, w, x = select.select([sys.stdin], [], [], timeout)
            if not r:
                break
            char = sys.stdin.read(1)
            response += char
            # Stop if we hit typical terminators (ST/BEL/string terminator)
            if char in ('\x07', '\x1c', '\x9c'):
                break
            # OSC 11 response often ends in ESC \
            if response.endswith('\x1b\\'):
                break
            # DECRQM response often ends in 'y'
            if sequence.endswith('$p') and char == 'y':
                break
                
        return response
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def main():
    print("Testing Terminal Capabilities...\n")
    
    # 1. DEC 2026 (Sync Output)
    # DECRQM format: ESC [ ? <mode> $ p
    dec_query = "\x1b[?2026$p"
    dec_response = probe_terminal(dec_query)
    
    if dec_response:
        # Expected: ESC [ ? 2026 ; <setting> $ y
        print(f"DEC 2026 Raw Response: {repr(dec_response)}")
        if ";1$y" in dec_response or ";2$y" in dec_response:
            print("DEC 2026: SUPPORTED (Recognized)")
        elif ";0$y" in dec_response:
            print("DEC 2026: UNRECOGNIZED (Not supported)")
        else:
            print("DEC 2026: UNKNOWN RESPONSE")
    else:
        print("DEC 2026 Raw Response: NONE (Timeout)")

    # 2. OSC 11 (Background Color)
    # OSC 11 format: ESC ] 11 ; ? ESC \
    osc_query = "\x1b]11;?\x1b\\"
    osc_response = probe_terminal(osc_query)
    
    if osc_response:
        print(f"\nOSC 11 Raw Response: {repr(osc_response)}")
        # Look for rgb:RRRR/GGGG/BBBB
        match = re.search(r"rgb:([0-9a-fA-F/]+)", osc_response)
        if match:
            print(f"OSC 11: Background Color = {match.group(1)}")
        else:
            print("OSC 11: Response received but no RGB found.")
    else:
        print("\nOSC 11 Raw Response: NONE (Timeout)")

if __name__ == "__main__":
    main()
