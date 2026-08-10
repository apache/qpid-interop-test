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

package org.apache.qpid.qit;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import jakarta.jms.*;
import java.nio.ByteBuffer;
import java.util.Enumeration;

/**
 * JMS Receiver Shim for QIT 2.0
 *
 * Receives JMS messages with support for:
 * - All JMS message types (Message, BytesMessage, MapMessage, StreamMessage, TextMessage)
 * - JMS headers (JMSCorrelationID, JMSReplyTo, JMSType)
 * - Application properties
 */
public class JmsReceiver {
    private Connection connection;
    private Session session;
    private MessageConsumer consumer;
    private int messagesReceived = 0;

    public static void main(String[] args) {
        try {
            JmsReceiver receiver = new JmsReceiver();
            receiver.run(args);
        } catch (Exception e) {
            System.err.println("ERROR: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    public void run(String[] args) throws Exception {
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

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--broker":
                    broker = args[++i];
                    break;
                case "--queue":
                    queue = args[++i];
                    break;
                case "--count":
                    count = Integer.parseInt(args[++i]);
                    break;
                case "--timeout":
                    timeout = Integer.parseInt(args[++i]);
                    break;
                case "--large-content":
                    largeContent = args[++i];
                    break;
                case "--size":
                    size = Integer.parseInt(args[++i]);
                    break;
                case "--seed":
                    seed = Integer.parseInt(args[++i]);
                    break;
                case "--elements":
                    elements = Integer.parseInt(args[++i]);
                    break;
                case "--element-size":
                    elementSize = Integer.parseInt(args[++i]);
                    break;
                default:
                    throw new IllegalArgumentException("Unknown argument: " + args[i]);
            }
        }

        if (broker == null || queue == null) {
            System.err.println("Usage: JmsReceiver --broker <url> --queue <name> --count <n> [--timeout <seconds>]");
            System.exit(1);
        }

        if (largeContent == null && count == 0) {
            System.err.println("Usage: JmsReceiver --broker <url> --queue <name> --count <n> [--timeout <seconds>]");
            System.exit(1);
        }

        // Connect to broker
        String brokerUrl = broker.startsWith("amqp://") ? broker : "amqp://" + broker;
        ConnectionFactory factory = new org.apache.qpid.jms.JmsConnectionFactory(brokerUrl);
        connection = factory.createConnection();
        connection.start();

        session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
        Destination destination = session.createQueue(queue);
        consumer = session.createConsumer(destination);

        // Large content mode
        if (largeContent != null) {
            long timeoutMs = timeout * 1000L;
            Message message = consumer.receive(timeoutMs);

            if (message == null) {
                System.out.println("{\"error\": \"timeout\", \"match\": false}");
            } else if ("binary".equals(largeContent)) {
                byte[] expected = lcgGenerateBytes(seed, size);
                if (message instanceof BytesMessage) {
                    BytesMessage bm = (BytesMessage) message;
                    byte[] received = new byte[(int) bm.getBodyLength()];
                    bm.readBytes(received);
                    int mismatch = -1;
                    int compareLen = Math.min(expected.length, received.length);
                    for (int i = 0; i < compareLen; i++) {
                        if (expected[i] != received[i]) {
                            mismatch = i;
                            break;
                        }
                    }
                    if (mismatch == -1 && expected.length != received.length) {
                        mismatch = compareLen;
                    }
                    if (mismatch == -1) {
                        System.out.println("{\"size\": " + received.length + ", \"expected_size\": " + size + ", \"match\": true}");
                    } else {
                        System.out.println("{\"size\": " + received.length + ", \"expected_size\": " + size + ", \"match\": false, \"first_mismatch_offset\": " + mismatch + "}");
                    }
                } else {
                    System.out.println("{\"match\": false, \"error\": \"expected BytesMessage, got " + message.getClass().getSimpleName() + "\"}");
                }
            } else if ("string".equals(largeContent)) {
                String expected = lcgGenerateString(seed, size);
                if (message instanceof TextMessage) {
                    String received = ((TextMessage) message).getText();
                    int mismatch = -1;
                    int compareLen = Math.min(expected.length(), received.length());
                    for (int i = 0; i < compareLen; i++) {
                        if (expected.charAt(i) != received.charAt(i)) {
                            mismatch = i;
                            break;
                        }
                    }
                    if (mismatch == -1 && expected.length() != received.length()) {
                        mismatch = compareLen;
                    }
                    if (mismatch == -1) {
                        System.out.println("{\"size\": " + received.length() + ", \"expected_size\": " + size + ", \"match\": true}");
                    } else {
                        System.out.println("{\"size\": " + received.length() + ", \"expected_size\": " + size + ", \"match\": false, \"first_mismatch_offset\": " + mismatch + "}");
                    }
                } else {
                    System.out.println("{\"match\": false, \"error\": \"expected TextMessage, got " + message.getClass().getSimpleName() + "\"}");
                }
            } else if ("list".equals(largeContent)) {
                java.util.List<String> expected = generateCollectionElements(seed, elements, elementSize);
                if (message instanceof StreamMessage) {
                    StreamMessage sm = (StreamMessage) message;
                    sm.reset();
                    java.util.List<String> received = new java.util.ArrayList<>();
                    try {
                        for (int idx = 0; idx < elements; idx++) {
                            received.add(sm.readString());
                        }
                    } catch (MessageEOFException e) {
                        // fewer elements than expected
                    }
                    outputCollectionResult(received, expected, elements, elementSize);
                } else {
                    System.out.println("{\"match\": false, \"error\": \"expected StreamMessage, got " + message.getClass().getSimpleName() + "\"}");
                }
            } else if ("map".equals(largeContent)) {
                java.util.List<String> expected = generateCollectionElements(seed, elements, elementSize);
                java.util.List<String> keys = generateMapKeys(elements);
                if (message instanceof MapMessage) {
                    MapMessage mm = (MapMessage) message;
                    java.util.List<String> received = new java.util.ArrayList<>();
                    for (String key : keys) {
                        String val = mm.getString(key);
                        received.add(val != null ? val : "");
                    }
                    outputCollectionResult(received, expected, elements, elementSize);
                } else {
                    System.out.println("{\"match\": false, \"error\": \"expected MapMessage, got " + message.getClass().getSimpleName() + "\"}");
                }
            } else {
                System.out.println("{\"match\": false, \"error\": \"unknown large-content type: " + largeContent + "\"}");
            }

            // Cleanup
            consumer.close();
            session.close();
            connection.close();
            return;
        }

        // Receive messages
        Gson gson = new GsonBuilder().serializeNulls().create();
        JsonArray messages = new JsonArray();

        long timeoutMs = timeout * 1000L;
        for (int i = 0; i < count; i++) {
            Message message = consumer.receive(timeoutMs);
            if (message == null) {
                break; // Timeout
            }

            JsonObject msgData = decodeMessage(message);
            messages.add(msgData);
            messagesReceived++;
        }

        // Output result
        JsonObject result = new JsonObject();
        result.add("messages", messages);
        JsonObject stats = new JsonObject();
        stats.addProperty("received", messagesReceived);
        result.add("stats", stats);
        System.out.println(gson.toJson(result));

        // Cleanup
        consumer.close();
        session.close();
        connection.close();
    }

