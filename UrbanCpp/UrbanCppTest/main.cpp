#include <iostream>
#include <fstream>
#include "json.cpp"
#include "CppJsonTest.cpp"
using json = nlohmann::json;

// g++ main.cpp && ./a.exe
int main() {
    // std::string filename = "test.json";
    // std::cout << filename << std::endl;
    // printFirstElement(filename);
    std::ifstream f("../../Database/jsonData_officiel.json");
    json data = json::parse(f);
    std::cout << data["Aamir"] << std::endl;
    return 0;
}

