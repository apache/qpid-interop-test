/*
 * QIT C++ Proton Shim - Receiver Implementation
 */

#include "qit_shim.hpp"
#include <json/json.h>
#include <proton/delivery.hpp>
#include <proton/transport.hpp>
#include <proton/work_queue.hpp>
#include <proton/annotation_key.hpp>
#include <proton/symbol.hpp>
#include <proton/codec/encoder.hpp>
#include <proton/codec/decoder.hpp>
#include <iostream>
#include <cstdlib>

namespace qit {

Receiver::Receiver(const std::string& broker_url,
                   const std::string& queue_name,
                   size_t count,
                   int timeout_sec)
    : broker_url_(broker_url),
      queue_name_(queue_name),
      expected_count_(count),
      received_count_(0),
      timeout_sec_(timeout_sec),
      output_sent_(false) {}

void Receiver::on_container_start(proton::container& c) {
    c.open_receiver(broker_url_ + "/" + queue_name_);

    // Set timeout using std::function wrapped work
    if (timeout_sec_ > 0) {
        proton::work timeout_work = proton::make_work([this]() {
            this->on_timeout();
        });
        c.schedule(proton::duration(timeout_sec_ * 1000), timeout_work);
    }
}

void Receiver::on_message(proton::delivery& d, proton::message& m) {
    try {
        // Check for JMS message type annotation
        // NOTE: Qpid JMS Client uses symbol as key
        int8_t jms_msg_type = -1;
        proton::annotation_key jms_key(proton::symbol("x-opt-jms-msg-type"));
        if (m.message_annotations().exists(jms_key)) {
            proton::value jms_value = m.message_annotations().get(jms_key);
            jms_msg_type = proton::get<int8_t>(jms_value);
        }

        Json::Value decoded;
        if (jms_msg_type >= 0) {
            // Decode as JMS message
            decoded = decode_jms_message(m.body(), jms_msg_type);
        } else {
            // Decode as regular AMQP message
            decoded = TypeCodec::decode(m.body());
        }

        Json::Value msg_data;
        msg_data["index"] = static_cast<int>(received_count_);
        msg_data["type"] = decoded["type"];
        msg_data["value"] = decoded["value"];

        received_messages_.append(msg_data);
        received_count_++;

        if (received_count_ >= expected_count_) {
            d.receiver().close();
            d.connection().close();

            // Output result
            output_result();
        }
    } catch (const std::exception& e) {
        std::cerr << "Error processing message: " << e.what() << std::endl;
        d.receiver().close();
        d.connection().close();
        throw;
    }
}

Json::Value Receiver::decode_jms_message(const proton::value& body, int8_t jms_msg_type) {
    // JMS message type constants
    const int8_t JMS_MESSAGE = 0;
    const int8_t JMS_TEXT_MESSAGE = 5;
    const int8_t JMS_BYTES_MESSAGE = 3;
    const int8_t JMS_MAP_MESSAGE = 2;
    const int8_t JMS_STREAM_MESSAGE = 4;

    Json::Value result;

    if (jms_msg_type == JMS_TEXT_MESSAGE) {
        // TextMessage: body is string in AmqpValue section
        result["type"] = "text";  // Use 'text' to match JMS shim output
        try {
            result["value"] = proton::get<std::string>(body);
        } catch (...) {
            result["value"] = Json::nullValue;
        }
    } else if (jms_msg_type == JMS_BYTES_MESSAGE) {
        // BytesMessage: body is binary in Data section
        result["type"] = "bytes";
        try {
            proton::binary bin = proton::get<proton::binary>(body);
            std::string hex;
            for (uint8_t byte : bin) {
                char buf[3];
                snprintf(buf, sizeof(buf), "%02x", byte);
                hex += buf;
            }
            result["value"] = hex;
        } catch (...) {
            result["value"] = Json::nullValue;
        }
    } else if (jms_msg_type == JMS_MESSAGE) {
        // Empty message
        result["type"] = "null";
        result["value"] = Json::nullValue;
    } else if (jms_msg_type == JMS_MAP_MESSAGE) {
        try {
            proton::codec::decoder dec(body);
            proton::codec::start s;
            dec >> s;
            if (s.size >= 2) {
                std::string key;
                proton::value val;
                dec >> key >> val;
                dec >> proton::codec::finish();
                Json::Value decoded = TypeCodec::decode(val);
                result["type"] = decoded["type"];
                result["value"] = decoded["value"];
            } else {
                result["type"] = "none";
                result["value"] = Json::nullValue;
            }
        } catch (...) {
            result["type"] = "none";
            result["value"] = Json::nullValue;
        }
    } else if (jms_msg_type == JMS_STREAM_MESSAGE) {
        try {
            proton::codec::decoder dec(body);
            proton::codec::start s;
            dec >> s;
            if (s.size >= 1) {
                proton::value val;
                dec >> val;
                dec >> proton::codec::finish();
                Json::Value decoded = TypeCodec::decode(val);
                result["type"] = decoded["type"];
                result["value"] = decoded["value"];
            } else {
                result["type"] = "none";
                result["value"] = Json::nullValue;
            }
        } catch (...) {
            result["type"] = "none";
            result["value"] = Json::nullValue;
        }
    } else {
        // Unknown JMS type, fall back to regular AMQP decoding
        return TypeCodec::decode(body);
    }

    return result;
}

void Receiver::on_timeout() {
    // Output what we received so far
    output_result();

    if (received_count_ < expected_count_) {
        std::exit(1);  // Exit with error if we didn't get all messages
    }
}

void Receiver::output_result() {
    if (output_sent_) return;  // Already output, don't duplicate
    output_sent_ = true;

    Json::Value result;
    result["messages"] = received_messages_;
    result["stats"]["received"] = static_cast<Json::Value::UInt>(received_count_);

    Json::StreamWriterBuilder builder;
    builder["indentation"] = "  ";
    std::cout << Json::writeString(builder, result) << std::endl;
}

void Receiver::on_transport_error(proton::transport& t) {
    std::cerr << "Transport error: " << t.error() << std::endl;
}

void Receiver::on_error(const proton::error_condition& ec) {
    std::cerr << "Error: " << ec << std::endl;
}

} // namespace qit