    private JsonObject decodeMessage(Message message) throws Exception {
        JsonObject msgData = new JsonObject();

        // Set index from JMSMessageID if available
        String msgId = message.getJMSMessageID();
        int index = messagesReceived;
        if (msgId != null && msgId.startsWith("ID:")) {
            try {
                index = Integer.parseInt(msgId.substring(3));
            } catch (NumberFormatException e) {
                // Use messagesReceived as fallback
            }
        }
        msgData.addProperty("index", index);

        // Decode based on message type
        // Check specific types first, then generic Message last
        if (message instanceof TextMessage) {
            TextMessage textMsg = (TextMessage) message;
            msgData.addProperty("type", "text");
            String text = textMsg.getText();
            if (text == null) {
                msgData.add("value", com.google.gson.JsonNull.INSTANCE);
            } else {
                msgData.addProperty("value", text);
            }

        } else if (message instanceof BytesMessage) {
            BytesMessage bytesMsg = (BytesMessage) message;
            long bodyLength = bytesMsg.getBodyLength();
            byte[] bytes = new byte[(int) bodyLength];
            bytesMsg.readBytes(bytes);

            // Try to infer type from byte array structure
            JsonObject decoded = decodeBytes(bytes);
            msgData.addProperty("type", decoded.get("type").getAsString());
            msgData.add("value", decoded.get("value"));

        } else if (message instanceof MapMessage) {
            MapMessage mapMsg = (MapMessage) message;
            Enumeration<?> mapNames = mapMsg.getMapNames();

            if (mapNames.hasMoreElements()) {
                String key = (String) mapNames.nextElement();
                Object value = mapMsg.getObject(key);

                // Infer type from value
                JsonObject decoded = decodeObject(value);
                msgData.addProperty("type", decoded.get("type").getAsString());
                msgData.add("value", decoded.get("value"));
            } else {
                msgData.addProperty("type", "unknown");
                msgData.add("value", com.google.gson.JsonNull.INSTANCE);
            }

        } else if (message instanceof StreamMessage) {
            StreamMessage streamMsg = (StreamMessage) message;
            streamMsg.reset(); // Reset to read from start

            try {
                Object value = streamMsg.readObject();
                JsonObject decoded = decodeObject(value);
                msgData.addProperty("type", decoded.get("type").getAsString());
                msgData.add("value", decoded.get("value"));
            } catch (MessageEOFException e) {
                msgData.addProperty("type", "none");
                msgData.add("value", com.google.gson.JsonNull.INSTANCE);
            }

        } else {
            // Plain JMS Message (no body) or unknown type
            msgData.addProperty("type", "none");
            msgData.add("value", com.google.gson.JsonNull.INSTANCE);
        }

        // Add headers if present
        JsonObject headers = extractHeaders(message);
        if (headers.size() > 0) {
            msgData.add("headers", headers);
        }

        // Add properties if present
        JsonObject properties = extractProperties(message);
        if (properties.size() > 0) {
            msgData.add("properties", properties);
        }

        return msgData;
    }

