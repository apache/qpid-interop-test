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
#include <cstdint>

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
              << "\nLarge content options:\n"
              << "  --large-content <type>  Content type: 'binary' or 'string'\n"
              << "  --size <bytes>          Content size in bytes\n"
              << "  --seed <n>              PRNG seed for content generation\n"
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
    std::string message_header;
    int count = 0;
    int timeout = 30;
    bool jms_mode = false;
    std::string large_content;  // "binary" or "string", empty if not large content mode
    size_t size = 0;
    uint32_t seed = 0;
    size_t elements = 0;
    size_t element_size = 0;

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
            } else if (opt == "--message-header") {
                message_header = val;
            } else if (opt == "--large-content") {
                large_content = val;
            } else if (opt == "--size") {
                size = static_cast<size_t>(std::strtoull(val.c_str(), nullptr, 10));
            } else if (opt == "--seed") {
                seed = static_cast<uint32_t>(std::strtoul(val.c_str(), nullptr, 10));
            } else if (opt == "--elements") {
                elements = static_cast<size_t>(std::strtoull(val.c_str(), nullptr, 10));
            } else if (opt == "--element-size") {
                element_size = static_cast<size_t>(std::strtoull(val.c_str(), nullptr, 10));
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

        // Large content mode has different requirements
        if (!large_content.empty()) {
            if (large_content != "binary" && large_content != "string" &&
                large_content != "list" && large_content != "array" &&
                large_content != "map" && large_content != "described") {
                std::cerr << "Error: --large-content must be binary, string, list, array, map, or described" << std::endl;
                return false;
            }
            if ((large_content == "binary" || large_content == "string") && size == 0) {
                std::cerr << "Error: --size is required for binary/string large content" << std::endl;
                return false;
            }
            if (large_content != "binary" && large_content != "string" && (elements == 0 || element_size == 0)) {
                std::cerr << "Error: --elements and --element-size are required for collection large content" << std::endl;
                return false;
            }
            return true;
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

        if (!args.large_content.empty()) {
            // Large content mode
            if (args.command == "send") {
                qit::LargeContentSender sender(args.broker, args.queue,
                    args.large_content, args.seed, args.size, args.jms_mode,
                    args.elements, args.element_size);
                proton::container(sender).run();
                return 0;
            } else if (args.command == "receive") {
                qit::LargeContentReceiver receiver(args.broker, args.queue,
                    args.large_content, args.seed, args.size, args.timeout,
                    args.elements, args.element_size);
                proton::container(receiver).run();
                return 0;
            }
        } else if (args.command == "send") {
            qit::Sender sender(args.broker, args.queue, args.amqp_type, args.data, args.jms_mode, args.headers, args.properties, args.message_header);
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
