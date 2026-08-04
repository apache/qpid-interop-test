/*
 * QIT C++ Proton Shim - Main Entry Point
 *
 * Command-line interface for AMQP interoperability testing using Qpid Proton C++
 */

#include "qit_shim.hpp"

#include <iostream>
#include <string>
#include <cstring>
#include <cstdlib>

void print_usage(const char* prog_name) {
    std::cerr << "Usage: " << prog_name << " <command> [options]\n"
              << "\nCommands:\n"
              << "  send      Send AMQP messages\n"
              << "  receive   Receive AMQP messages\n"
              << "\nSend options:\n"
              << "  --broker <url>      Broker URL (e.g., amqp://localhost:5672)\n"
              << "  --queue <name>      Queue name\n"
              << "  --type <amqp_type>  AMQP type\n"
              << "  --count <n>         Number of messages\n"
              << "  --data <json>       JSON array of test data\n"
              << "\nReceive options:\n"
              << "  --broker <url>      Broker URL\n"
              << "  --queue <name>      Queue name\n"
              << "  --count <n>         Expected message count\n"
              << "  --timeout <sec>     Timeout in seconds (default: 30)\n"
              << std::endl;
}

struct CommandLineArgs {
    std::string command;
    std::string broker;
    std::string queue;
    std::string amqp_type;
    std::string data;
    std::string headers;
    std::string properties;
    int count = 0;
    int timeout = 30;
    bool jms_mode = false;

    bool parse(int argc, char** argv) {
        if (argc < 2) {
            return false;
        }

        command = argv[1];

        for (int i = 2; i < argc; ) {
            std::string opt = argv[i];

            // Check if this is a flag (no value)
            if (opt == "--jms-mode") {
                jms_mode = true;
                i++;
                continue;
            }

            // Regular option with value
            if (i + 1 >= argc) {
                std::cerr << "Error: Missing value for option " << argv[i] << std::endl;
                return false;
            }

            std::string val = argv[i + 1];

            if (opt == "--broker") {
                broker = val;
            } else if (opt == "--queue") {
                queue = val;
            } else if (opt == "--type") {
                amqp_type = val;
            } else if (opt == "--count") {
                count = std::atoi(val.c_str());
            } else if (opt == "--data") {
                data = val;
            } else if (opt == "--timeout") {
                timeout = std::atoi(val.c_str());
            } else if (opt == "--headers") {
                headers = val;
            } else if (opt == "--properties") {
                properties = val;
            } else {
                std::cerr << "Error: Unknown option " << opt << std::endl;
                return false;
            }

            i += 2;
        }

        return validate();
    }

    bool validate() {
        if (command != "send" && command != "receive") {
            std::cerr << "Error: Invalid command. Must be 'send' or 'receive'" << std::endl;
            return false;
        }

        if (broker.empty()) {
            std::cerr << "Error: --broker is required" << std::endl;
            return false;
        }

        if (queue.empty()) {
            std::cerr << "Error: --queue is required" << std::endl;
            return false;
        }

        if (count <= 0) {
            std::cerr << "Error: --count must be positive" << std::endl;
            return false;
        }

        if (command == "send") {
            if (amqp_type.empty()) {
                std::cerr << "Error: --type is required for send" << std::endl;
                return false;
            }
            if (data.empty()) {
                std::cerr << "Error: --data is required for send" << std::endl;
                return false;
            }
        }

        return true;
    }
};

int main(int argc, char** argv) {
    try {
        CommandLineArgs args;
        if (!args.parse(argc, argv)) {
            print_usage(argv[0]);
            return 1;
        }

        if (args.command == "send") {
            qit::Sender sender(args.broker, args.queue, args.amqp_type, args.data, args.jms_mode, args.headers, args.properties);
            proton::container(sender).run();
            return 0;
        } else if (args.command == "receive") {
            qit::Receiver receiver(args.broker, args.queue, args.count, args.timeout);
            proton::container(receiver).run();
            return 0;
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
