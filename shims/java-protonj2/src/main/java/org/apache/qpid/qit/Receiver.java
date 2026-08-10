/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * QIT ProtonJ2 Shim - Receiver
 */
package org.apache.qpid.qit;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.apache.qpid.protonj2.client.Client;
import org.apache.qpid.protonj2.client.Connection;
import org.apache.qpid.protonj2.client.ConnectionOptions;
import org.apache.qpid.protonj2.client.Delivery;
import org.apache.qpid.protonj2.client.Message;

import java.net.URI;
import java.util.ArrayList;
import java.util.List;

public class Receiver {
    public static void main(String[] args) throws Exception {
        // Parse command-line arguments
        String broker = null;
        String queue = null;
        int count = 0;
        int timeout = 30;
        String largeContent = null;
        int size = 0;
        int seed = 0;
        int elements = 0;
        int elementSize = 0;

        for (int i = 1; i < args.length; i += 2) {
            String key = args[i].replace("--", "");
            String value = args[i + 1];

            switch (key) {
                case "broker":
                    broker = value;
                    break;
                case "queue":
                    queue = value;
                    break;
                case "count":
                    count = Integer.parseInt(value);
                    break;
                case "timeout":
                    timeout = Integer.parseInt(value);
                    break;
                case "large-content":
                    largeContent = value;
                    break;
                case "size":
                    size = Integer.parseInt(value);
                    break;
                case "seed":
                    seed = Integer.parseInt(value);
                    break;
                case "elements":
                    elements = Integer.parseInt(value);
                    break;
                case "element-size":
                    elementSize = Integer.parseInt(value);
                    break;
            }
        }

        // Large content receive path
        if (largeContent != null) {
            if (broker == null || queue == null) {
                System.err.println("Missing required arguments");
                System.exit(1);
            }

            URI brokerUri = parseBrokerUrl(broker);

            Client client = Client.create();
            ConnectionOptions options = new ConnectionOptions();
            options.user("artemis");
            options.password("artemis");

            try (Connection connection = client.connect(brokerUri.getHost(), brokerUri.getPort(), options);
                 org.apache.qpid.protonj2.client.Receiver receiver = connection.openReceiver(queue)) {

                Delivery delivery = receiver.receive(timeout, java.util.concurrent.TimeUnit.SECONDS);
                if (delivery == null) {
                    System.out.println("{\"received\": false, \"error\": \"timeout\"}");
                    System.exit(1);
                    return;
                }

                Message<?> message = delivery.message();
                Object body = message.body();

                boolean match;
                int receivedSize;

                if ("binary".equals(largeContent)) {
                    byte[] expected = lcgGenerateBytes(seed, size);
                    byte[] received;
                    if (body instanceof byte[]) {
                        received = (byte[]) body;
                    } else if (body instanceof org.apache.qpid.protonj2.types.Binary) {
                        org.apache.qpid.protonj2.types.Binary bin = (org.apache.qpid.protonj2.types.Binary) body;
                        received = bin.asByteArray();
                    } else {
                        System.out.println("{\"received\": true, \"match\": false, \"error\": \"expected byte[] but got " + body.getClass().getSimpleName() + "\"}");
                        System.exit(1);
                        return;
                    }
                    receivedSize = received.length;
                    int mismatchOffset = -1;
                    if (received.length != expected.length) {
                        match = false;
                    } else {
                        match = true;
                        for (int i = 0; i < expected.length; i++) {
                            if (received[i] != expected[i]) {
                                match = false;
                                mismatchOffset = i;
                                break;
                            }
                        }
                    }
                    StringBuilder sb = new StringBuilder();
                    sb.append("{\"size\": ").append(receivedSize)
                      .append(", \"expected_size\": ").append(size)
                      .append(", \"match\": ").append(match);
                    if (mismatchOffset >= 0)
                        sb.append(", \"first_mismatch_offset\": ").append(mismatchOffset);
                    sb.append("}");
                    System.out.println(sb.toString());
                    if (!match) System.exit(1);
                    return;
                } else if ("string".equals(largeContent)) {
                    String expected = lcgGenerateString(seed, size);
                    String received;
                    if (body instanceof String) {
                        received = (String) body;
                    } else {
                        System.out.println("{\"received\": true, \"match\": false, \"error\": \"expected String but got " + body.getClass().getSimpleName() + "\"}");
                        System.exit(1);
                        return;
                    }
                    receivedSize = received.length();
                    int mismatchOffset = -1;
                    if (received.length() != expected.length()) {
                        match = false;
                    } else {
                        match = true;
                        for (int i = 0; i < expected.length(); i++) {
                            if (received.charAt(i) != expected.charAt(i)) {
                                match = false;
                                mismatchOffset = i;
                                break;
                            }
                        }
                    }
                    StringBuilder sb = new StringBuilder();
                    sb.append("{\"size\": ").append(receivedSize)
                      .append(", \"expected_size\": ").append(size)
                      .append(", \"match\": ").append(match);
                    if (mismatchOffset >= 0)
                        sb.append(", \"first_mismatch_offset\": ").append(mismatchOffset);
                    sb.append("}");
                    System.out.println(sb.toString());
                    if (!match) System.exit(1);
                    return;
                } else if ("list".equals(largeContent) || "array".equals(largeContent) ||
                           "map".equals(largeContent) || "described".equals(largeContent)) {
                    java.util.List<String> expected = generateCollectionElements(seed, elements, elementSize);
                    java.util.List<String> received = new java.util.ArrayList<>();

                    if ("list".equals(largeContent)) {
                        if (body instanceof java.util.List) {
                            for (Object elem : (java.util.List<?>) body) {
                                received.add(elem.toString());
                            }
                        } else {
                            System.out.println("{\"match\": false, \"error\": \"expected List, got " + body.getClass().getSimpleName() + "\"}");
                            System.exit(1);
                            return;
                        }
                    } else if ("array".equals(largeContent)) {
                        if (body instanceof String[]) {
                            for (String s : (String[]) body) received.add(s);
                        } else if (body instanceof Object[]) {
                            for (Object o : (Object[]) body) received.add(o.toString());
                        } else if (body instanceof java.util.List) {
                            for (Object elem : (java.util.List<?>) body) received.add(elem.toString());
                        } else {
                            System.out.println("{\"match\": false, \"error\": \"expected array, got " + body.getClass().getSimpleName() + "\"}");
                            System.exit(1);
                            return;
                        }
                    } else if ("map".equals(largeContent)) {
                        if (body instanceof java.util.Map) {
                            java.util.List<String> keys = generateMapKeys(elements);
                            java.util.Map<?, ?> map = (java.util.Map<?, ?>) body;
                            for (String key : keys) {
                                Object val = map.get(key);
                                received.add(val != null ? val.toString() : "");
                            }
                        } else {
                            System.out.println("{\"match\": false, \"error\": \"expected Map, got " + body.getClass().getSimpleName() + "\"}");
                            System.exit(1);
                            return;
                        }
                    } else if ("described".equals(largeContent)) {
                        Object inner = body;
                        if (body instanceof org.apache.qpid.protonj2.types.DescribedType) {
                            inner = ((org.apache.qpid.protonj2.types.DescribedType) body).getDescribed();
                        }
                        if (inner instanceof java.util.List) {
                            for (Object elem : (java.util.List<?>) inner) {
                                received.add(elem.toString());
                            }
                        } else {
                            System.out.println("{\"match\": false, \"error\": \"expected described list, got " + (inner != null ? inner.getClass().getSimpleName() : "null") + "\"}");
                            System.exit(1);
                            return;
                        }
                    }

                    // Compare element by element
                    StringBuilder sb = new StringBuilder();
                    sb.append("{\"elements\": ").append(received.size());
                    sb.append(", \"element_size\": ").append(elementSize);

                    if (received.size() != elements) {
                        sb.append(", \"match\": false}");
                    } else {
                        boolean matched = true;
                        int mismatchElem = -1;
                        int mismatchOffset = -1;
                        for (int idx = 0; idx < elements; idx++) {
                            String exp = expected.get(idx);
                            String rcv = received.get(idx);
                            if (!exp.equals(rcv)) {
                                matched = false;
                                mismatchElem = idx;
                                int minLen = Math.min(exp.length(), rcv.length());
                                for (int j = 0; j < minLen; j++) {
                                    if (exp.charAt(j) != rcv.charAt(j)) {
                                        mismatchOffset = j;
                                        break;
                                    }
                                }
                                if (mismatchOffset == -1) mismatchOffset = minLen;
                                break;
                            }
                        }
                        sb.append(", \"match\": ").append(matched);
                        if (mismatchElem >= 0) {
                            sb.append(", \"first_mismatch_element\": ").append(mismatchElem);
                            sb.append(", \"first_mismatch_offset\": ").append(mismatchOffset);
                        }
                        sb.append("}");
                    }

                    System.out.println(sb.toString());
                    if (!sb.toString().contains("\"match\": true")) System.exit(1);
                    return;
                }
            }
        }

        if (broker == null || queue == null || count == 0) {
            System.err.println("Missing required arguments");
            System.exit(1);
        }

        // Parse broker URL
        URI brokerUri = parseBrokerUrl(broker);

        // Create client and connect
        Client client = Client.create();
        ConnectionOptions options = new ConnectionOptions();
        options.user("artemis");
        options.password("artemis");

        try (Connection connection = client.connect(brokerUri.getHost(), brokerUri.getPort(), options);
             org.apache.qpid.protonj2.client.Receiver receiver = connection.openReceiver(queue)) {

            List<JsonObject> messages = new ArrayList<>();

            // Receive messages
            for (int i = 0; i < count; i++) {
                Delivery delivery = receiver.receive(timeout, java.util.concurrent.TimeUnit.SECONDS);
                
                if (delivery == null) {
                    break;  // Timeout
                }

                Message<?> message = delivery.message();

                // Check for JMS message type annotation
                byte jmsType = -1;
                if (message.hasAnnotation("x-opt-jms-msg-type")) {
                    Object annotation = message.annotation("x-opt-jms-msg-type");
                    if (annotation instanceof Byte) {
                        jmsType = (Byte) annotation;
                    }
                }

                TypeCodec.DecodedMessage decoded;
                if (jmsType >= 0) {
                    // Decode as JMS message
                    decoded = decodeJmsMessage(message.body(), jmsType);
                } else {
                    // Decode as regular AMQP message
                    decoded = TypeCodec.decode(message.body());
                }

                JsonObject msgResult = new JsonObject();
                msgResult.addProperty("index", i);
                msgResult.addProperty("type", decoded.type);
                msgResult.add("value", decoded.value);

                // Extract JMS headers
                JsonObject hdrs = new JsonObject();
                Object corrId = message.correlationId();
                if (corrId != null) {
                    if (corrId instanceof byte[]) {
                        byte[] corrBytes = (byte[]) corrId;
                        JsonObject corrObj = new JsonObject();
                        corrObj.addProperty("type", "bytes");
                        corrObj.addProperty("value", bytesToHex(corrBytes));
                        hdrs.add("JMSCorrelationID", corrObj);
                    } else {
                        hdrs.addProperty("JMSCorrelationID", corrId.toString());
                    }
                }
                String replyTo = message.replyTo();
                if (replyTo != null) {
                    JsonObject rtObj = new JsonObject();
                    String replyType = "queue";
                    if (message.hasAnnotation("x-opt-jms-reply-to")) {
                        Object rt = message.annotation("x-opt-jms-reply-to");
                        if (rt instanceof Byte && ((Byte) rt) == 1) replyType = "topic";
                    } else if (replyTo.startsWith("topic://")) {
                        replyType = "topic";
                        replyTo = replyTo.substring(8);
                    } else if (replyTo.startsWith("queue://")) {
                        replyTo = replyTo.substring(8);
                    }
                    rtObj.addProperty("type", replyType);
                    rtObj.addProperty("value", replyTo);
                    hdrs.add("JMSReplyTo", rtObj);
                }
                String subj = message.subject();
                if (subj != null) {
                    hdrs.addProperty("JMSType", subj);
                }
                if (hdrs.size() > 0) {
                    msgResult.add("headers", hdrs);
                }

                // Extract application properties
                JsonObject propsJson = new JsonObject();
                message.forEachProperty((name, value) -> {
                    JsonObject propObj = new JsonObject();
                    if (value instanceof Boolean) {
                        propObj.addProperty("type", "boolean");
                        propObj.addProperty("value", (Boolean) value);
                    } else if (value instanceof Byte) {
                        byte b = (Byte) value;
                        propObj.addProperty("type", "byte");
                        propObj.addProperty("value", String.format("0x%02x", b & 0xFF));
                    } else if (value instanceof Short) {
                        short s = (Short) value;
                        propObj.addProperty("type", "short");
                        propObj.addProperty("value", String.format("0x%04x", s & 0xFFFF));
                    } else if (value instanceof Integer) {
                        int iv = (Integer) value;
                        propObj.addProperty("type", "int");
                        propObj.addProperty("value", String.format("0x%08x", iv));
                    } else if (value instanceof Long) {
                        long l = (Long) value;
                        propObj.addProperty("type", "long");
                        propObj.addProperty("value", String.format("0x%016x", l));
                    } else if (value instanceof Float) {
                        float f = (Float) value;
                        propObj.addProperty("type", "float");
                        propObj.addProperty("value", String.format("0x%08x", Float.floatToRawIntBits(f)));
                    } else if (value instanceof Double) {
                        double d = (Double) value;
                        propObj.addProperty("type", "double");
                        propObj.addProperty("value", String.format("0x%016x", Double.doubleToRawLongBits(d)));
                    } else if (value instanceof String) {
                        propObj.addProperty("type", "string");
                        propObj.addProperty("value", (String) value);
                    }
                    if (propObj.size() > 0) {
                        propsJson.add(name, propObj);
                    }
                });
                if (propsJson.size() > 0) {
                    msgResult.add("properties", propsJson);
                }

                // Extract AMQP Header section fields
                JsonObject msgHeader = new JsonObject();
                msgHeader.addProperty("durable", message.durable());
                msgHeader.addProperty("priority", (int) message.priority());
                msgHeader.addProperty("ttl", message.timeToLive());
                msgHeader.addProperty("first_acquirer", message.firstAcquirer());
                msgHeader.addProperty("delivery_count", (int) message.deliveryCount());
                msgResult.add("message_header", msgHeader);

                messages.add(msgResult);
            }

            // Output result
            JsonObject result = new JsonObject();
            JsonArray messagesArray = new JsonArray();
            for (JsonObject msg : messages) {
                messagesArray.add(msg);
            }
            result.add("messages", messagesArray);

            JsonObject stats = new JsonObject();
            stats.addProperty("received", messages.size());
            result.add("stats", stats);

            Gson prettyGson = new GsonBuilder()
                .setPrettyPrinting()
                .serializeNulls()  // Force serialization of null values
                .create();
            System.out.println(prettyGson.toJson(result));

            if (messages.size() < count) {
                System.exit(1);
            }
        }
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    private static URI parseBrokerUrl(String broker) throws Exception {
        if (!broker.startsWith("amqp://")) {
            broker = "amqp://" + broker;
        }
        URI uri = new URI(broker);
        return uri;
    }

    private static byte[] lcgGenerateBytes(int seed, int size) {
        int state = seed & 0x7FFFFFFF;
        byte[] result = new byte[size];
        for (int i = 0; i < size; i++) {
            state = (int)(((long)state * 1103515245L + 12345L) & 0x7FFFFFFFL);
            result[i] = (byte)((state >> 16) & 0xFF);
        }
        return result;
    }

    private static String lcgGenerateString(int seed, int size) {
        byte[] raw = lcgGenerateBytes(seed, size);
        char[] chars = new char[size];
        for (int i = 0; i < size; i++) {
            chars[i] = (char)(32 + ((raw[i] & 0xFF) % 95));
        }
        return new String(chars);
    }

    private static java.util.List<String> generateCollectionElements(int seed, int count, int elemSize) {
        int total = count * elemSize;
        String full = lcgGenerateString(seed, total);
        java.util.List<String> result = new java.util.ArrayList<>();
        for (int i = 0; i < count; i++) {
            result.add(full.substring(i * elemSize, (i + 1) * elemSize));
        }
        return result;
    }

    private static java.util.List<String> generateMapKeys(int count) {
        java.util.List<String> keys = new java.util.ArrayList<>();
        for (int i = 0; i < count; i++) {
            keys.add(String.format("key_%04d", i));
        }
        return keys;
    }

    private static TypeCodec.DecodedMessage decodeJmsMessage(Object body, byte jmsType) {
        // JMS message type constants
        final byte JMS_MESSAGE = 0;
        final byte JMS_MAP_MESSAGE = 2;
        final byte JMS_BYTES_MESSAGE = 3;
        final byte JMS_STREAM_MESSAGE = 4;
        final byte JMS_TEXT_MESSAGE = 5;

        if (jmsType == JMS_TEXT_MESSAGE) {
            // TextMessage: body is string in AmqpValue section
            TypeCodec.DecodedMessage result = new TypeCodec.DecodedMessage();
            result.type = "text";  // Use 'text' to match JMS shim output
            if (body instanceof String) {
                result.value = new com.google.gson.JsonPrimitive((String) body);
            } else {
                result.value = com.google.gson.JsonNull.INSTANCE;
            }
            return result;
        } else if (jmsType == JMS_BYTES_MESSAGE) {
            // BytesMessage: body is binary in Data section
            TypeCodec.DecodedMessage result = new TypeCodec.DecodedMessage();
            result.type = "bytes";
            if (body instanceof byte[]) {
                byte[] bytes = (byte[]) body;
                StringBuilder hex = new StringBuilder();
                for (byte b : bytes) {
                    hex.append(String.format("%02x", b));
                }
                result.value = new com.google.gson.JsonPrimitive(hex.toString());
            } else {
                result.value = com.google.gson.JsonNull.INSTANCE;
            }
            return result;
        } else if (jmsType == JMS_MESSAGE) {
            // Empty message
            TypeCodec.DecodedMessage result = new TypeCodec.DecodedMessage();
            result.type = "null";
            result.value = com.google.gson.JsonNull.INSTANCE;
            return result;
        }

        if (jmsType == JMS_MAP_MESSAGE) {
            if (body instanceof java.util.Map) {
                java.util.Map<?, ?> map = (java.util.Map<?, ?>) body;
                if (!map.isEmpty()) {
                    Object firstValue = map.values().iterator().next();
                    return TypeCodec.decode(firstValue);
                }
            }
            TypeCodec.DecodedMessage result = new TypeCodec.DecodedMessage();
            result.type = "none";
            result.value = com.google.gson.JsonNull.INSTANCE;
            return result;
        }

        if (jmsType == JMS_STREAM_MESSAGE) {
            if (body instanceof java.util.List) {
                java.util.List<?> list = (java.util.List<?>) body;
                if (!list.isEmpty()) {
                    return TypeCodec.decode(list.get(0));
                }
            }
            TypeCodec.DecodedMessage result = new TypeCodec.DecodedMessage();
            result.type = "none";
            result.value = com.google.gson.JsonNull.INSTANCE;
            return result;
        }

        // Unknown JMS type, fall back to regular AMQP decoding
        return TypeCodec.decode(body);
    }
}