    private JsonObject decodeBytes(byte[] bytes) {
        JsonObject result = new JsonObject();

        if (bytes.length == 0) {
            result.addProperty("type", "bytes");
            result.addProperty("value", "");
            return result;
        }

        // Try to detect type based on length and structure
        if (bytes.length == 1) {
            // Could be boolean or byte
            if (bytes[0] == 0 || bytes[0] == 1) {
                result.addProperty("type", "boolean");
                result.addProperty("value", bytes[0] == 1);
            } else {
                result.addProperty("type", "byte");
                result.addProperty("value", String.format("0x%02x", bytes[0]));
            }

        } else if (bytes.length == 2) {
            // Could be short or char
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            short shortValue = buffer.getShort();
            result.addProperty("type", "short");
            result.addProperty("value", String.format("0x%04x", shortValue & 0xFFFF));

        } else if (bytes.length == 4) {
            // Could be int or float
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            int intValue = buffer.getInt();
            result.addProperty("type", "int");
            result.addProperty("value", String.format("0x%08x", intValue));

        } else if (bytes.length == 8) {
            // Could be long or double
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            long longValue = buffer.getLong();
            result.addProperty("type", "long");
            result.addProperty("value", String.format("0x%016x", longValue));

        } else if (bytes.length > 2 && bytes[0] == 0 && bytes[1] > 0) {
            // Could be string (length-prefixed)
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            short length = buffer.getShort();
            if (length == bytes.length - 2) {
                byte[] strBytes = new byte[length];
                buffer.get(strBytes);
                result.addProperty("type", "string");
                result.addProperty("value", new String(strBytes, java.nio.charset.StandardCharsets.UTF_8));
                return result;
            }

            // Default to bytes
            result.addProperty("type", "bytes");
            result.addProperty("value", bytesToHex(bytes));

        } else {
            // Default to bytes
            result.addProperty("type", "bytes");
            result.addProperty("value", bytesToHex(bytes));
        }

        return result;
    }

    private JsonObject decodeObject(Object value) {
        JsonObject result = new JsonObject();

        if (value == null) {
            result.addProperty("type", "none");
            result.add("value", com.google.gson.JsonNull.INSTANCE);

        } else if (value instanceof Boolean) {
            result.addProperty("type", "boolean");
            result.addProperty("value", (Boolean) value);

        } else if (value instanceof Byte) {
            result.addProperty("type", "byte");
            result.addProperty("value", String.format("0x%02x", (Byte) value));

        } else if (value instanceof Short) {
            result.addProperty("type", "short");
            result.addProperty("value", String.format("0x%04x", (Short) value & 0xFFFF));

        } else if (value instanceof Integer) {
            result.addProperty("type", "int");
            result.addProperty("value", String.format("0x%08x", (Integer) value));

        } else if (value instanceof Long) {
            result.addProperty("type", "long");
            result.addProperty("value", String.format("0x%016x", (Long) value));

        } else if (value instanceof Float) {
            result.addProperty("type", "float");
            int bits = Float.floatToRawIntBits((Float) value);
            result.addProperty("value", String.format("0x%08x", bits));

        } else if (value instanceof Double) {
            result.addProperty("type", "double");
            long bits = Double.doubleToRawLongBits((Double) value);
            result.addProperty("value", String.format("0x%016x", bits));

        } else if (value instanceof String) {
            result.addProperty("type", "string");
            result.addProperty("value", (String) value);

        } else if (value instanceof byte[]) {
            result.addProperty("type", "bytes");
            result.addProperty("value", bytesToHex((byte[]) value));

        } else if (value instanceof Character) {
            result.addProperty("type", "char");
            // Encode as base64
            byte[] charBytes = new byte[] { (byte) ((Character) value).charValue() };
            result.addProperty("value", java.util.Base64.getEncoder().encodeToString(charBytes));

        } else {
            result.addProperty("type", "string");
            result.addProperty("value", value.toString());
        }

        return result;
    }

