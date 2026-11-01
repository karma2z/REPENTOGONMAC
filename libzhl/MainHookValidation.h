#pragma once

#include <cstddef>

// HookMain copies seven bytes verbatim to a trampoline after restoring push ebp.
// Validate the actual bytes, not only the wildcard signature that located them.
// This checks instruction shape only; it does not establish game compatibility.
inline bool ValidateMainHookWindow(const unsigned char* code, std::size_t size) {
    if (!code || size < 10 || code[1] != 0x8b || code[2] != 0xec) {
        return false;
    }
    // The first byte may be poisoned by the loader; HookMain restores it to 0x55.
    std::size_t offset = 3;
    while (offset < 10) {
        // Decode only the two relocation-independent immediate-push encodings
        // used by this SEH prologue. Prefixes and every other opcode fail closed.
        const std::size_t length = code[offset] == 0x6a ? 2 : code[offset] == 0x68 ? 5 : 0;
        if (!length || length > 10 - offset) {
            return false;
        }
        offset += length;
    }
    return offset == 10;
}
