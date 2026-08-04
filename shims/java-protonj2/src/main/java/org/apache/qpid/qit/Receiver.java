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
