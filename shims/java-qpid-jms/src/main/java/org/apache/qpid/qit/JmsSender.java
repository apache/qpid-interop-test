package org.apache.qpid.qit;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import jakarta.jms.*;
import java.nio.ByteBuffer;
import java.util.Base64;

/**
 * JMS Sender Shim for QIT 2.0
 *
 * Sends JMS messages with support for:
 * - All JMS message types (Message, BytesMessage, MapMessage, StreamMessage, TextMessage)
 * - JMS headers (JMSCorrelationID, JMSReplyTo, JMSType)
 * - Application properties
 */
public class JmsSender {
    private Connection connection;
    private Session session;
    private MessageProducer producer;
    private int messagesSent = 0;

    public static void main(String[] args) {
        try {
            JmsSender sender = new JmsSender();
            sender.run(args);
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
        String type = null;
        String data = null;
        String headersJson = null;
        String propertiesJson = null;
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
                case "--type":
                    type = args[++i];
                    break;
                case "--data":
                    data = args[++i];
                    break;
                case "--headers":
                    headersJson = args[++i];
                    break;
                case "--properties":
                    propertiesJson = args[++i];
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
            System.err.println("Usage: JmsSender --broker <url> --queue <name> --type <jms_type> --data <json> [--headers <json>] [--properties <json>]");
            System.exit(1);
        }

        if (largeContent == null && (type == null || data == null)) {
            System.err.println("Usage: JmsSender --broker <url> --queue <name> --type <jms_type> --data <json> [--headers <json>] [--properties <json>]");
            System.exit(1);
        }

        // Connect to broker
        String brokerUrl = broker.startsWith("amqp://") ? broker : "amqp://" + broker;
        ConnectionFactory factory = new org.apache.qpid.jms.JmsConnectionFactory(brokerUrl);
        connection = factory.createConnection();
        connection.start();

        session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
        Destination destination = session.createQueue(queue);
        producer = session.createProducer(destination);

        // Large content mode
        if (largeContent != null) {
            if ("binary".equals(largeContent)) {
                byte[] contentData = lcgGenerateBytes(seed, size);
                BytesMessage message = session.createBytesMessage();
                message.writeBytes(contentData);
                producer.send(message, DeliveryMode.NON_PERSISTENT, Message.DEFAULT_PRIORITY, Message.DEFAULT_TIME_TO_LIVE);
            } else if ("string".equals(largeContent)) {
                String contentData = lcgGenerateString(seed, size);
                TextMessage message = session.createTextMessage(contentData);
                producer.send(message, DeliveryMode.NON_PERSISTENT, Message.DEFAULT_PRIORITY, Message.DEFAULT_TIME_TO_LIVE);
            } else if ("list".equals(largeContent)) {
                java.util.List<String> elems = generateCollectionElements(seed, elements, elementSize);
                StreamMessage message = session.createStreamMessage();
                for (String elem : elems) {
                    message.writeString(elem);
                }
                producer.send(message, DeliveryMode.NON_PERSISTENT, Message.DEFAULT_PRIORITY, Message.DEFAULT_TIME_TO_LIVE);
            } else if ("map".equals(largeContent)) {
                java.util.List<String> elems = generateCollectionElements(seed, elements, elementSize);
                java.util.List<String> keys = generateMapKeys(elements);
                MapMessage message = session.createMapMessage();
                for (int idx = 0; idx < elements; idx++) {
                    message.setString(keys.get(idx), elems.get(idx));
                }
                producer.send(message, DeliveryMode.NON_PERSISTENT, Message.DEFAULT_PRIORITY, Message.DEFAULT_TIME_TO_LIVE);
            } else {
                throw new IllegalArgumentException("Unknown large-content type: " + largeContent);
            }
            if ("list".equals(largeContent) || "map".equals(largeContent)) {
                System.out.println("{\"sent\": true, \"elements\": " + elements + ", \"element_size\": " + elementSize + "}");
            } else {
                System.out.println("{\"sent\": true, \"size\": " + size + "}");
            }

            // Cleanup
            producer.close();
            session.close();
            connection.close();
            return;
        }

        // Parse JSON data
        Gson gson = new Gson();
        JsonArray messages = gson.fromJson(data, JsonArray.class);
        JsonObject headers = headersJson != null ? gson.fromJson(headersJson, JsonObject.class) : new JsonObject();
        JsonObject properties = propertiesJson != null ? gson.fromJson(propertiesJson, JsonObject.class) : new JsonObject();

        // Send messages
        for (JsonElement element : messages) {
            JsonObject msgData = element.getAsJsonObject();
            Message message = createMessage(type, msgData);

            // Add headers
            addHeaders(message, headers);

            // Add properties
            addProperties(message, properties);

            producer.send(message, DeliveryMode.NON_PERSISTENT, Message.DEFAULT_PRIORITY, Message.DEFAULT_TIME_TO_LIVE);
            messagesSent++;
        }

        // Output result
        JsonObject result = new JsonObject();
        result.add("messages", messages);
        JsonObject stats = new JsonObject();
        stats.addProperty("sent", messagesSent);
        result.add("stats", stats);
        System.out.println(gson.toJson(result));

        // Cleanup
        producer.close();
        session.close();
        connection.close();
    }

