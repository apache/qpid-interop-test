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
package org.apache.qpid.interop_test.jms_hdrs_props_test;

import java.io.Serializable;
import java.io.StringReader;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import javax.jms.BytesMessage;
import javax.jms.Connection;
import javax.jms.ConnectionFactory;
import javax.jms.DeliveryMode;
import javax.jms.ExceptionListener;
import javax.jms.JMSException;
import javax.jms.MapMessage;
import javax.jms.Message;
import javax.jms.MessageProducer;
import javax.jms.ObjectMessage;
import javax.jms.Queue;
import javax.jms.Session;
import javax.jms.StreamMessage;
import javax.jms.TextMessage;
import javax.json.Json;
import javax.json.JsonArray;
import javax.json.JsonObject;
import javax.json.JsonReader;
import org.apache.qpid.jms.JmsConnectionFactory;

public class Sender {
    private static final String USER = "guest";
    private static final String PASSWORD = "guest";
    private static final String[] SUPPORTED_JMS_MESSAGE_TYPES = {"JMS_MESSAGE_TYPE",
                                                                 "JMS_BYTESMESSAGE_TYPE",
                                                                 "JMS_MAPMESSAGE_TYPE",
                                                                 "JMS_OBJECTMESSAGE_TYPE",
                                                                 "JMS_STREAMMESSAGE_TYPE",
                                                                 "JMS_TEXTMESSAGE_TYPE"};
    Connection _connection;
    Session _session;
    Queue _queue;
    MessageProducer _messageProducer;
    int _msgsSent;
    

