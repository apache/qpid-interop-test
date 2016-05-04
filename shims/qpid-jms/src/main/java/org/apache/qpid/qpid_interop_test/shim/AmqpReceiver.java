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

import java.math.BigDecimal;
import java.util.UUID;
import java.util.Vector;
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
import javax.naming.Context;
import javax.naming.InitialContext;
import org.apache.qpid.jms.JmsConnectionFactory;

public class AmqpReceiver {
    private static final String USER = "guest";
    private static final String PASSWORD = "guest";
    private static final int TIMEOUT = 1000;
    private static final String[] SUPPORTED_AMQP_TYPES = {"null",
													      "boolean",
													      "ubyte",
													      "ushort",
													      "uint",
													      "ulong",
													      "byte",
													      "short",
													      "int",
													      "long",
													      "float",
													      "double",
													      "decimal32",
													      "decimal64",
													      "decimal128",
													      "char",
													      "timestamp",
													      "uuid",
													      "binary",
													      "string",
													      "symbol",
													      "list",
													      "map",
													      "array"};

    public static void main(String[] args) throws Exception {
    	if (args.length < 4) {
    		System.out.println("AmqpReceiver: Insufficient number of arguments");
    		System.out.println("AmqpReceiver: Expected arguments: broker_address, queue_name, amqp_type, num_test_values");
    		System.exit(1);
    	}
    	String brokerAddress = "amqp://" + args[0];
    	String queueName = args[1];
    	String amqpType = args[2];
    	int numTestValues = Integer.parseInt(args[3]);
    	Connection connection = null;

        try {
        	ConnectionFactory factory = (ConnectionFactory)new JmsConnectionFactory(brokerAddress);

            connection = factory.createConnection(USER, PASSWORD);
            connection.setExceptionListener(new MyExceptionListener());
            connection.start();

            Session session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
            
            Queue queue = session.createQueue(queueName);

            MessageConsumer messageConsumer = session.createConsumer(queue);
            
            Vector<String> outList = new Vector<String>();
            outList.add(amqpType);
            if (isSupportedAmqpType(amqpType)) {
                int actualCount = 0;
                Message message = null;
                for (int i = 1; i <= numTestValues; i++, actualCount++) {
        			message = messageConsumer.receive(TIMEOUT);
        			if (message == null)
        				break;
            		switch (amqpType) {
            		case "null":
            			long bodyLength = ((BytesMessage)message).getBodyLength();
            			if (bodyLength == 0L) {
            				outList.add("None");
            			} else {
            				throw new Exception("AmqpReceiver: JMS BytesMessage size error: Expected 0 bytes, read " + bodyLength);
            			}
            			break;
            		case "boolean":
            			String bs = String.valueOf(((BytesMessage)message).readBoolean());
            			outList.add(Character.toUpperCase(bs.charAt(0)) + bs.substring(1));
            			break;
            		case "ubyte":
            			byte byteValue = ((BytesMessage)message).readByte();
            			short ubyteValue = (short)(byteValue & 0xff);
            			outList.add(String.valueOf(ubyteValue));
            			break;
            		case "ushort":
            		{
            			byte[] byteArray = new byte[2];
            			int numBytes = ((BytesMessage)message).readBytes(byteArray);
            			if (numBytes != 2) {
            				// TODO: numBytes == -1 means no more bytes in stream - add error message for this case?
            				throw new Exception("AmqpReceiver: JMS BytesMessage size error: Exptected 2 bytes, read " + numBytes);
            			}
            			int ushortValue = 0;
            			for (int j=0; j<byteArray.length; j++) {
            				ushortValue = (ushortValue << 8) + (byteArray[j] & 0xff);
            			}
            			outList.add(String.valueOf(ushortValue));
            			break;
            		}
            		case "uint":
            		{
            			byte[] byteArray = new byte[4];
            			int numBytes = ((BytesMessage)message).readBytes(byteArray);
            			if (numBytes != 4) {
            				// TODO: numBytes == -1 means no more bytes in stream - add error message for this case?
            				throw new Exception("AmqpReceiver: JMS BytesMessage size error: Exptected 4 bytes, read " + numBytes);
            			}
            			long uintValue = 0;
            			for (int j=0; j<byteArray.length; j++) {
            				uintValue = (uintValue << 8) + (byteArray[j] & 0xff);
            			}
            			outList.add(String.valueOf(uintValue));
            			break;
            		}
            		case "ulong":
            		case "timestamp":
            		{
            			// TODO: Tidy this ugliness up - perhaps use of vector<byte>?
            			byte[] byteArray = new byte[8];
            			int numBytes = ((BytesMessage)message).readBytes(byteArray);
            			if (numBytes != 8) {
            				// TODO: numBytes == -1 means no more bytes in stream - add error message for this case?
            				throw new Exception("AmqpReceiver: JMS BytesMessage size error: Exptected 8 bytes, read " + numBytes);
            			}
            			// TODO: shortcut in use here - this byte array should go through a Java type that can represent this as a number - such as BigInteger.
            			outList.add(String.format("0x%02x%02x%02x%02x%02x%02x%02x%02x", byteArray[0], byteArray[1],
            					byteArray[2], byteArray[3], byteArray[4], byteArray[5], byteArray[6], byteArray[7]));
            			break;
            		}
            		case "byte":
            			outList.add(String.valueOf(((BytesMessage)message).readByte()));
            			break;
            		case "short":
            			outList.add(String.valueOf(((BytesMessage)message).readShort()));
            			break;
            		case "int":
            			outList.add(String.valueOf(((BytesMessage)message).readInt()));
            			break;
            		case "long":
            			outList.add(String.valueOf(((BytesMessage)message).readLong()));
            			break;
            		case "float":
            			float f = ((BytesMessage)message).readFloat();
            			int i0 = Float.floatToRawIntBits(f);
            			outList.add(String.format("0x%8s", Integer.toHexString(i0)).replace(' ', '0'));
            			break;
            		case "double":
            			double d = ((BytesMessage)message).readDouble();
            			long l = Double.doubleToRawLongBits(d);
            			outList.add(String.format("0x%16s", Long.toHexString(l)).replace(' ', '0'));
            			break;
            		case "decimal32":
            			BigDecimal bd32 = (BigDecimal)((ObjectMessage)message).getObject();
            			outList.add(bd32.toString());
            			break;
            		case "decimal64":
            			BigDecimal bd64 = (BigDecimal)((ObjectMessage)message).getObject();
            			outList.add(bd64.toString());
            			break;
            		case "decimal128":
            			BigDecimal bd128 = (BigDecimal)((ObjectMessage)message).getObject();
            			outList.add(bd128.toString());
            			break;
            		case "char":
            			outList.add(String.format("%c", ((BytesMessage)message).readChar()));
            			break;
            		case "uuid":
            			UUID uuid = (UUID)((ObjectMessage)message).getObject();
            			outList.add(uuid.toString());
            			break;
            		case "binary":
            			BytesMessage bm = (BytesMessage)message;
            			int msgLen = (int)bm.getBodyLength();
            			byte[] ba = new byte[msgLen];
            			if (bm.readBytes(ba) == msgLen) {
            				outList.add(new String(ba));
            			} else {
            				// TODO: Raise exception or error here: size mismatch
            			}
            			break;
            		case "string":
            			outList.add(((TextMessage)message).getText());
            			break;
            		case "symbol":
            			outList.add(((BytesMessage)message).readUTF());
            			break;
            		case "list":
            			break;
            		case "map":
            			break;
            		case "array":
            			break;
            		default:
            			// Internal error, should never happen if SUPPORTED_AMQP_TYPES matches this case stmt
            			connection.close();
            			throw new Exception("AmqpReceiver: Internal error: unsupported AMQP type \"" + amqpType + "\"");
            		}
                }
            } else {
            	System.out.println("ERROR: AmqpReceiver: AMQP type \"" + amqpType + "\" is not supported");
            	connection.close();
            	System.exit(1);
            }

            connection.close();

            // No exception, print results
            for (int i=0; i<outList.size(); i++) {
            	System.out.println(outList.get(i));
            }
        } catch (Exception exp) {
        	if (connection != null)
        		connection.close();
            System.out.println("Caught exception, exiting.");
            exp.printStackTrace(System.out);
            System.exit(1);
        }
    }
    
    protected static boolean isSupportedAmqpType(String amqpType) {
    	for (String supportedAmqpType: SUPPORTED_AMQP_TYPES) {
    		if (amqpType.equals(supportedAmqpType))
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