    private Message createMessage(String jmsType, JsonObject msgData) throws Exception {
        int index = msgData.get("index").getAsInt();
        String subType = msgData.get("type").getAsString();
        JsonElement valueElement = msgData.get("value");

        switch (jmsType) {
            case "JMS_MESSAGE_TYPE":
                return createJmsMessage(index);

            case "JMS_BYTESMESSAGE_TYPE":
                return createJmsBytesMessage(index, subType, valueElement);

            case "JMS_MAPMESSAGE_TYPE":
                return createJmsMapMessage(index, subType, valueElement);

            case "JMS_STREAMMESSAGE_TYPE":
                return createJmsStreamMessage(index, subType, valueElement);

            case "JMS_TEXTMESSAGE_TYPE":
                return createJmsTextMessage(index, subType, valueElement);

            default:
                throw new IllegalArgumentException("Unknown JMS message type: " + jmsType);
        }
    }

    private Message createJmsMessage(int index) throws Exception {
        Message message = session.createMessage();
        message.setJMSMessageID("ID:" + index);
        return message;
    }

    private BytesMessage createJmsBytesMessage(int index, String subType, JsonElement valueElement) throws Exception {
        BytesMessage message = session.createBytesMessage();
        message.setJMSMessageID("ID:" + index);

        byte[] bytes = encodeValueAsBytes(subType, valueElement);
        message.writeBytes(bytes);

        return message;
    }

    private MapMessage createJmsMapMessage(int index, String subType, JsonElement valueElement) throws Exception {
        MapMessage message = session.createMapMessage();
        message.setJMSMessageID("ID:" + index);

        String key = String.format("%s_%03d", subType, index);
        Object value = encodeValue(subType, valueElement);

        // MapMessage setters by type
        if (value instanceof Boolean) {
            message.setBoolean(key, (Boolean) value);
        } else if (value instanceof Byte) {
            message.setByte(key, (Byte) value);
        } else if (value instanceof Short) {
            message.setShort(key, (Short) value);
        } else if (value instanceof Integer) {
            message.setInt(key, (Integer) value);
        } else if (value instanceof Long) {
            message.setLong(key, (Long) value);
        } else if (value instanceof Float) {
            message.setFloat(key, (Float) value);
        } else if (value instanceof Double) {
            message.setDouble(key, (Double) value);
        } else if (value instanceof String) {
            message.setString(key, (String) value);
        } else if (value instanceof byte[]) {
            message.setBytes(key, (byte[]) value);
        } else if (value instanceof Character) {
            message.setChar(key, (Character) value);
        } else {
            message.setObject(key, value);
        }

        return message;
    }

