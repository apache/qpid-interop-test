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
#include <proton/message_id.hpp>
#include <proton/codec/encoder.hpp>
#include <proton/codec/decoder.hpp>
#include <iostream>
#include <vector>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <cstdint>

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

        // Extract JMS headers
        Json::Value headers(Json::objectValue);
        try {
            proton::message_id cid = m.correlation_id();
            proton::type_id cid_type = cid.type();
            if (cid_type == proton::BINARY) {
                proton::binary bin = proton::get<proton::binary>(cid);
                Json::Value cid_obj;
                cid_obj["type"] = "bytes";
                cid_obj["value"] = binary_to_hex(bin);
                headers["JMSCorrelationID"] = cid_obj;
            } else if (cid_type == proton::STRING) {
                headers["JMSCorrelationID"] = proton::get<std::string>(cid);
            }
        } catch (...) {}

        std::string reply_to = m.reply_to();
        if (!reply_to.empty()) {
            Json::Value rt_obj;
            std::string reply_type = "queue";
            proton::annotation_key rt_key(proton::symbol("x-opt-jms-reply-to"));
            if (m.message_annotations().exists(rt_key)) {
                proton::value rt_val = m.message_annotations().get(rt_key);
                if (proton::get<int8_t>(rt_val) == 1) reply_type = "topic";
            } else if (reply_to.substr(0, 8) == "topic://") {
                reply_type = "topic";
                reply_to = reply_to.substr(8);
            } else if (reply_to.substr(0, 8) == "queue://") {
                reply_to = reply_to.substr(8);
            }
            rt_obj["type"] = reply_type;
            rt_obj["value"] = reply_to;
            headers["JMSReplyTo"] = rt_obj;
        }

        std::string subject = m.subject();
        if (!subject.empty()) {
            headers["JMSType"] = subject;
        }

        if (headers.size() > 0) {
            msg_data["headers"] = headers;
        }

        // Extract application properties
        Json::Value props(Json::objectValue);
        try {
            if (!m.properties().empty()) {
                const proton::value& pval = m.properties().value();
                proton::codec::decoder dec(pval);
                proton::codec::start s;
                dec >> s;
                for (size_t pi = 0; pi < s.size / 2; ++pi) {
                    std::string key;
                    proton::scalar val;
                    dec >> key >> val;

                    Json::Value prop_obj;
                    proton::type_id tid = val.type();
                    char hex_buf[32];

                    if (tid == proton::BOOLEAN) {
                        prop_obj["type"] = "boolean";
                        prop_obj["value"] = proton::get<bool>(val);
                    } else if (tid == proton::BYTE) {
                        prop_obj["type"] = "byte";
                        int8_t v = proton::get<int8_t>(val);
                        snprintf(hex_buf, sizeof(hex_buf), "0x%02x", static_cast<unsigned int>(v & 0xFF));
                        prop_obj["value"] = std::string(hex_buf);
                    } else if (tid == proton::SHORT) {
                        prop_obj["type"] = "short";
                        int16_t v = proton::get<int16_t>(val);
                        snprintf(hex_buf, sizeof(hex_buf), "0x%04x", static_cast<unsigned int>(v & 0xFFFF));
                        prop_obj["value"] = std::string(hex_buf);
                    } else if (tid == proton::INT) {
                        prop_obj["type"] = "int";
                        int32_t v = proton::get<int32_t>(val);
                        snprintf(hex_buf, sizeof(hex_buf), "0x%08x", static_cast<unsigned int>(v));
                        prop_obj["value"] = std::string(hex_buf);
                    } else if (tid == proton::LONG) {
                        prop_obj["type"] = "long";
                        int64_t v = proton::get<int64_t>(val);
                        snprintf(hex_buf, sizeof(hex_buf), "0x%016llx", static_cast<unsigned long long>(v));
                        prop_obj["value"] = std::string(hex_buf);
                    } else if (tid == proton::FLOAT) {
                        prop_obj["type"] = "float";
                        float fv = proton::get<float>(val);
                        uint32_t bits;
                        std::memcpy(&bits, &fv, sizeof(bits));
                        snprintf(hex_buf, sizeof(hex_buf), "0x%08x", bits);
                        prop_obj["value"] = std::string(hex_buf);
                    } else if (tid == proton::DOUBLE) {
                        prop_obj["type"] = "double";
                        double dv = proton::get<double>(val);
                        uint64_t bits;
                        std::memcpy(&bits, &dv, sizeof(bits));
                        snprintf(hex_buf, sizeof(hex_buf), "0x%016llx", static_cast<unsigned long long>(bits));
                        prop_obj["value"] = std::string(hex_buf);
                    } else if (tid == proton::STRING) {
                        prop_obj["type"] = "string";
                        prop_obj["value"] = proton::get<std::string>(val);
                    } else {
                        continue;
                    }

                    props[key] = prop_obj;
                }
                dec >> proton::codec::finish();
            }
        } catch (...) {}

        if (props.size() > 0) {
            msg_data["properties"] = props;
        }

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

