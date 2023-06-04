#include <iostream>
#include <algorithm>
#include <fstream>
#include <cctype>

bool isDigitString(const std::string& str) {
    return std::all_of(str.begin(), str.end(), [](unsigned char c) {
        return std::isdigit(c);
    });
}