    private StreamMessage createJmsStreamMessage(int index, String subType, JsonElement valueElement) throws Exception {
        StreamMessage message = session.createStreamMessage();
        message.setJMSMessageID("ID:" + index);

        Object value = encodeValue(subType, valueElement);

        // StreamMessage writers by type
        if (value instanceof Boolean) {
            message.writeBoolean((Boolean) value);
        } else if (value instanceof Byte) {
            message.writeByte((Byte) value);
        } else if (value instanceof Short) {
            message.writeShort((Short) value);
        } else if (value instanceof Integer) {
            message.writeInt((Integer) value);
        } else if (value instanceof Long) {
            message.writeLong((Long) value);
        } else if (value instanceof Float) {
            message.writeFloat((Float) value);
        } else if (value instanceof Double) {
            message.writeDouble((Double) value);
        } else if (value instanceof String) {
            message.writeString((String) value);
        } else if (value instanceof byte[]) {
            message.writeBytes((byte[]) value);
        } else if (value instanceof Character) {
            message.writeChar((Character) value);
        } else {
            message.writeObject(value);
        }

        return message;
    }

    private TextMessage createJmsTextMessage(int index, String subType, JsonElement valueElement) throws Exception {
        TextMessage message = session.createTextMessage();
        message.setJMSMessageID("ID:" + index);

        if (subType.equals("text")) {
            String text = valueElement.isJsonNull() ? null : valueElement.getAsString();
            message.setText(text);
        } else {
            throw new IllegalArgumentException("TextMessage expects subType 'text', got: " + subType);
        }

        return message;
    }

    private Object encodeValue(String type, JsonElement valueElement) throws Exception {
        if (valueElement.isJsonNull()) {
            return null;
        }

        switch (type) {
            case "boolean":
                return valueElement.getAsBoolean() || valueElement.getAsString().equals("True");

            case "byte":
                return parseNumber(valueElement).byteValue();

            case "short":
                return parseNumber(valueElement).shortValue();

            case "int":
                return parseNumber(valueElement).intValue();

            case "long":
                return parseNumber(valueElement).longValue();

            case "float":
                return parseFloat(valueElement);

            case "double":
                return parseDouble(valueElement);

            case "string":
            case "text":
                return valueElement.getAsString();

            case "bytes":
                String hexString = valueElement.getAsString();
                return hexToBytes(hexString);

            case "char":
                String charStr = valueElement.getAsString();
                if (charStr.length() == 1) {
                    return charStr.charAt(0);
                } else {
                    // Assume it's a base64 encoded byte
                    byte[] decoded = Base64.getDecoder().decode(charStr);
                    return (char) decoded[0];
                }

            default:
                throw new IllegalArgumentException("Unknown type: " + type);
        }
    }

    private byte[] encodeValueAsBytes(String type, JsonElement valueElement) throws Exception {
        Object value = encodeValue(type, valueElement);

        if (value == null) {
            return new byte[0];
        }

        ByteBuffer buffer;

        switch (type) {
            case "boolean":
                return new byte[] { (Boolean) value ? (byte) 1 : (byte) 0 };

            case "byte":
                return new byte[] { (Byte) value };

            case "short":
                buffer = ByteBuffer.allocate(2);
                buffer.putShort((Short) value);
                return buffer.array();

            case "int":
                buffer = ByteBuffer.allocate(4);
                buffer.putInt((Integer) value);
                return buffer.array();

            case "long":
                buffer = ByteBuffer.allocate(8);
                buffer.putLong((Long) value);
                return buffer.array();

            case "float":
                buffer = ByteBuffer.allocate(4);
                buffer.putFloat((Float) value);
                return buffer.array();

            case "double":
                buffer = ByteBuffer.allocate(8);
                buffer.putDouble((Double) value);
                return buffer.array();

            case "string":
            case "text":
                String str = (String) value;
                // JMS BytesMessage expects modified UTF-8 with length prefix
                buffer = ByteBuffer.allocate(2 + str.length());
                buffer.putShort((short) str.length());
                buffer.put(str.getBytes("UTF-8"));
                return buffer.array();

            case "bytes":
                return (byte[]) value;

            case "char":
                // JMS expects 2-byte char
                buffer = ByteBuffer.allocate(2);
                buffer.putChar((Character) value);
                return buffer.array();

            default:
                throw new IllegalArgumentException("Cannot encode type as bytes: " + type);
        }
    }

    private Long parseNumber(JsonElement element) {
        String str = element.getAsString();
        if (str.startsWith("0x") || str.startsWith("0X")) {
            return Long.parseUnsignedLong(str.substring(2), 16);
        } else if (str.startsWith("-0x") || str.startsWith("-0X")) {
            return -Long.parseUnsignedLong(str.substring(3), 16);
        } else {
            return element.getAsLong();
        }
    }

