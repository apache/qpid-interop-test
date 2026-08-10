/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

/*
 * QIT C++ Proton Shim - Sender Implementation
 */

#include "qit_shim.hpp"
#include <json/json.h>
#include <proton/duration.hpp>
#include <proton/message_id.hpp>
#include <proton/transport.hpp>
#include <proton/annotation_key.hpp>
#include <proton/symbol.hpp>
#include <proton/codec/encoder.hpp>
#include <proton/codec/decoder.hpp>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <vector>
#include <cstdio>
#include <cstring>
#include <cstdint>

namespace qit {

Sender::Sender(const std::string& broker_url,
               const std::string& queue_name,
               const std::string& amqp_type,
               const std::string& test_data_json,
               bool jms_mode,
               const std::string& headers_json,
               const std::string& properties_json,
               const std::string& message_header_json)
    : broker_url_(broker_url),
      queue_name_(queue_name),
      amqp_type_(amqp_type),
      sent_count_(0),
      confirmed_count_(0),
      jms_mode_(jms_mode) {

    // Parse JSON test data
    Json::CharReaderBuilder builder;
    Json::Value root;
    std::istringstream iss(test_data_json);
    std::string errors;

    if (!Json::parseFromStream(builder, iss, &root, &errors)) {
        throw std::runtime_error("Failed to parse JSON test data: " + errors);
    }

    if (!root.isArray()) {
        throw std::runtime_error("Test data must be a JSON array");
    }

    test_values_ = root;

    // Parse headers JSON if provided
    if (!headers_json.empty()) {
        Json::CharReaderBuilder hbuilder;
        std::istringstream hiss(headers_json);
        std::string herrors;
        if (!Json::parseFromStream(hbuilder, hiss, &headers_, &herrors)) {
            throw std::runtime_error("Failed to parse headers JSON: " + herrors);
        }
    }

    // Parse properties JSON if provided
    if (!properties_json.empty()) {
        Json::CharReaderBuilder pbuilder;
        std::istringstream piss(properties_json);
        std::string perrors;
        if (!Json::parseFromStream(pbuilder, piss, &properties_, &perrors)) {
            throw std::runtime_error("Failed to parse properties JSON: " + perrors);
        }
    }

    // Parse message header JSON if provided
    if (!message_header_json.empty()) {
        Json::CharReaderBuilder mbuilder;
        std::istringstream miss(message_header_json);
        std::string merrors;
        if (!Json::parseFromStream(mbuilder, miss, &message_header_, &merrors)) {
            throw std::runtime_error("Failed to parse message header JSON: " + merrors);
        }
    }
}

int8_t Sender::get_jms_message_type(const std::string& amqp_type) const {
    // JMS message type constants (from Qpid JMS Client)
    const int8_t JMS_MESSAGE = 0;        // Empty message
    const int8_t JMS_MAP_MESSAGE = 2;    // Map
    const int8_t JMS_BYTES_MESSAGE = 3;  // Binary data
    const int8_t JMS_STREAM_MESSAGE = 4; // List/stream
    const int8_t JMS_TEXT_MESSAGE = 5;   // String/text

    if (amqp_type == "string") {
        return JMS_TEXT_MESSAGE;
    } else if (amqp_type == "binary") {
        return JMS_BYTES_MESSAGE;
    } else if (amqp_type == "null") {
        return JMS_MESSAGE;
    } else if (amqp_type == "map") {
        return JMS_MAP_MESSAGE;
    } else if (amqp_type == "list") {
        return JMS_STREAM_MESSAGE;
    }

    return -1;
}

void Sender::on_container_start(proton::container& c) {
    c.open_sender(broker_url_ + "/" + queue_name_);
}

void Sender::on_sendable(proton::sender& s) {
    while (s.credit() && sent_count_ < test_values_.size()) {
        proton::message msg;
        const Json::Value& test_value = test_values_[static_cast<int>(sent_count_)];

        msg.id(proton::message_id(test_value["index"].asInt()));

        if (jms_mode_ && amqp_type_ == "map") {
            std::string sub_type = test_value["type"].asString();
            int index = test_value["index"].asInt();
            char key_buf[64];
            snprintf(key_buf, sizeof(key_buf), "%s_%03d", sub_type.c_str(), index);
            std::string key(key_buf);
            proton::value encoded_value = TypeCodec::encode(sub_type, test_value["value"]);

            proton::value body;
            proton::codec::encoder enc(body);
            enc << proton::codec::start::map();
            enc << key << encoded_value;
            enc << proton::codec::finish();
            msg.body(body);
        } else if (jms_mode_ && amqp_type_ == "list") {
            std::string sub_type = test_value["type"].asString();
            proton::value encoded_value = TypeCodec::encode(sub_type, test_value["value"]);

            proton::value body;
            proton::codec::encoder enc(body);
            enc << proton::codec::start::list();
            enc << encoded_value;
            enc << proton::codec::finish();
            msg.body(body);
        } else if (TypeCodec::is_complex_type(amqp_type_)) {
            msg.body(TypeCodec::encode_complex(amqp_type_, test_value["value"]));
        } else {
            msg.body(TypeCodec::encode(amqp_type_, test_value["value"]));
        }

        // Add JMS annotations if in JMS mode
        if (jms_mode_) {
            int8_t jms_type = get_jms_message_type(amqp_type_);
            if (jms_type >= 0) {
                // NOTE: Key MUST be symbol, value MUST be byte (not ubyte)
                // This matches Qpid JMS Client wire format
                proton::annotation_key jms_key(proton::symbol("x-opt-jms-msg-type"));
                msg.message_annotations().put(jms_key, jms_type);
            }
        }

        if (!headers_.isNull()) {
            apply_headers(msg);
        }

        if (!properties_.isNull()) {
            apply_properties(msg);
        }

        if (!message_header_.isNull()) {
            apply_message_header(msg);
        }

        s.send(msg);
        sent_count_++;
    }
}

void Sender::apply_headers(proton::message& msg) {
    if (headers_.isMember("JMSCorrelationID")) {
        const Json::Value& h = headers_["JMSCorrelationID"];
        std::string htype = h["type"].asString();
        if (htype == "string") {
            msg.correlation_id(h["value"].asString());
        } else if (htype == "bytes") {
            msg.correlation_id(hex_to_binary(h["value"].asString()));
        }
    }
    if (headers_.isMember("JMSReplyTo")) {
        const Json::Value& h = headers_["JMSReplyTo"];
        msg.reply_to(h["value"].asString());
        int8_t reply_type = (h["type"].asString() == "topic") ? 1 : 0;
        proton::annotation_key rt_key(proton::symbol("x-opt-jms-reply-to"));
        msg.message_annotations().put(rt_key, reply_type);
    }
    if (headers_.isMember("JMSType")) {
        msg.subject(headers_["JMSType"]["value"].asString());
    }
}

void Sender::apply_properties(proton::message& msg) {
    std::map<std::string, proton::scalar> props;
    for (auto it = properties_.begin(); it != properties_.end(); ++it) {
        std::string name = it.key().asString();
        const Json::Value& prop = *it;
        std::string ptype = prop["type"].asString();
        std::string pvalue = prop["value"].asString();

        if (ptype == "boolean") {
            props[name] = (pvalue == "true");
        } else if (ptype == "byte") {
            unsigned long val = std::stoull(pvalue, nullptr, 16);
            props[name] = static_cast<int8_t>(val);
        } else if (ptype == "short") {
            unsigned long val = std::stoull(pvalue, nullptr, 16);
            props[name] = static_cast<int16_t>(val);
        } else if (ptype == "int") {
            unsigned long val = std::stoull(pvalue, nullptr, 16);
            props[name] = static_cast<int32_t>(val);
        } else if (ptype == "long") {
            uint64_t val = std::stoull(pvalue, nullptr, 16);
            int64_t sval;
            std::memcpy(&sval, &val, sizeof(sval));
            props[name] = sval;
        } else if (ptype == "float") {
            uint32_t bits = static_cast<uint32_t>(std::stoull(pvalue, nullptr, 16));
            float fval;
            std::memcpy(&fval, &bits, sizeof(fval));
            props[name] = fval;
        } else if (ptype == "double") {
            uint64_t bits = std::stoull(pvalue, nullptr, 16);
            double dval;
            std::memcpy(&dval, &bits, sizeof(dval));
            props[name] = dval;
        } else if (ptype == "string") {
            props[name] = pvalue;
        }
    }

    // Set application properties on the message
    for (auto& kv : props) {
        msg.properties().put(kv.first, kv.second);
    }
}

void Sender::apply_message_header(proton::message& msg) {
    if (message_header_.isMember("durable"))
        msg.durable(message_header_["durable"].asBool());
    if (message_header_.isMember("priority"))
        msg.priority(static_cast<uint8_t>(message_header_["priority"].asInt()));
    if (message_header_.isMember("ttl"))
        msg.ttl(proton::duration(message_header_["ttl"].asUInt()));
    if (message_header_.isMember("first_acquirer"))
        msg.first_acquirer(message_header_["first_acquirer"].asBool());
}

void Sender::on_tracker_accept(proton::tracker& t) {
    confirmed_count_++;

    if (confirmed_count_ == test_values_.size()) {
        // Output result as JSON
        Json::Value result;
        result["messages"] = test_values_;
        result["stats"]["sent"] = static_cast<Json::Value::UInt>(sent_count_);

        Json::StreamWriterBuilder builder;
        builder["indentation"] = "  ";
        std::cout << Json::writeString(builder, result) << std::endl;

        t.sender().close();
        t.connection().close();
    }
}

void Sender::on_transport_error(proton::transport& t) {
    std::cerr << "Transport error: " << t.error() << std::endl;
}

void Sender::on_error(const proton::error_condition& ec) {
    std::cerr << "Error: " << ec << std::endl;
}

// --- LCG PRNG functions ---

std::vector<uint8_t> lcg_generate_bytes(uint32_t seed, size_t size) {
    uint32_t state = seed & 0x7FFFFFFF;
    std::vector<uint8_t> result(size);
    for (size_t i = 0; i < size; i++) {
        state = (state * 1103515245u + 12345u) & 0x7FFFFFFF;
        result[i] = (state >> 16) & 0xFF;
    }
    return result;
}

std::string lcg_generate_string(uint32_t seed, size_t size) {
    auto raw = lcg_generate_bytes(seed, size);
    std::string result(size, '\0');
    for (size_t i = 0; i < size; i++) {
        result[i] = static_cast<char>(32 + (raw[i] % 95));
    }
    return result;
}

std::vector<std::string> generate_collection_elements(uint32_t seed, size_t count, size_t elem_size) {
    size_t total = count * elem_size;
    std::string full = lcg_generate_string(seed, total);
    std::vector<std::string> result;
    result.reserve(count);
    for (size_t i = 0; i < count; i++) {
        result.push_back(full.substr(i * elem_size, elem_size));
    }
    return result;
}

std::vector<std::string> generate_map_keys(size_t count) {
    std::vector<std::string> keys;
    keys.reserve(count);
    char buf[16];
    for (size_t i = 0; i < count; i++) {
        std::snprintf(buf, sizeof(buf), "key_%04zu", i);
        keys.push_back(std::string(buf));
    }
    return keys;
}

// --- Large Content Sender ---

LargeContentSender::LargeContentSender(const std::string& broker_url,
                                       const std::string& queue_name,
                                       const std::string& content_type,
                                       uint32_t seed,
                                       size_t size,
                                       bool jms_mode,
                                       size_t elements,
                                       size_t element_size)
    : broker_url_(broker_url),
      queue_name_(queue_name),
      content_type_(content_type),
      seed_(seed),
      size_(size),
      jms_mode_(jms_mode),
      sent_(false),
      elements_(elements),
      element_size_(element_size) {}

void LargeContentSender::on_container_start(proton::container& c) {
    c.open_sender(broker_url_ + "/" + queue_name_);
}

void LargeContentSender::on_sendable(proton::sender& s) {
    if (sent_) return;
    sent_ = true;

    proton::message msg;
    int8_t jms_msg_type = -1;

    if (content_type_ == "binary") {
        auto data = lcg_generate_bytes(seed_, size_);
        proton::binary bin(data.begin(), data.end());
        msg.body(bin);
        jms_msg_type = 3;  // JMS_BYTES_MESSAGE
    } else if (content_type_ == "string") {
        std::string str = lcg_generate_string(seed_, size_);
        msg.body(str);
        jms_msg_type = 5;  // JMS_TEXT_MESSAGE
    } else if (content_type_ == "list") {
        auto elements = generate_collection_elements(seed_, elements_, element_size_);
        proton::value body;
        proton::codec::encoder enc(body);
        enc << proton::codec::start::list();
        for (const auto& elem : elements) {
            enc << elem;
        }
        enc << proton::codec::finish();
        msg.body(body);
        jms_msg_type = 4;  // JMS_STREAM_MESSAGE
    } else if (content_type_ == "array") {
        auto elements = generate_collection_elements(seed_, elements_, element_size_);
        proton::value body;
        proton::codec::encoder enc(body);
        enc << proton::codec::start::array(proton::STRING);
        for (const auto& elem : elements) {
            enc << elem;
        }
        enc << proton::codec::finish();
        msg.body(body);
        jms_msg_type = -1;
    } else if (content_type_ == "map") {
        auto elements = generate_collection_elements(seed_, elements_, element_size_);
        auto keys = generate_map_keys(elements_);
        proton::value body;
        proton::codec::encoder enc(body);
        enc << proton::codec::start::map();
        for (size_t i = 0; i < elements_; i++) {
            enc << keys[i] << elements[i];
        }
        enc << proton::codec::finish();
        msg.body(body);
        jms_msg_type = 2;  // JMS_MAP_MESSAGE
    } else if (content_type_ == "described") {
        auto elements = generate_collection_elements(seed_, elements_, element_size_);
        proton::value body;
        proton::codec::encoder enc(body);
        enc << proton::codec::start::described();
        enc << proton::symbol("test.large.described");
        enc << proton::codec::start::list();
        for (const auto& elem : elements) {
            enc << elem;
        }
        enc << proton::codec::finish();
        enc << proton::codec::finish();
        msg.body(body);
        jms_msg_type = -1;
    }

    if (jms_mode_ && jms_msg_type >= 0) {
        proton::annotation_key jms_key(proton::symbol("x-opt-jms-msg-type"));
        msg.message_annotations().put(jms_key, jms_msg_type);
    }

    s.send(msg);
}

void LargeContentSender::on_tracker_accept(proton::tracker& t) {
    // Output result as JSON
    Json::Value result;
    result["sent"] = true;
    if (content_type_ == "list" || content_type_ == "array" ||
        content_type_ == "map" || content_type_ == "described") {
        result["elements"] = static_cast<Json::Value::UInt64>(elements_);
        result["element_size"] = static_cast<Json::Value::UInt64>(element_size_);
    } else {
        result["size"] = static_cast<Json::Value::UInt64>(size_);
    }

    Json::StreamWriterBuilder builder;
    builder["indentation"] = "  ";
    std::cout << Json::writeString(builder, result) << std::endl;

    t.sender().close();
    t.connection().close();
}

void LargeContentSender::on_transport_error(proton::transport& t) {
    std::cerr << "Transport error: " << t.error() << std::endl;
}

} // namespace qit
