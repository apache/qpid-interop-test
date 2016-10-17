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
package org.apache.qpid.interop_test.jms_large_content_test;

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
    // ...
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.out.println("JmsSenderShim: Incorrect number of arguments");
            System.out.println("JmsSenderShim: Expected arguments: broker_address, queue_name, ...");
            System.exit(1);
        }
        String brokerAddress = "amqp://" + args[0];
        String queueName = args[1];

        Sender shim = new Sender(brokerAddress, queueName);
        shim.runTests();
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

    public void runTests() throws Exception {
        _connection.close();
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