    private static String stripAddressPrefix(String name) {
        if (name.startsWith("queue://")) return name.substring(8);
        if (name.startsWith("topic://")) return name.substring(8);
        return name;
    }

    private JsonObject extractHeaders(Message message) throws Exception {
        JsonObject headers = new JsonObject();

        // JMSCorrelationID — try bytes first for binary correlation IDs,
        // fall back to string for normal string correlation IDs
        try {
            byte[] corrIdBytes = message.getJMSCorrelationIDAsBytes();
            if (corrIdBytes != null && corrIdBytes.length > 0) {
                JsonObject corrIdObj = new JsonObject();
                corrIdObj.addProperty("type", "bytes");
                corrIdObj.addProperty("value", bytesToHex(corrIdBytes));
                headers.add("JMSCorrelationID", corrIdObj);
            }
        } catch (JMSException e) {
            // Not available as bytes, try string
            String corrId = message.getJMSCorrelationID();
            if (corrId != null) {
                headers.addProperty("JMSCorrelationID", corrId);
            }
        }

        // JMSReplyTo
        Destination replyTo = message.getJMSReplyTo();
        if (replyTo != null) {
            JsonObject replyToObj = new JsonObject();
            if (replyTo instanceof Queue) {
                replyToObj.addProperty("type", "queue");
                replyToObj.addProperty("value", stripAddressPrefix(((Queue) replyTo).getQueueName()));
            } else if (replyTo instanceof Topic) {
                replyToObj.addProperty("type", "topic");
                replyToObj.addProperty("value", stripAddressPrefix(((Topic) replyTo).getTopicName()));
            } else {
                replyToObj.addProperty("type", "unknown");
                replyToObj.addProperty("value", replyTo.toString());
            }
            headers.add("JMSReplyTo", replyToObj);
        }

        // JMSType
        String jmsType = message.getJMSType();
        if (jmsType != null) {
            headers.addProperty("JMSType", jmsType);
        }

        return headers;
    }

    private JsonObject extractProperties(Message message) throws Exception {
        JsonObject properties = new JsonObject();

        Enumeration<?> propertyNames = message.getPropertyNames();
        while (propertyNames.hasMoreElements()) {
            String propName = (String) propertyNames.nextElement();

            // Skip JMS-reserved properties
            if (propName.startsWith("JMS")) {
                continue;
            }

            Object propValue = message.getObjectProperty(propName);

            JsonObject propObj = new JsonObject();

            if (propValue instanceof Boolean) {
                propObj.addProperty("type", "boolean");
                propObj.addProperty("value", (Boolean) propValue);

            } else if (propValue instanceof Byte) {
                propObj.addProperty("type", "byte");
                propObj.addProperty("value", String.format("0x%02x", (Byte) propValue));

            } else if (propValue instanceof Short) {
                propObj.addProperty("type", "short");
                propObj.addProperty("value", String.format("0x%04x", (Short) propValue & 0xFFFF));

            } else if (propValue instanceof Integer) {
                propObj.addProperty("type", "int");
                propObj.addProperty("value", String.format("0x%08x", (Integer) propValue));

            } else if (propValue instanceof Long) {
                propObj.addProperty("type", "long");
                propObj.addProperty("value", String.format("0x%016x", (Long) propValue));

            } else if (propValue instanceof Float) {
                propObj.addProperty("type", "float");
                int bits = Float.floatToRawIntBits((Float) propValue);
                propObj.addProperty("value", String.format("0x%08x", bits));

            } else if (propValue instanceof Double) {
                propObj.addProperty("type", "double");
                long bits = Double.doubleToRawLongBits((Double) propValue);
                propObj.addProperty("value", String.format("0x%016x", bits));

            } else if (propValue instanceof String) {
                propObj.addProperty("type", "string");
                propObj.addProperty("value", (String) propValue);

            } else {
                propObj.addProperty("type", "string");
                propObj.addProperty("value", propValue.toString());
            }

            properties.add(propName, propObj);
        }

        return properties;
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
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

    private void outputCollectionResult(java.util.List<String> received, java.util.List<String> expected, int elementsCount, int elementSize) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"elements\": ").append(received.size());
        sb.append(", \"element_size\": ").append(elementSize);

        if (received.size() != elementsCount) {
            sb.append(", \"match\": false}");
            System.out.println(sb.toString());
            System.exit(1);
        } else {
            boolean matched = true;
            int mismatchElem = -1;
            int mismatchOffset = -1;
            for (int i = 0; i < elementsCount; i++) {
                String exp = expected.get(i);
                String rcv = received.get(i);
                if (!exp.equals(rcv)) {
                    matched = false;
                    mismatchElem = i;
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
            System.out.println(sb.toString());
            if (!matched) System.exit(1);
        }
    }
}
