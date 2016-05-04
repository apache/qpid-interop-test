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
package org.apache.qpid.interop_test.shim;

import java.io.ByteArrayInputStream;
import java.io.ObjectInputStream;
import java.io.StringReader;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import javax.jms.BytesMessage;
import javax.jms.Connection;
import javax.jms.ConnectionFactory;
import javax.jms.ExceptionListener;
import javax.jms.JMSException;
import javax.jms.MapMessage;
import javax.jms.Message;
import javax.jms.MessageConsumer;
import javax.jms.ObjectMessage;
import javax.jms.Queue;
import javax.jms.Session;
import javax.jms.StreamMessage;
import javax.jms.TextMessage;
import javax.json.Json;
import javax.json.JsonArrayBuilder;
import javax.json.JsonObject;
import javax.json.JsonObjectBuilder;
import javax.json.JsonReader;
import javax.json.JsonWriter;
import org.apache.qpid.jms.JmsConnectionFactory;

public class JmsReceiverShim {
    private static final String USER = "guest";
    private static final String PASSWORD = "guest";
    private static final int TIMEOUT = 1000;
    private static final String[] SUPPORTED_JMS_MESSAGE_TYPES = {"JMS_BYTESMESSAGE_TYPE",
                                                                 "JMS_MAPMESSAGE_TYPE",
                                                                 "JMS_OBJECTMESSAGE_TYPE",
                                                                 "JMS_STREAMMESSAGE_TYPE",
                                                                 "JMS_TEXTMESSAGE_TYPE"};

