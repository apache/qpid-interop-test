/*
 * QIT ProtonJ2 Shim - Sender
 */
package org.apache.qpid.qit;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import org.apache.qpid.protonj2.client.Client;
import org.apache.qpid.protonj2.client.Connection;
import org.apache.qpid.protonj2.client.ConnectionOptions;
import org.apache.qpid.protonj2.client.Message;

import java.net.URI;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class Sender {
    public static void main(String[] args) throws Exception {
        // Parse command-line arguments
        String broker = null;
        String queue = null;
        String type = null;
        String data = null;
        String headersJson = null;
        String propertiesJson = null;
        boolean jmsMode = false;
        String largeContent = null;
        int size = 0;
        int seed = 0;
        int elements = 0;
        int elementSize = 0;

        for (int i = 1; i < args.length; i++) {
            String arg = args[i];

            // Check for flags (no value)
            if ("--jms-mode".equals(arg)) {
                jmsMode = true;
                continue;
            }

            // Regular options (key-value pairs)
            if (i + 1 >= args.length) {
                System.err.println("Missing value for option: " + arg);
                System.exit(1);
            }

            String key = arg.replace("--", "");
            String value = args[i + 1];

            switch (key) {
                case "broker":
                    broker = value;
                    break;
                case "queue":
                    queue = value;
                    break;
                case "type":
                    type = value;
                    break;
                case "data":
                    data = value;
                    break;
                case "headers":
                    headersJson = value;
                    break;
                case "properties":
                    propertiesJson = value;
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
            i++;  // Skip the value in next iteration
        }

        // Large content send path
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
                 org.apache.qpid.protonj2.client.Sender sender = connection.openSender(queue)) {

                Message<Object> message = Message.create();
                byte jmsMsgType = -1;

                if ("binary".equals(largeContent)) {
                    message.body(lcgGenerateBytes(seed, size));
                    jmsMsgType = 3;
                } else if ("string".equals(largeContent)) {
                    message.body(lcgGenerateString(seed, size));
                    jmsMsgType = 5;
                } else if ("list".equals(largeContent)) {
                    java.util.List<String> elems = generateCollectionElements(seed, elements, elementSize);
                    message.body(new java.util.ArrayList<Object>(elems));
                    jmsMsgType = 4; // STREAM_MESSAGE
                } else if ("array".equals(largeContent)) {
                    java.util.List<String> elems = generateCollectionElements(seed, elements, elementSize);
                    message.body(elems.toArray(new String[0]));
                } else if ("map".equals(largeContent)) {
                    java.util.List<String> elems = generateCollectionElements(seed, elements, elementSize);
                    java.util.List<String> keys = generateMapKeys(elements);
                    java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
                    for (int idx = 0; idx < elements; idx++) {
                        map.put(keys.get(idx), elems.get(idx));
                    }
                    message.body(map);
                    jmsMsgType = 2; // MAP_MESSAGE
                } else if ("described".equals(largeContent)) {
                    java.util.List<String> elems = generateCollectionElements(seed, elements, elementSize);
                    message.body(new org.apache.qpid.protonj2.types.UnknownDescribedType(
                        org.apache.qpid.protonj2.types.Symbol.valueOf("test.large.described"),
                        new java.util.ArrayList<Object>(elems)));
                } else {
                    System.err.println("Unknown large-content type: " + largeContent);
                    System.exit(1);
                }

                if (jmsMode && jmsMsgType >= 0) {
                    message.annotation("x-opt-jms-msg-type", jmsMsgType);
                }

                sender.send(message);
            }

            // Output result
            StringBuilder sb = new StringBuilder();
            sb.append("{\"sent\": true");
            if ("binary".equals(largeContent) || "string".equals(largeContent)) {
                sb.append(", \"size\": ").append(size);
            } else {
                sb.append(", \"elements\": ").append(elements);
                sb.append(", \"element_size\": ").append(elementSize);
            }
            sb.append("}");
            System.out.println(sb.toString());
            return;
        }

        if (broker == null || queue == null || type == null || data == null) {
            System.err.println("Missing required arguments");
            System.exit(1);
        }

        // Parse broker URL
        URI brokerUri = parseBrokerUrl(broker);

        // Parse test data
        Gson gson = new Gson();
        JsonArray testData = gson.fromJson(data, JsonArray.class);

        // Create client and connect
        Client client = Client.create();
        ConnectionOptions options = new ConnectionOptions();
        options.user("artemis");
        options.password("artemis");

        try (Connection connection = client.connect(brokerUri.getHost(), brokerUri.getPort(), options);
             org.apache.qpid.protonj2.client.Sender sender = connection.openSender(queue)) {

            JsonObject headers = null;
            if (headersJson != null) {
                headers = gson.fromJson(headersJson, JsonObject.class);
            }

            JsonObject properties = null;
            if (propertiesJson != null) {
                properties = gson.fromJson(propertiesJson, JsonObject.class);
            }

            List<JsonObject> messages = new ArrayList<>();

            // Send all messages
            for (int i = 0; i < testData.size(); i++) {
                JsonObject testMsg = testData.get(i).getAsJsonObject();
                int index = testMsg.get("index").getAsInt();
                Object value = testMsg.get("value");

                Message<Object> message = Message.create();
                message.messageId(String.valueOf(index));

                if (jmsMode && type.equals("map")) {
                    String subType = testMsg.has("type") ? testMsg.get("type").getAsString() : "string";
                    String key = String.format("%s_%03d", subType, index);
                    Object encodedValue = TypeCodec.encode(subType, value);
                    Map<String, Object> mapBody = new LinkedHashMap<>();
                    mapBody.put(key, encodedValue);
                    message.body(mapBody);
                } else if (jmsMode && type.equals("list")) {
                    String subType = testMsg.has("type") ? testMsg.get("type").getAsString() : "string";
                    Object encodedValue = TypeCodec.encode(subType, value);
                    List<Object> listBody = new ArrayList<>();
                    listBody.add(encodedValue);
                    message.body(listBody);
                } else if (TypeCodec.isComplexType(type)) {
                    message.body(TypeCodec.encodeComplex(type, value));
                } else {
                    message.body(TypeCodec.encode(type, value));
                }

                // Add JMS annotations if in JMS mode
                if (jmsMode) {
                    byte jmsType = getJmsMessageType(type);
                    if (jmsType >= 0) {
                        // NOTE: Key MUST be Symbol, value MUST be signed byte
                        // This matches Qpid JMS Client wire format
                        message.annotation("x-opt-jms-msg-type", jmsType);
                    }
                }

                // Apply JMS headers
                if (headers != null) {
                    if (headers.has("JMSCorrelationID")) {
                        JsonObject h = headers.getAsJsonObject("JMSCorrelationID");
                        String htype = h.get("type").getAsString();
                        if ("string".equals(htype)) {
                            message.correlationId(h.get("value").getAsString());
                        } else if ("bytes".equals(htype)) {
                            System.err.println("Error: ProtonJ2 does not support binary correlation IDs");
                            System.exit(1);
                        }
                    }
                    if (headers.has("JMSReplyTo")) {
                        JsonObject h = headers.getAsJsonObject("JMSReplyTo");
                        message.replyTo(h.get("value").getAsString());
                        byte replyType = (byte) ("topic".equals(h.get("type").getAsString()) ? 1 : 0);
                        message.annotation("x-opt-jms-reply-to", replyType);
                    }
                    if (headers.has("JMSType")) {
                        JsonObject h = headers.getAsJsonObject("JMSType");
                        message.subject(h.get("value").getAsString());
                    }
                }

                // Apply JMS application properties
                if (properties != null) {
                    for (Map.Entry<String, JsonElement> entry : properties.entrySet()) {
                        String name = entry.getKey();
                        JsonObject prop = entry.getValue().getAsJsonObject();
                        String ptype = prop.get("type").getAsString();
                        switch (ptype) {
                            case "boolean":
                                message.property(name, prop.get("value").getAsBoolean());
                                break;
                            case "byte": {
                                String hex = prop.get("value").getAsString().replace("0x", "");
                                long val = Long.parseUnsignedLong(hex, 16);
                                message.property(name, (byte) val);
                                break;
                            }
                            case "short": {
                                String hex = prop.get("value").getAsString().replace("0x", "");
                                long val = Long.parseUnsignedLong(hex, 16);
                                message.property(name, (short) val);
                                break;
                            }
                            case "int": {
                                String hex = prop.get("value").getAsString().replace("0x", "");
                                long val = Long.parseUnsignedLong(hex, 16);
                                message.property(name, (int) val);
                                break;
                            }
                            case "long": {
                                String hex = prop.get("value").getAsString().replace("0x", "");
                                long val = Long.parseUnsignedLong(hex, 16);
                                message.property(name, val);
                                break;
                            }
                            case "float": {
                                String hex = prop.get("value").getAsString().replace("0x", "");
                                long val = Long.parseUnsignedLong(hex, 16);
                                float floatVal = Float.intBitsToFloat((int) val);
                                message.property(name, floatVal);
                                break;
                            }
                            case "double": {
                                String hex = prop.get("value").getAsString().replace("0x", "");
                                long val = Long.parseUnsignedLong(hex, 16);
                                double doubleVal = Double.longBitsToDouble(val);
                                message.property(name, doubleVal);
                                break;
                            }
                            case "string":
                                message.property(name, prop.get("value").getAsString());
                                break;
                        }
                    }
                }

                sender.send(message);

                // Record sent message
                JsonObject msgResult = new JsonObject();
                msgResult.addProperty("index", index);
                msgResult.addProperty("type", type);

                // Explicitly handle null values - must include "value" key even when null
                JsonElement valueElement = testMsg.get("value");
                if (valueElement == null || valueElement.isJsonNull()) {
                    msgResult.add("value", com.google.gson.JsonNull.INSTANCE);
                } else {
                    msgResult.add("value", valueElement);
                }
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
            stats.addProperty("sent", messages.size());
            result.add("stats", stats);

            Gson prettyGson = new GsonBuilder()
                .setPrettyPrinting()
                .serializeNulls()  // Force serialization of null values
                .create();
            System.out.println(prettyGson.toJson(result));
        }
    }

    private static URI parseBrokerUrl(String broker) throws Exception {
        if (!broker.startsWith("amqp://")) {
            broker = "amqp://" + broker;
        }
        URI uri = new URI(broker);
        return uri;
    }

    private static byte[] hexToBytes(String hex) {
        int len = hex.length();
        byte[] result = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            result[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                                   + Character.digit(hex.charAt(i + 1), 16));
        }
        return result;
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

    private static byte getJmsMessageType(String amqpType) {
        // JMS message type constants (from Qpid JMS Client)
        final byte JMS_MESSAGE = 0;        // Empty message
        final byte JMS_MAP_MESSAGE = 2;    // Map
        final byte JMS_BYTES_MESSAGE = 3;  // Binary data
        final byte JMS_STREAM_MESSAGE = 4; // List/stream
        final byte JMS_TEXT_MESSAGE = 5;   // String/text

        switch (amqpType) {
            case "string":
                return JMS_TEXT_MESSAGE;
            case "binary":
                return JMS_BYTES_MESSAGE;
            case "null":
                return JMS_MESSAGE;
            case "map":
                return JMS_MAP_MESSAGE;
            case "list":
                return JMS_STREAM_MESSAGE;
            default:
                return -1;
        }
    }
}