    // args[0]: Broker URL
    // args[1]: Queue name
    // args[2]: JMS message type
    // args[3]: JSON Test parameters containing 3 maps: [testValueMap, testHeadersMap, testPropertiesMap]
    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            System.out.println("JmsSenderShim: Incorrect number of arguments");
            System.out.println("JmsSenderShim: Expected arguments: broker_address, queue_name, JMS_msg_type, JSON_send_params");
            System.exit(1);
        }
        String brokerAddress = "amqp://" + args[0];
        String queueName = args[1];
        String jmsMessageType = args[2];
        if (!isSupportedJmsMessageType(jmsMessageType)) {
            System.err.println("ERROR: JmsSender: Unknown or unsupported JMS message type \"" + jmsMessageType + "\"");
            System.exit(1);
        }

        JsonReader jsonReader = Json.createReader(new StringReader(args[3]));
        JsonArray testParamsList = jsonReader.readArray();
        jsonReader.close();

        if (testParamsList.size() != 3) {
            System.err.println("ERROR: Incorrect number of JSON parameters: Expected 3, got " + Integer.toString(testParamsList.size()));
            System.err.println("  JSON parameters found: \"" + testParamsList + "\"");
            System.exit(1);
        }
        JsonObject testValuesMap = testParamsList.getJsonObject(0);
        JsonObject testHeadersMap = testParamsList.getJsonObject(1);
        JsonObject testPropertiesMap = testParamsList.getJsonObject(2);

        Sender shim = new Sender(brokerAddress, queueName);
        shim.runTests(jmsMessageType, testValuesMap, testHeadersMap, testPropertiesMap);
    }

    public Sender(String brokerAddress, String queueName) {
        try {
            ConnectionFactory factory = (ConnectionFactory)new JmsConnectionFactory(brokerAddress);

            _connection = factory.createConnection();
            _connection.setExceptionListener(new MyExceptionListener());
            _connection.start();

            _session = _connection.createSession(false, Session.AUTO_ACKNOWLEDGE);

            _queue = _session.createQueue(queueName);

            _messageProducer = _session.createProducer(_queue);
            
            _msgsSent = 0;
        } catch (Exception exp) {
            System.out.println("Caught exception, exiting.");
            exp.printStackTrace(System.out);
            System.exit(1);
        }
    }

    public void runTests(String jmsMessageType, JsonObject testValuesMap, JsonObject testHeadersMap, JsonObject testPropertiesMap) throws Exception {
        List<String> testValuesKeyList = new ArrayList<String>(testValuesMap.keySet());
        Collections.sort(testValuesKeyList);
        for (String key: testValuesKeyList) {
            JsonArray testValues = testValuesMap.getJsonArray(key);
            for (int i=0; i<testValues.size(); ++i) {
                String testValue = "";
                if (!testValues.isNull(i)) {
                    testValue = testValues.getJsonString(i).getString();
                }
                
                // Send message
                Message msg = createMessage(jmsMessageType, key, testValue, i);
                addMessageHeaders(msg, testHeadersMap);
                addMessageProperties(msg, testPropertiesMap);
                _messageProducer.send(msg, DeliveryMode.NON_PERSISTENT, Message.DEFAULT_PRIORITY, Message.DEFAULT_TIME_TO_LIVE);
                _msgsSent++;
            }
        }
        _connection.close();
    }
    
    protected Message createMessage(String jmsMessageType, String key, String testValue, int i) throws Exception {
        Message message = null;
        switch (jmsMessageType) {
        case "JMS_MESSAGE_TYPE":
            message = createJMSMessage(key, testValue);
            break;
        case "JMS_BYTESMESSAGE_TYPE":
            message = createJMSBytesMessage(key, testValue);
            break;
        case "JMS_MAPMESSAGE_TYPE":
            message = createJMSMapMessage(key, testValue, i);
            break;
        case "JMS_OBJECTMESSAGE_TYPE":
            message = createJMSObjectMessage(key, testValue);
            break;
        case "JMS_STREAMMESSAGE_TYPE":
            message = createJMSStreamMessage(key, testValue);
            break;
        case "JMS_TEXTMESSAGE_TYPE":
            message = createTextMessage(testValue);
            break;
        default:
            throw new Exception("Internal exception: Unexpected JMS message type \"" + jmsMessageType + "\"");
        }
        return message;
    }


    protected void addMessageHeaders(Message msg, JsonObject testHeadersMap) throws Exception, JMSException {
        List<String> testHeadersKeyList = new ArrayList<String>(testHeadersMap.keySet());
        for (String key: testHeadersKeyList) {
            JsonObject subMap = testHeadersMap.getJsonObject(key);
            List<String> subMapKeyList = new ArrayList<String>(subMap.keySet());
            String subMapKey = subMapKeyList.get(0); // There is always only one entry in map
            String subMapVal = subMap.getString(subMapKey);
            switch (key) {
            case "JMS_TYPE_HEADER":
                if (subMapKey.compareTo("string") == 0) {
                    msg.setJMSType(subMapVal);
                } else {
                    throw new Exception("Internal exception: Invalid message header type \"" + subMapKey + "\" for message header \"" + key + "\"");
                }
                break;
            case "JMS_CORRELATIONID_HEADER":
                if (subMapKey.compareTo("string") == 0) {
                    msg.setJMSCorrelationID(subMapVal);
                } else if (subMapKey.compareTo("bytes") == 0) {
                    msg.setJMSCorrelationIDAsBytes(Base64.getDecoder().decode(subMapVal.getBytes()));
                } else {
                    throw new Exception("Internal exception: Invalid message header type \"" + subMapKey + "\" for message header \"" + key + "\"");
                }
                break;
            case "JMS_REPLYTO_HEADER":
                switch (subMapKey) {
                case "queue":
                    msg.setJMSReplyTo(_session.createQueue(subMapVal));
                    break;
                case "temp_queue":
                    msg.setJMSReplyTo(_session.createTemporaryQueue());
                    break;
                case "topic":
                    msg.setJMSReplyTo(_session.createTopic(subMapVal));
                    break;
                case "temp_topic":
                    msg.setJMSReplyTo(_session.createTemporaryTopic());
                    break;
                default:
                    throw new Exception("Internal exception: Invalid message header type \"" + subMapKey + "\" for message header \"" + key + "\"");
                }
                break;
            default:
                throw new Exception("Internal exception: Unknown or unsupported message header \"" + key + "\"");
            }
        }
    }

    protected void addMessageProperties(Message msg, JsonObject testPropertiesMap) throws Exception, JMSException {
        List<String> testPropertiesKeyList = new ArrayList<String>(testPropertiesMap.keySet());
        for (String key: testPropertiesKeyList) {
            JsonObject subMap = testPropertiesMap.getJsonObject(key);
            List<String> subMapKeyList = new ArrayList<String>(subMap.keySet());
            String subMapKey = subMapKeyList.get(0); // There is always only one entry in map
            String subMapVal = subMap.getString(subMapKey);
            switch (subMapKey) {
            case "boolean":
                msg.setBooleanProperty(key, Boolean.parseBoolean(subMapVal));
                break;
            case "byte":
                msg.setByteProperty(key, Byte.decode(subMapVal));
                break;
            case "double":
                Long l1 = Long.parseLong(subMapVal.substring(2, 3), 16) << 60;
                Long l2 = Long.parseLong(subMapVal.substring(3), 16);
                msg.setDoubleProperty(key, Double.longBitsToDouble(l1 | l2));
                break;
            case "float":
                Long i = Long.parseLong(subMapVal.substring(2), 16);
                msg.setFloatProperty(key, Float.intBitsToFloat(i.intValue()));
                break;
            case "int":
                msg.setIntProperty(key, Integer.decode(subMapVal));
                break;
            case "long":
                msg.setLongProperty(key, Long.decode(subMapVal));
                break;
            case "short":
                msg.setShortProperty(key, Short.decode(subMapVal));
                break;
            case "string":
                msg.setStringProperty(key, subMapVal);
                break;
            default:
                throw new Exception("Internal exception: Unknown or unsupported message property type \"" + subMapKey + "\"");
            }
        }
    }

    protected Message createJMSMessage(String testValueType, String testValue) throws Exception, JMSException {
        if (testValueType.compareTo("none") != 0) {
            throw new Exception("Internal exception: Unexpected JMS message sub-type \"" + testValueType + "\"");
        }
        if (testValue.length() > 0) {
            throw new Exception("Internal exception: Unexpected JMS message value \"" + testValue + "\" for sub-type \"" + testValueType + "\"");
        }
        return _session.createMessage();
    }

    protected BytesMessage createJMSBytesMessage(String testValueType, String testValue) throws Exception, JMSException {
        BytesMessage message = _session.createBytesMessage();
        switch (testValueType) {
        case "boolean":
            message.writeBoolean(Boolean.parseBoolean(testValue));
            break;
        case "byte":
            message.writeByte(Byte.decode(testValue));
            break;
        case "bytes":
            message.writeBytes(Base64.getDecoder().decode(testValue));
            break;
        case "char":
            byte[] decodedValue = Base64.getDecoder().decode(testValue);
            if (decodedValue.length == 1) { // Char format: "X" or "\xNN"
                message.writeChar((char)decodedValue[0]);
            } else {
                throw new Exception("JmsSenderShim.createJMSBytesMessage() Malformed char string: \"" + decodedValue + "\" of length " + decodedValue.length);
            }
            break;
        case "double":
            Long l1 = Long.parseLong(testValue.substring(2, 3), 16) << 60;
            Long l2 = Long.parseLong(testValue.substring(3), 16);
            message.writeDouble(Double.longBitsToDouble(l1 | l2));
            break;
        case "float":
            Long i = Long.parseLong(testValue.substring(2), 16);
            message.writeFloat(Float.intBitsToFloat(i.intValue()));
            break;
        case "int":
            message.writeInt(Integer.decode(testValue));
            break;
        case "long":
            message.writeLong(Long.decode(testValue));
            break;
        case "object":
            Object obj = (Object)createObject(testValue);
            message.writeObject(obj);
            break;
        case "short":
            message.writeShort(Short.decode(testValue));
            break;
        case "string":
            message.writeUTF(testValue);
            break;
        default:
            throw new Exception("Internal exception: Unexpected JMS message sub-type \"" + testValueType + "\"");
        }
        return message;
    }
    
    protected MapMessage createJMSMapMessage(String testValueType, String testValue, int testValueNum) throws Exception, JMSException {
        MapMessage message = _session.createMapMessage();
        String name = String.format("%s%03d", testValueType, testValueNum);
        switch (testValueType) {
        case "boolean":
            message.setBoolean(name, Boolean.parseBoolean(testValue));
            break;
        case "byte":
            message.setByte(name, Byte.decode(testValue));
            break;
        case "bytes":
            message.setBytes(name, Base64.getDecoder().decode(testValue));
            break;
        case "char":
            byte[] decodedValue = Base64.getDecoder().decode(testValue);
            if (decodedValue.length == 1) { // Char format: "X" or "\xNN"
                message.setChar(name, (char)decodedValue[0]);
            } else if (decodedValue.length == 6) { // Char format: "\xNNNN"
                message.setChar(name, ByteBuffer.wrap(decodedValue).getChar());
            } else {
                throw new Exception("JmsSenderShim.createJMSMapMessage() Malformed char string: \"" + decodedValue + "\"");
            }
            break;
        case "double":
            Long l1 = Long.parseLong(testValue.substring(2, 3), 16) << 60;
            Long l2 = Long.parseLong(testValue.substring(3), 16);
            message.setDouble(name, Double.longBitsToDouble(l1 | l2));
            break;
        case "float":
            Long i = Long.parseLong(testValue.substring(2), 16);
            message.setFloat(name, Float.intBitsToFloat(i.intValue()));
            break;
        case "int":
            message.setInt(name, Integer.decode(testValue));
            break;
        case "long":
            message.setLong(name, Long.decode(testValue));
            break;
        case "object":
            Object obj = (Object)createObject(testValue);
            message.setObject(name, obj);
            break;
        case "short":
            message.setShort(name, Short.decode(testValue));
            break;
        case "string":
            message.setString(name, testValue);
            break;
        default:
            throw new Exception("Internal exception: Unexpected JMS message sub-type \"" + testValueType + "\"");
        }
        return message;
    }
    
    protected ObjectMessage createJMSObjectMessage(String className, String testValue) throws Exception, JMSException {
        Serializable obj = createJavaObject(className, testValue);
        if (obj == null) {
            // TODO: Handle error here
            System.out.println("JmsSenderShim.createJMSObjectMessage: obj == null");
            return null;
        }
        ObjectMessage message = _session.createObjectMessage();
        message.setObject(obj);
        return message;
    }
    
    protected StreamMessage createJMSStreamMessage(String testValueType, String testValue) throws Exception, JMSException {
        StreamMessage message = _session.createStreamMessage();
        switch (testValueType) {
        case "boolean":
            message.writeBoolean(Boolean.parseBoolean(testValue));
            break;
        case "byte":
            message.writeByte(Byte.decode(testValue));
            break;
        case "bytes":
            message.writeBytes(Base64.getDecoder().decode(testValue.getBytes()));
            break;
        case "char":
            byte[] decodedValue = Base64.getDecoder().decode(testValue);
            if (decodedValue.length == 1) { // Char format: "X"
                message.writeChar((char)decodedValue[0]);
            } else if (testValue.length() == 6) { // Char format: "\xNNNN"
                message.writeChar(ByteBuffer.wrap(decodedValue).getChar());
            } else {
                throw new Exception("JmsSenderShim.createJMSStreamMessage() Malformed char string: \"" + decodedValue + "\"");
            }
            break;
        case "double":
            Long l1 = Long.parseLong(testValue.substring(2, 3), 16) << 60;
            Long l2 = Long.parseLong(testValue.substring(3), 16);
            message.writeDouble(Double.longBitsToDouble(l1 | l2));
            break;
        case "float":
            Long i = Long.parseLong(testValue.substring(2), 16);
            message.writeFloat(Float.intBitsToFloat(i.intValue()));
            break;
        case "int":
            message.writeInt(Integer.decode(testValue));
            break;
        case "long":
            message.writeLong(Long.decode(testValue));
            break;
        case "object":
            Object obj = (Object)createObject(testValue);
            message.writeObject(obj);
            break;
        case "short":
            message.writeShort(Short.decode(testValue));
            break;
        case "string":
            message.writeString(testValue);
            break;
        default:
            throw new Exception("JmsSenderShim.createJMSStreamMessage(): Unexpected JMS message sub-type \"" + testValueType + "\"");
        }
        return message;
    }

    protected static Serializable createJavaObject(String className, String testValue) throws Exception {
        Serializable obj = null;
        try {
            Class<?> c = Class.forName(className);
            if (className.compareTo("java.lang.Character") == 0) {
                Constructor ctor = c.getConstructor(char.class);
                if (testValue.length() == 1) {
                    // Use first character of string
                    obj = (Serializable)ctor.newInstance(testValue.charAt(0));
                } else if (testValue.length() == 4 || testValue.length() == 6) {
                    // Format '\xNN' or '\xNNNN'
                    obj = (Serializable)ctor.newInstance((char)Integer.parseInt(testValue.substring(2), 16));
                } else {
                    throw new Exception("JmsSenderShim.createJavaObject(): Malformed char string: \"" + testValue + "\"");
                }
            } else {
                // Use string constructor
                Constructor ctor = c.getConstructor(String.class);
                obj = (Serializable)ctor.newInstance(testValue);
            }
        }
        catch (ClassNotFoundException e) {
            e.printStackTrace(System.out);
        }
        catch (NoSuchMethodException e) {
            e.printStackTrace(System.out);
        }
        catch (InstantiationException e) {
            e.printStackTrace(System.out);
        }
        catch (IllegalAccessException e) {
            e.printStackTrace(System.out);
        }
        catch (InvocationTargetException e) {
            e.printStackTrace(System.out);
        }
        return obj;
    }
    
    // value has format "classname:ctorstrvalue"
    protected static Serializable createObject(String value) throws Exception {
        Serializable obj = null;
        int colonIndex = value.indexOf(":");
        if (colonIndex >= 0) {
            String className = value.substring(0, colonIndex);
            String testValue = value.substring(colonIndex+1);
            obj = createJavaObject(className, testValue);
        } else {
            throw new Exception("createObject(): Malformed value string");
        }
        return obj;
    }
    
    protected TextMessage createTextMessage(String valueStr) throws JMSException {
        return _session.createTextMessage(valueStr);
    }
    
    protected static boolean isSupportedJmsMessageType(String jmsMessageType) {
        for (String supportedJmsMessageType: SUPPORTED_JMS_MESSAGE_TYPES) {
            if (jmsMessageType.equals(supportedJmsMessageType))
                return true;
        }
        return false;
    }

    private static class MyExceptionListener implements ExceptionListener {
        @Override
        public void onException(JMSException exception) {
            System.out.println("Connection ExceptionListener fired, exiting.");
            exception.printStackTrace(System.out);
            System.exit(1);
        }
    }
}