    // args[0]: Broker URL
    // args[1]: Queue name
    // args[2]: JMS message type
    // args[3]: JSON Test number map
    public static void main(String[] args) throws Exception {
        if (args.length < 4) {
            System.out.println("JmsReceiverShim: Insufficient number of arguments");
            System.out.println("JmsReceiverShim: Expected arguments: broker_address, queue_name, amqp_type, num_test_values");
            System.exit(1);
        }
        String brokerAddress = "amqp://" + args[0];
        String queueName = args[1];
        String jmsMessageType = args[2];
        if (!isSupportedJmsMessageType(jmsMessageType)) {
            System.out.println("ERROR: JmsReceiverShim: unknown or unsupported JMS message type \"" + jmsMessageType + "\"");
            System.exit(1);
        }

        JsonReader jsonReader = Json.createReader(new StringReader(args[3]));
        JsonObject numTestValuesMap = jsonReader.readObject();
        jsonReader.close();

        Connection connection = null;

        try {
            ConnectionFactory factory = (ConnectionFactory)new JmsConnectionFactory(brokerAddress);

            connection = factory.createConnection(USER, PASSWORD);
            connection.setExceptionListener(new MyExceptionListener());
            connection.start();

            Session session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);

            Queue queue = session.createQueue(queueName);

            MessageConsumer messageConsumer = session.createConsumer(queue);
            
            List<String> keyList = new ArrayList<String>(numTestValuesMap.keySet());
            Collections.sort(keyList);

            Message message = null;
            JsonObjectBuilder job = Json.createObjectBuilder();
            for (String key: keyList) {
                JsonArrayBuilder jab = Json.createArrayBuilder();
                for (int i=0; i<numTestValuesMap.getJsonNumber(key).intValue(); ++i) {
                    message = messageConsumer.receive(TIMEOUT);
                    if (message == null) break;
                    switch (jmsMessageType) {
                    case "JMS_BYTESMESSAGE_TYPE":
                        switch (key) {
                        case "boolean":
                            jab.add(((BytesMessage)message).readBoolean()?"True":"False");
                            break;
                        case "byte":
                            jab.add(formatByte(((BytesMessage)message).readByte()));
                            break;
                        case "bytes":
                            {
                                byte[] bytesBuff = new byte[65536];
                                int numBytesRead = ((BytesMessage)message).readBytes(bytesBuff);
                                if (numBytesRead >= 0) {
                                    jab.add(new String(Arrays.copyOfRange(bytesBuff, 0, numBytesRead)));
                                } else {
                                    // NOTE: For this case, an empty byte array has nothing to return
                                    jab.add(new String());
                                }
                            }
                            break;
                        case "char":
                            jab.add(formatChar(((BytesMessage)message).readChar()));
                            break;
                        case "double":
                            long l = Double.doubleToRawLongBits(((BytesMessage)message).readDouble());
                            jab.add(String.format("0x%16s", Long.toHexString(l)).replace(' ', '0'));
                            break;
                        case "float":
                            int i0 = Float.floatToRawIntBits(((BytesMessage)message).readFloat());
                            jab.add(String.format("0x%8s", Integer.toHexString(i0)).replace(' ', '0'));
                            break;
                        case "int":
                            jab.add(formatInt(((BytesMessage)message).readInt()));
                            break;
                        case "long":
                            jab.add(formatLong(((BytesMessage)message).readLong()));
                            break;
                        case "object":
                            {
                                byte[] bytesBuff = new byte[65536];
                                int numBytesRead = ((BytesMessage)message).readBytes(bytesBuff);
                                if (numBytesRead >= 0) {
                                    ByteArrayInputStream bais = new ByteArrayInputStream(Arrays.copyOfRange(bytesBuff, 0, numBytesRead));
                                    ObjectInputStream ois = new ObjectInputStream(bais);
                                    Object obj = ois.readObject();
                                    jab.add(obj.getClass().getName() + ":" + obj.toString());
                                } else {
                                    jab.add("<object error>");
                                }
                            }
                            break;
                        case "short":
                            jab.add(formatShort(((BytesMessage)message).readShort()));
                            break;
                        case "string":
                            jab.add(((BytesMessage)message).readUTF());
                            break;
                        default:
                            throw new Exception("JmsReceiverShim: Unknown subtype for " + jmsMessageType + ": \"" + key + "\"");
                        }
                        break;
                    case "JMS_STREAMMESSAGE_TYPE":
                        switch (key) {
                        case "boolean":
                            jab.add(((StreamMessage)message).readBoolean()?"True":"False");
                            break;
                        case "byte":
                            jab.add(formatByte(((StreamMessage)message).readByte()));
                            break;
                        case "bytes":
                            byte[] bytesBuff = new byte[65536];
                            int numBytesRead = ((StreamMessage)message).readBytes(bytesBuff);
                            if (numBytesRead >= 0) {
                                jab.add(new String(Arrays.copyOfRange(bytesBuff, 0, numBytesRead)));
                            } else {
                                System.out.println("StreamMessage.readBytes() returned " + numBytesRead);
                                jab.add("<bytes error>");
                            }
                            break;
                        case "char":
                            jab.add(formatChar(((StreamMessage)message).readChar()));
                            break;
                        case "double":
                            long l = Double.doubleToRawLongBits(((StreamMessage)message).readDouble());
                            jab.add(String.format("0x%16s", Long.toHexString(l)).replace(' ', '0'));
                            break;
                        case "float":
                            int i0 = Float.floatToRawIntBits(((StreamMessage)message).readFloat());
                            jab.add(String.format("0x%8s", Integer.toHexString(i0)).replace(' ', '0'));
                            break;
                        case "int":
                            jab.add(formatInt(((StreamMessage)message).readInt()));
                            break;
                        case "long":
                            jab.add(formatLong(((StreamMessage)message).readLong()));
                            break;
                        case "object":
                            Object obj = ((StreamMessage)message).readObject();
                            jab.add(obj.getClass().getName() + ":" + obj.toString());
                            break;
                        case "short":
                            jab.add(formatShort(((StreamMessage)message).readShort()));
                            break;
                        case "string":
                            jab.add(((StreamMessage)message).readString());
                            break;
                        default:
                            throw new Exception("JmsReceiverShim: Unknown subtype for " + jmsMessageType + ": \"" + key + "\"");
                        }
                        break;
                    case "JMS_MAPMESSAGE_TYPE":
                        String name = String.format("%s%03d", key, i);
                        switch (key) {
                        case "boolean":
                            jab.add(((MapMessage)message).getBoolean(name)?"True":"False");
                            break;
                        case "byte":
                            jab.add(formatByte(((MapMessage)message).getByte(name)));
                            break;
                        case "bytes":
                            jab.add(new String(((MapMessage)message).getBytes(name)));
                            break;
                        case "char":
                            jab.add(formatChar(((MapMessage)message).getChar(name)));
                            break;
                        case "double":
                            long l = Double.doubleToRawLongBits(((MapMessage)message).getDouble(name));
                            jab.add(String.format("0x%16s", Long.toHexString(l)).replace(' ', '0'));
                            break;
                        case "float":
                            int i0 = Float.floatToRawIntBits(((MapMessage)message).getFloat(name));
                            jab.add(String.format("0x%8s", Integer.toHexString(i0)).replace(' ', '0'));
                            break;
                        case "int":
                            jab.add(formatInt(((MapMessage)message).getInt(name)));
                            break;
                        case "long":
                            jab.add(formatLong(((MapMessage)message).getLong(name)));
                            break;
                        case "object":
                            Object obj = ((MapMessage)message).getObject(name);
                            jab.add(obj.getClass().getName() + ":" + obj.toString());
                            break;
                        case "short":
                            jab.add(formatShort(((MapMessage)message).getShort(name)));
                            break;
                        case "string":
                            jab.add(((MapMessage)message).getString(name));
                            break;
                        default:
                            throw new Exception("JmsReceiverShim: Unknown subtype for " + jmsMessageType + ": \"" + key + "\"");
                        }
                        break;
                    case "JMS_OBJECTMESSAGE_TYPE":
                        jab.add(((ObjectMessage)message).getObject().toString());
                        break;
                    case "JMS_TEXTMESSAGE_TYPE":
                        jab.add(((TextMessage)message).getText());
                        break;
                    default:
                        connection.close();
                        throw new Exception("JmsReceiverShim: Internal error: unknown or unsupported JMS message type \"" + jmsMessageType + "\"");
                    }
                }
                job.add(key, jab);
            }
            connection.close();

            System.out.println(jmsMessageType);
            StringWriter out = new StringWriter();
            JsonWriter jsonWriter = Json.createWriter(out);
            jsonWriter.writeObject(job.build());
            jsonWriter.close();
            System.out.println(out.toString());
        } catch (Exception exp) {
            if (connection != null)
                connection.close();
            System.out.println("Caught exception, exiting.");
            exp.printStackTrace(System.out);
            System.exit(1);
        }
    }
    
    protected static String formatByte(byte b) {
        boolean neg = false;
        if (b < 0) {
            neg = true;
            b = (byte)-b;
        }
        return String.format("%s0x%x", neg?"-":"", b);
    }
    
    protected static String formatChar(char c) {
        if (Character.isLetterOrDigit(c)) {
            return String.format("%c", c);
        }
        char[] ca = {c};
        return new String(ca);
    }
    
    protected static String formatInt(int i) {
        boolean neg = false;
        if (i < 0) {
            neg = true;
            i = -i;
        }
        return String.format("%s0x%x", neg?"-":"", i);
    }
    
    protected static String formatLong(long l) {
        boolean neg = false;
        if (l < 0) {
            neg = true;
            l = -l;
        }
        return String.format("%s0x%x", neg?"-":"", l);
    }
    
    protected static String formatShort(int s) {
        boolean neg = false;
        if (s < 0) {
            neg = true;
            s = -s;
        }
        return String.format("%s0x%x", neg?"-":"", s);
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