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

import java.io.Serializable;
import java.io.StringReader;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.util.ArrayList;
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

public class JmsSenderShim {
    private static final String USER = "guest";
    private static final String PASSWORD = "guest";
    private static final String[] SUPPORTED_JMS_MESSAGE_TYPES = {"JMS_BYTESMESSAGE_TYPE",
    	                                                         "JMS_MAPMESSAGE_TYPE",
    	                                                         "JMS_OBJECTMESSAGE_TYPE",
    	                                                         "JMS_STREAMMESSAGE_TYPE",
    	                                                         "JMS_TEXTMESSAGE_TYPE"};

    // args[0]: Broker URL
    // args[1]: Queue name
    // args[2]: JMS message type
    // args[3]: JSON Test value map
    public static void main(String[] args) throws Exception {
    	if (args.length < 4) {
    		System.out.println("JmsSenderShim: Insufficient number of arguments");
    		System.out.println("JmsSenderShim: Expected arguments: broker_address, queue_name, amqp_type, test_val, test_val, ...");
    		System.exit(1);
    	}
    	String brokerAddress = "amqp://" + args[0];
    	String queueName = args[1];
    	String jmsMessageType = args[2];
    	if (!isSupportedJmsMessageType(jmsMessageType)) {
        	System.out.println("ERROR: JmsReceiver: unknown or unsupported JMS message type \"" + jmsMessageType + "\"");
        	System.exit(1);    		
    	}
    	
    	JsonReader jsonReader = Json.createReader(new StringReader(args[3]));
    	JsonObject testValuesMap = jsonReader.readObject();
    	jsonReader.close();
    	
        try {
        	ConnectionFactory factory = (ConnectionFactory)new JmsConnectionFactory(brokerAddress);

            Connection connection = factory.createConnection();
            connection.setExceptionListener(new MyExceptionListener());
            connection.start();

            Session session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
            
            Queue queue = session.createQueue(queueName);

            MessageProducer messageProducer = session.createProducer(queue);

        	Message message = null;
   			List<String> keyList = new ArrayList<String>(testValuesMap.keySet());
   			Collections.sort(keyList);
   			for (String key: keyList) {
   				JsonArray testValues = testValuesMap.getJsonArray(key);
   				for (int i=0; i<testValues.size(); ++i) {
   					String testValue = testValues.getJsonString(i).getString();
   	           		switch (jmsMessageType) {
   	           		case "JMS_BYTESMESSAGE_TYPE":
   	           			message = createBytesMessage(session, key, testValue);
   	           			break;
   	           		case "JMS_MAPMESSAGE_TYPE":
   	           			message = createMapMessage(session, key, testValue, i);
   	           			break;
   	           		case "JMS_OBJECTMESSAGE_TYPE":
   	           			message = createObjectMessage(session, key, testValue);
   	           			break;
   	           		case "JMS_STREAMMESSAGE_TYPE":
   	           			message = createStreamMessage(session, key, testValue);
   	           			break;
   	           		case "JMS_TEXTMESSAGE_TYPE":
   	           			message = createTextMessage(session, testValue);
   	           			break;
   					default:
   						throw new Exception("Internal exception: Unexpected JMS message type \"" + jmsMessageType + "\"");
   	           		}
   	           		messageProducer.send(message, DeliveryMode.NON_PERSISTENT, Message.DEFAULT_PRIORITY, Message.DEFAULT_TIME_TO_LIVE);
   				}
   			}
            
            connection.close();
        } catch (Exception exp) {
            System.out.println("Caught exception, exiting.");
            exp.printStackTrace(System.out);
            System.exit(1);
        }
    }

    protected static BytesMessage createBytesMessage(Session session, String testValueType, String testValue) throws Exception, JMSException {
		BytesMessage message = session.createBytesMessage();
		switch (testValueType) {
		case "boolean":
			message.writeBoolean(Boolean.parseBoolean(testValue));
			break;
		case "byte":
			message.writeByte(Byte.decode(testValue));
			break;
		case "bytes":
			message.writeBytes(testValue.getBytes());
			break;
		case "char":
			if (testValue.length() == 1) { // Char format: "X" or "\xNN"
				message.writeChar(testValue.charAt(0));
			} else {
				throw new Exception("JmsSenderShim.createBytesMessage() Malformed char string: \"" + testValue + "\" of length " + testValue.length());
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
    
    protected static MapMessage createMapMessage(Session session, String testValueType, String testValue, int testValueNum) throws Exception, JMSException {
    	MapMessage message = session.createMapMessage();
    	String name = String.format("%s%03d", testValueType, testValueNum);
		switch (testValueType) {
		case "boolean":
			message.setBoolean(name, Boolean.parseBoolean(testValue));
			break;
		case "byte":
			message.setByte(name, Byte.decode(testValue));
			break;
		case "bytes":
			message.setBytes(name, testValue.getBytes());
			break;
		case "char":
			if (testValue.length() == 1) { // Char format: "X"
				message.setChar(name, testValue.charAt(0));
			} else if (testValue.length() == 6) { // Char format: "\xNNNN"
				message.setChar(name, (char)Integer.parseInt(testValue.substring(2), 16));
			} else {
				throw new Exception("JmsSenderShim.createMapMessage() Malformed char string: \"" + testValue + "\"");
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
    
    protected static ObjectMessage createObjectMessage(Session session, String className, String testValue) throws Exception, JMSException {
    	Serializable obj = createJavaObject(className, testValue);
    	if (obj == null) {
    		// TODO: Handle error here
    		System.out.println("createObjectMessage: obj == null");
    		return null;
    	}
		ObjectMessage message = session.createObjectMessage();
		message.setObject(obj);
		return message;
    }
    
    protected static StreamMessage createStreamMessage(Session session, String testValueType, String testValue) throws Exception, JMSException {
    	StreamMessage message = session.createStreamMessage();
		switch (testValueType) {
		case "boolean":
			message.writeBoolean(Boolean.parseBoolean(testValue));
			break;
		case "byte":
			message.writeByte(Byte.decode(testValue));
			break;
		case "bytes":
			message.writeBytes(testValue.getBytes());
			break;
		case "char":
			if (testValue.length() == 1) { // Char format: "X"
				message.writeChar(testValue.charAt(0));
			} else if (testValue.length() == 6) { // Char format: "\xNNNN"
				message.writeChar((char)Integer.parseInt(testValue.substring(2), 16));
			} else {
				throw new Exception("JmsSenderShim.createStreamMessage() Malformed char string: \"" + testValue + "\"");
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
			throw new Exception("Internal exception: Unexpected JMS message sub-type \"" + testValueType + "\"");
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
	    			throw new Exception("JmsSenderShim.createStreamMessage() Malformed char string: \"" + testValue + "\"");
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
    
    protected static TextMessage createTextMessage(Session session, String valueStr) throws JMSException {
    	return session.createTextMessage(valueStr);
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