    private Float parseFloat(JsonElement element) {
        String str = element.getAsString();
        if (str.startsWith("0x") || str.startsWith("0X")) {
            int bits = (int) Long.parseLong(str.substring(2), 16);
            return Float.intBitsToFloat(bits);
        } else {
            return element.getAsFloat();
        }
    }

    private Double parseDouble(JsonElement element) {
        String str = element.getAsString();
        if (str.startsWith("0x") || str.startsWith("0X")) {
            long bits = Long.parseUnsignedLong(str.substring(2), 16);
            return Double.longBitsToDouble(bits);
        } else {
            return element.getAsDouble();
        }
    }

    private byte[] hexToBytes(String hex) {
        int len = hex.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                    + Character.digit(hex.charAt(i + 1), 16));
        }
        return data;
    }

    private void addHeaders(Message message, JsonObject headers) throws Exception {
        if (headers.size() == 0) {
            return;
        }

        // JMSCorrelationID
        if (headers.has("JMSCorrelationID")) {
            JsonElement corrIdElement = headers.get("JMSCorrelationID");
            if (corrIdElement.isJsonPrimitive()) {
                message.setJMSCorrelationID(corrIdElement.getAsString());
            } else if (corrIdElement.isJsonObject()) {
                JsonObject corrIdObj = corrIdElement.getAsJsonObject();
                String type = corrIdObj.get("type").getAsString();
                JsonElement value = corrIdObj.get("value");

                if (type.equals("string")) {
                    message.setJMSCorrelationID(value.getAsString());
                } else if (type.equals("bytes")) {
                    byte[] bytes = hexToBytes(value.getAsString());
                    message.setJMSCorrelationIDAsBytes(bytes);
                }
            }
        }

        // JMSReplyTo
        if (headers.has("JMSReplyTo")) {
            JsonElement replyToElement = headers.get("JMSReplyTo");
            if (replyToElement.isJsonPrimitive()) {
                String replyTo = replyToElement.getAsString();
                // Default to queue
                message.setJMSReplyTo(session.createQueue(replyTo));
            } else if (replyToElement.isJsonObject()) {
                JsonObject replyToObj = replyToElement.getAsJsonObject();
                String type = replyToObj.get("type").getAsString();
                String value = replyToObj.get("value").getAsString();

                if (type.equals("queue")) {
                    message.setJMSReplyTo(session.createQueue(value));
                } else if (type.equals("topic")) {
                    message.setJMSReplyTo(session.createTopic(value));
                }
            }
        }

        // JMSType
        if (headers.has("JMSType")) {
            JsonElement typeElement = headers.get("JMSType");
            if (typeElement.isJsonPrimitive()) {
                message.setJMSType(typeElement.getAsString());
            } else if (typeElement.isJsonObject()) {
                JsonObject typeObj = typeElement.getAsJsonObject();
                message.setJMSType(typeObj.get("value").getAsString());
            }
        }
    }

    private void addProperties(Message message, JsonObject properties) throws Exception {
        if (properties.size() == 0) {
            return;
        }

        for (String propName : properties.keySet()) {
            JsonObject propObj = properties.getAsJsonObject(propName);
            String type = propObj.get("type").getAsString();
            JsonElement value = propObj.get("value");

            switch (type) {
                case "boolean":
                    message.setBooleanProperty(propName, value.getAsBoolean() || value.getAsString().equals("True"));
                    break;
                case "byte":
                    message.setByteProperty(propName, parseNumber(value).byteValue());
                    break;
                case "short":
                    message.setShortProperty(propName, parseNumber(value).shortValue());
                    break;
                case "int":
                    message.setIntProperty(propName, parseNumber(value).intValue());
                    break;
                case "long":
                    message.setLongProperty(propName, parseNumber(value).longValue());
                    break;
                case "float":
                    message.setFloatProperty(propName, parseFloat(value));
                    break;
                case "double":
                    message.setDoubleProperty(propName, parseDouble(value));
                    break;
                case "string":
                    message.setStringProperty(propName, value.getAsString());
                    break;
                default:
                    throw new IllegalArgumentException("Unknown property type: " + type);
            }
        }
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
}
