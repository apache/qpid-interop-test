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
                default:
                    throw new IllegalArgumentException("Unknown argument: " + args[i]);
            }
        }

        if (broker == null || queue == null || count == 0) {
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

    private JsonObject extractHeaders(Message message) throws Exception {
        JsonObject headers = new JsonObject();

        // JMSCorrelationID
        String corrId = message.getJMSCorrelationID();
        if (corrId != null) {
            headers.addProperty("JMSCorrelationID", corrId);
        }

        // Also check for correlation ID as bytes
        try {
            byte[] corrIdBytes = message.getJMSCorrelationIDAsBytes();
            if (corrIdBytes != null && corrIdBytes.length > 0) {
                JsonObject corrIdObj = new JsonObject();
                corrIdObj.addProperty("type", "bytes");
                corrIdObj.addProperty("value", bytesToHex(corrIdBytes));
                headers.add("JMSCorrelationID", corrIdObj);
            }
        } catch (JMSException e) {
            // Not set as bytes, ignore
        }

        // JMSReplyTo
        Destination replyTo = message.getJMSReplyTo();
        if (replyTo != null) {
            JsonObject replyToObj = new JsonObject();
            if (replyTo instanceof Queue) {
                replyToObj.addProperty("type", "queue");
                replyToObj.addProperty("value", ((Queue) replyTo).getQueueName());
            } else if (replyTo instanceof Topic) {
                replyToObj.addProperty("type", "topic");
                replyToObj.addProperty("value", ((Topic) replyTo).getTopicName());
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
}
