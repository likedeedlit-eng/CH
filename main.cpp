#include "ConsistentHash.cpp"
#include <string>
#include <iostream>

int main() {
    ConsistentHash* consistentHash = new ConsistentHash();
    while (true) {
        std::string command;
        std::cin >> command;
        
        if (command.substr(0, 12) == "/add_machine") {
            int machineId;
            std::cin >> machineId;
            consistentHash->addMachine(machineId);
        }
        else if (command.substr(0, 14) == "/delete_machine") {
            int machineId;
            std::cin >> machineId;
            consistentHash->deleteMachine(machineId);
        }
        else if (command.substr(0, 9) == "/add_data") {
            int dataValue;
            std::cin >> dataValue;
            consistentHash->addData(dataValue);
        }
        else if (command.substr(0, 12) == "/delete_data") {
            int dataValue;
            std::cin >> dataValue;
            consistentHash->deleteData(dataValue);
        }
        else if (command == "/exit") {
            delete consistentHash;
            break;
        }
        else {
            std::cout << "Unknown command. Available commands:" << std::endl;
            std::cout << "  /add_machine <id>" << std::endl;
            std::cout << "  /delete_machine <id>" << std::endl;
            std::cout << "  /add_data <value>" << std::endl;
            std::cout << "  /delete_data <value>" << std::endl;
            std::cout << "  /exit" << std::endl;
        }
    }
    return 0;
}