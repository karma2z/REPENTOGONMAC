#include "MainHookValidation.h"
#include <array>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc == 3) {
        std::ifstream input(argv[1], std::ios::binary);
        input.seekg(std::stoull(argv[2], nullptr, 0));
        std::array<unsigned char, 10> bytes{};
        if (!input.read(reinterpret_cast<char*>(bytes.data()), bytes.size())) return 2;
        const bool valid = ValidateMainHookWindow(bytes.data(), bytes.size());
        std::cout << (valid ? "main instruction window accepted" : "main instruction window rejected") << '\n';
        return valid ? 0 : 1;
    }
    // Immediate values are synthetic; both old/new SEH initializer values work.
    std::array<unsigned char, 10> code{0x55,0x8b,0xec,0x6a,0xfe,0x68,0,0,0,0};
    unsigned failures = 0;
    auto check = [&](bool value, const char* name) {
        if (!value) { std::cerr << "FAILED: " << name << '\n'; ++failures; }
    };
    check(ValidateMainHookWindow(code.data(), code.size()), "complete push instructions");
    code[4] = 0xff;
    check(ValidateMainHookWindow(code.data(), code.size()), "alternate SEH initializer");
    code[0] = 0xcc;
    check(ValidateMainHookWindow(code.data(), code.size()), "loader-poisoned first byte");
    check(!ValidateMainHookWindow(nullptr, 10), "null input");
    for (std::size_t size = 0; size < 10; ++size)
        check(!ValidateMainHookWindow(code.data(), size), "truncated input");
    code[1] = 0x90;
    check(!ValidateMainHookWindow(code.data(), code.size()), "incorrect frame setup");
    code[1] = 0x8b;
    code[3] = 0xe8;
    check(!ValidateMainHookWindow(code.data(), code.size()), "relative call");
    code[3] = 0xc3;
    check(!ValidateMainHookWindow(code.data(), code.size()), "early return");
    code[3] = 0x6a;
    code[5] = 0x90;
    check(!ValidateMainHookWindow(code.data(), code.size()), "unexpected prologue instruction");
    code[5] = 0x6a;
    code[7] = 0x68;
    check(!ValidateMainHookWindow(code.data(), code.size()), "split final instruction");
    code[5] = 0x68;
    std::cout << "Main hook validation: " << failures << " failures\n";
    return failures ? 1 : 0;
}
