/*
 * QIT C++ Proton Shim
 *
 * AMQP 1.0 interoperability test shim using Qpid Proton C++
 */

#pragma once

#include <proton/connection.hpp>
#include <proton/container.hpp>
#include <proton/message.hpp>
#include <proton/messaging_handler.hpp>
#include <proton/receiver.hpp>
#include <proton/sender.hpp>
#include <json/json.h>

#include <string>
#include <vector>

namespace qit {

// Hex/binary conversion utilities
std::string binary_to_hex(const proton::binary& bin);
proton::binary hex_to_binary(const std::string& hex_str);

// Sender handler - sends messages
class Sender : public proton::messaging_handler {
public:
    Sender(const std::string& broker_url,
           const std::string& queue_name,
           const std::string& amqp_type,
           const std::string& test_data_json,
           bool jms_mode = false,
           const std::string& headers_json = "");

    void on_container_start(proton::container& c) override;
    void on_sendable(proton::sender& s) override;
    void on_tracker_accept(proton::tracker& t) override;
    void on_transport_error(proton::transport& t) override;
    void on_error(const proton::error_condition& ec) override;

private:
    std::string broker_url_;
    std::string queue_name_;
    std::string amqp_type_;
    Json::Value test_values_;
    size_t sent_count_;
    size_t confirmed_count_;
    bool jms_mode_;
    Json::Value headers_;

    int8_t get_jms_message_type(const std::string& amqp_type) const;
    void apply_headers(proton::message& msg);
};

// Receiver handler - receives messages
class Receiver : public proton::messaging_handler {
public:
    Receiver(const std::string& broker_url,
             const std::string& queue_name,
             size_t count,
             int timeout_sec = 30);

    void on_container_start(proton::container& c) override;
    void on_message(proton::delivery& d, proton::message& m) override;
    void on_transport_error(proton::transport& t) override;
    void on_error(const proton::error_condition& ec) override;

    const Json::Value& get_messages() const { return received_messages_; }

private:
    std::string broker_url_;
    std::string queue_name_;
    size_t expected_count_;
    size_t received_count_;
    int timeout_sec_;
    bool output_sent_;
    Json::Value received_messages_;

    void on_timeout();
    void output_result();
    Json::Value decode_jms_message(const proton::value& body, int8_t jms_msg_type);
};

// Type codec - converts between AMQP values and JSON
class TypeCodec {
public:
    // Encode JSON test value to AMQP value
    static proton::value encode(const std::string& amqp_type, const Json::Value& test_value);

    // Encode a complex type (array, list, map, described) to AMQP value
    static proton::value encode_complex(const std::string& amqp_type, const Json::Value& value);

    // Decode AMQP value to JSON
    static Json::Value decode(const proton::value& amqp_value);

    // Decode AMQP value to typed element ["type", value]
    static Json::Value decode_typed(const proton::value& val);

    // Infer AMQP type name from proton::value
    static std::string infer_type(const proton::value& amqp_value);

    // Check if an AMQP type is complex
    static bool is_complex_type(const std::string& type_name);

    // Map AMQP type name to proton::type_id
    static proton::type_id type_name_to_id(const std::string& name);
};

} // namespace qit