// --- Large Content Receiver ---

LargeContentReceiver::LargeContentReceiver(const std::string& broker_url,
                                           const std::string& queue_name,
                                           const std::string& content_type,
                                           uint32_t seed,
                                           size_t size,
                                           int timeout_sec)
    : broker_url_(broker_url),
      queue_name_(queue_name),
      content_type_(content_type),
      seed_(seed),
      size_(size),
      timeout_sec_(timeout_sec),
      received_(false) {}

void LargeContentReceiver::on_container_start(proton::container& c) {
    c.open_receiver(broker_url_ + "/" + queue_name_);

    if (timeout_sec_ > 0) {
        proton::work timeout_work = proton::make_work([this]() {
            this->on_timeout();
        });
        c.schedule(proton::duration(timeout_sec_ * 1000), timeout_work);
    }
}

void LargeContentReceiver::on_message(proton::delivery& d, proton::message& m) {
    if (received_) return;
    received_ = true;

    Json::Value result;

    try {
        if (content_type_ == "binary") {
            proton::binary received_bin = proton::get<proton::binary>(m.body());
            auto expected = lcg_generate_bytes(seed_, size_);

            size_t received_size = received_bin.size();
            result["size"] = static_cast<Json::Value::UInt64>(received_size);
            result["expected_size"] = static_cast<Json::Value::UInt64>(size_);

            if (received_size != size_) {
                result["match"] = false;
            } else {
                bool match = true;
                for (size_t i = 0; i < size_; i++) {
                    if (static_cast<uint8_t>(received_bin[i]) != expected[i]) {
                        result["match"] = false;
                        result["first_mismatch_offset"] = static_cast<Json::Value::UInt64>(i);
                        match = false;
                        break;
                    }
                }
                if (match) {
                    result["match"] = true;
                }
            }
        } else {
            std::string received_str = proton::get<std::string>(m.body());
            std::string expected = lcg_generate_string(seed_, size_);

            size_t received_size = received_str.size();
            result["size"] = static_cast<Json::Value::UInt64>(received_size);
            result["expected_size"] = static_cast<Json::Value::UInt64>(size_);

            if (received_size != size_) {
                result["match"] = false;
            } else if (received_str == expected) {
                result["match"] = true;
            } else {
                result["match"] = false;
                for (size_t i = 0; i < size_; i++) {
                    if (received_str[i] != expected[i]) {
                        result["first_mismatch_offset"] = static_cast<Json::Value::UInt64>(i);
                        break;
                    }
                }
            }
        }
    } catch (const std::exception& e) {
        result["match"] = false;
        result["error"] = std::string("Failed to extract body: ") + e.what();
    }

    Json::StreamWriterBuilder builder;
    builder["indentation"] = "  ";
    std::cout << Json::writeString(builder, result) << std::endl;

    d.receiver().close();
    d.connection().close();
}

void LargeContentReceiver::on_timeout() {
    if (!received_) {
        Json::Value result;
        result["match"] = false;
        result["error"] = "no message received";

        Json::StreamWriterBuilder builder;
        builder["indentation"] = "  ";
        std::cout << Json::writeString(builder, result) << std::endl;

        std::exit(1);
    }
}

void LargeContentReceiver::on_transport_error(proton::transport& t) {
    std::cerr << "Transport error: " << t.error() << std::endl;
}

} // namespace qit
