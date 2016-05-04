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
import java.math.BigInteger; 
import java.math.MathContext; 
import java.util.Arrays;
import java.util.UUID;
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
import javax.naming.Context;
import javax.naming.InitialContext;
import org.apache.qpid.jms.JmsConnectionFactory;

public class AmqpSender {
    private static final String USER = "guest";
    private static final String PASSWORD = "guest";
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
            System.out.println("AmqpSender: Insufficient number of arguments");
            System.out.println("AmqpSender: Expected arguments: broker_address, queue_name, amqp_type, test_val, test_val, ...");
            System.exit(1);
        }
        String brokerAddress = "amqp://" + args[0];
        String queueName = args[1];
        String amqpType = args[2];
        String[] testValueList = Arrays.copyOfRange(args, 3, args.length); // Use remaining args as test values

        try {
            ConnectionFactory factory = (ConnectionFactory)new JmsConnectionFactory(brokerAddress);

            Connection connection = factory.createConnection();
            connection.setExceptionListener(new MyExceptionListener());
            connection.start();

            Session session = connection.createSession(false, Session.AUTO_ACKNOWLEDGE);
            
            Queue queue = session.createQueue(queueName);

            MessageProducer messageProducer = session.createProducer(queue);

            if (isSupportedAmqpType(amqpType)) {
                Message message = null;
                for (String testValueStr : testValueList) {
                    switch (amqpType) {
                    case "null":
                        message = session.createBytesMessage();
                        break;
                    case "boolean":
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeBoolean(Boolean.parseBoolean(testValueStr));
                        break;
                    case "ubyte":
                    {
                        byte testValue = (byte)Short.parseShort(testValueStr);
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeByte(testValue);
                        break;
                    }
                    case "ushort":
                    {
                        int testValue = Integer.parseInt(testValueStr);
                        byte[] byteArray = new byte[2];
                        byteArray[0] = (byte)(testValue >> 8);
                        byteArray[1] = (byte)(testValue);
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeBytes(byteArray);
                        break;
                    }
                    case "uint":
                    {
                        long testValue = Long.parseLong(testValueStr);
                        byte[] byteArray = new byte[4];
                        byteArray[0] = (byte)(testValue >> 24);
                        byteArray[1] = (byte)(testValue >> 16);
                        byteArray[2] = (byte)(testValue >> 8);
                        byteArray[3] = (byte)(testValue);
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeBytes(byteArray);
                        break;
                    }
                    case "ulong":
                    {
                        // TODO: Tidy this ugliness up - perhaps use of vector<byte>?
                        BigInteger testValue = new BigInteger(testValueStr);
                        byte[] bigIntArray =  testValue.toByteArray(); // may be 1 to 9 bytes depending on number
                        byte[] byteArray = {0, 0, 0, 0, 0, 0, 0, 0};
                        int effectiveBigIntArrayLen = bigIntArray.length > 8 ? 8 : bigIntArray.length; // Cap length at 8
                        int bigIntArrayOffs = bigIntArray.length > 8 ? bigIntArray.length - 8 : 0; // Offset when length > 8
                        for (int i=0; i<bigIntArray.length && i < 8; i++)
                            byteArray[8 - effectiveBigIntArrayLen + i] = bigIntArray[bigIntArrayOffs + i];
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeBytes(byteArray);
                        break;
                    }
                    case "byte":
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeByte(Byte.parseByte(testValueStr));
                        break;
                    case "short":
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeShort(Short.parseShort(testValueStr));
                        break;
                    case "int":
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeInt(Integer.parseInt(testValueStr));
                        break;
                    case "long":
                    case "timestamp":
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeLong(Long.parseLong(testValueStr));
                        break;
                    case "float":
                        Long i = Long.parseLong(testValueStr.substring(2), 16);
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeFloat(Float.intBitsToFloat(i.intValue()));
                        break;
                    case "double":
                        Long l1 = Long.parseLong(testValueStr.substring(2, 3), 16) << 60;
                        Long l2 = Long.parseLong(testValueStr.substring(3), 16);
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeDouble(Double.longBitsToDouble(l1 | l2));
                        break;
                    case "decimal32":
                        BigDecimal bd32 = new BigDecimal(testValueStr, MathContext.DECIMAL32);
                        message = session.createObjectMessage();
                        ((ObjectMessage)message).setObject(bd32);
                        break;
                    case "decimal64":
                        BigDecimal bd64 = new BigDecimal(testValueStr, MathContext.DECIMAL64);
                        message = session.createObjectMessage();
                        ((ObjectMessage)message).setObject(bd64);
                        break;
                    case "decimal128":
                        BigDecimal bd128 = new BigDecimal(testValueStr, MathContext.DECIMAL128);
                        message = session.createObjectMessage();
                        ((ObjectMessage)message).setObject(bd128);
                        break;
                    case "char":
                        char c = 0;
                        if (testValueStr.length() == 1) // Single char
                            c = testValueStr.charAt(0);
                        else if (testValueStr.length() == 6) // unicode format
                            c = (char)Integer.parseInt(testValueStr, 16);
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeChar(c);
                        break;
                    case "uuid":
                        UUID uuid = UUID.fromString(testValueStr);
                        message = session.createObjectMessage();
                        ((ObjectMessage)message).setObject(uuid);
                        break;
                    case "binary":
                        message = session.createBytesMessage();
                        byte[] byteArray = testValueStr.getBytes();
                        ((BytesMessage)message).writeBytes(byteArray, 0, byteArray.length);
                        break;
                    case "string":
                        message = session.createTextMessage(testValueStr);
                        break;
                    case "symbol":
                        message = session.createBytesMessage();
                        ((BytesMessage)message).writeUTF(testValueStr);
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
                        throw new Exception("AmqpSender: Internal error: unsupported AMQP type \"" + amqpType + "\"");
                    }
                    messageProducer.send(message, DeliveryMode.NON_PERSISTENT, Message.DEFAULT_PRIORITY, Message.DEFAULT_TIME_TO_LIVE);
                }
            } else {
                System.out.println("ERROR: AmqpSender: AMQP type \"" + amqpType + "\" is not supported");
                connection.close();
                System.exit(1);
            }
            
            connection.close();
        } catch (Exception exp) {
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