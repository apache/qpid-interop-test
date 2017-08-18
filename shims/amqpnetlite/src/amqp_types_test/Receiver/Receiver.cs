/*
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */

using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using Amqp;
using Amqp.Framing;
using Amqp.Types;
using System.Web.Script.Serialization;
//using Newtonsoft.Json;

namespace Qpidit
{

    /// <summary>
    /// MessageValue holds a typed AMQP.Net Lite message body AmqpValue,
    /// decodes it, and returns the QpidIT string that represents the message.
    /// Complex values List and Map are constructed recursively.
    /// Remaining singleton values like int or long are held directly as strings.
    /// </summary>
    class MessageValue
    {
        // Original message body object
        private object messageValue;

        // Computed object type names
        private string liteType;
        private string qpiditType;

        // Singleton decoded value in QpidIt format
        private string valueString;

        // Storage for List
        private List<MessageValue> valueList;

        // Storage for Map
        // Kept as lists to avoid dictionary reordering complications.
        private List<MessageValue> valueMapKeys;
        private List<MessageValue> valueMapValues;

        /// <summary>
        /// Constructor.
        /// User must call Decode to parse values.
        /// </summary>
        /// <param name="messageValue">Lite AmqpValue</param>
        public MessageValue(object messageValue)
        {
            this.messageValue = messageValue;
            liteType = "";
            qpiditType = "";
            valueString = null;
            valueList = null;
            valueMapKeys = null;
            valueMapValues = null;
        }

        /// <summary>
        /// Lite type name property
        /// </summary>
        public string LiteTypeName { get { return liteType; } }

        /// <summary>
        /// QpidIt type name property
        /// </summary>
        public string QpiditTypeName { get { return qpiditType; } }

        /// <summary>
        /// Decode the value and contained sub-values.
        /// </summary>
        /// <returns></returns>
        public override string ToString()
        {
            if (valueString != null)
            {
                return "\"" + valueString + "\"";
            }
            else if (valueList != null)
            {
                StringBuilder sb = new StringBuilder();
                bool leading = false;
                sb.Append("[");
                foreach (var item in valueList)
                {
                    if (leading) sb.Append(", ");
                    leading = true;
                    sb.Append(item.ToString());
                }
                sb.Append("]");
                return sb.ToString();
            }
            else if (valueMapKeys != null)
            {
                StringBuilder msb = new StringBuilder();
                msb.Append("{");
                for (int i = 0; i < valueMapKeys.Count; i++)
                {
                    if (i > 0) msb.Append(", ");
                    msb.Append(valueMapKeys[i].ToString());
                    msb.Append(":");
                    msb.Append(valueMapValues[i].ToString());
                }
                msb.Append("}");
                return msb.ToString();
            }
            else
            {
                throw new ApplicationException("printing undecoded MessageValue");
            }
        }

        /// <summary>
        /// Compute contents of byte array in reverse order.
        /// </summary>
        /// <param name="input">The byte array.</param>
        /// <param name="suppressLeading0s">Flag controls suppression of leading zeros.</param>
        /// <returns>Hexadecimal string</returns>
        public string BytesReversedToString(byte[] input, bool suppressLeading0s = false)
        {
            if (!BitConverter.IsLittleEndian)
            {
                throw new ApplicationException("This code requires a little endian host.");
            }
            string result = "";
            for (int i = input.Length - 1; i >= 0; i--)
            {
                result += String.Format("{0:x2}", input[i]);
            }
            if (suppressLeading0s)
            {
                result = result.TrimStart('0');
            }
            if (String.IsNullOrEmpty(result))
            {
                result = "0";
            }
            return result;
        }


        /// <summary>
        /// Json-encode an array of bytes assumed to be plain ascii text.
        /// </summary>
        /// <param name="theBytes">The byte array.</param>
        /// <returns>Serialized string</returns>
        public string SerializeBytes(byte[] theBytes)
        {
            StringBuilder builder = new StringBuilder();
            byte asciiSlash = Encoding.Default.GetBytes("\\")[0];
            byte asciiDoubleQuote = Encoding.Default.GetBytes("\"")[0];
            foreach (byte b in theBytes)
            {
                if (b == asciiSlash) {
                    // backslash needs backslash escape
                    builder.Append((char)asciiSlash);
                    builder.Append((char)asciiSlash);
                }
                else if (b == asciiDoubleQuote) {
                    // doublequote needs backslash escape
                    builder.Append((char)asciiSlash);
                    builder.Append((char)asciiDoubleQuote);
                }
                else if (b >= 32 && b <= 127)
                    // printable ascii passed through
                    builder.Append((char)b);
                else
                    // non-printable ascii as escaped hex bytes
                    builder.Append(String.Format("\\x{0:x2}", b));
            }
            return builder.ToString();
        }


        /// <summary>
        /// Json-encode an object whose string value is assumed to be plain ascii text.
        /// </summary>
        /// <param name="theObject">The object.</param>
        /// <returns>Serialized string</returns>
        public string SerializeString(object theObject)
        {
            byte[] bytes = Encoding.ASCII.GetBytes(theObject.ToString());
            return SerializeBytes(bytes);
        }


        /// <summary>
        /// Decode message body's object type names and QpidIt display details.
        /// Recursively process maps and lists.
        /// </summary>
        public void Decode()
        {
            if (messageValue == null)
            {
                liteType = "null";
                qpiditType = "null";
                valueString = "None";
                return;
            }

            liteType = messageValue.GetType().Name;
            if (liteType == "List")
            {
                qpiditType = "list";
                valueList = new List<MessageValue>();
                List list = (List)messageValue;
                foreach (var item in list)
                {
                    MessageValue itemValue = new Qpidit.MessageValue(item);
                    itemValue.Decode();
                    valueList.Add(itemValue);
                }
            }
            else if (liteType == "Map")
            {
                qpiditType = "map";
                valueMapKeys = new List<MessageValue>();
                valueMapValues = new List<MessageValue>();
                Map map = (Map)messageValue;
                foreach (var key in map.Keys)
                {
                    MessageValue valueKey = new Qpidit.MessageValue(key);
                    valueKey.Decode();
                    MessageValue valueValue = new Qpidit.MessageValue(map[key]);
                    valueValue.Decode();
                    valueMapKeys.Add(valueKey);
                    valueMapValues.Add(valueValue);
                }
            }
            else
            {
                //Console.WriteLine("MessageValue singleton type : {0}", liteType);
                switch (liteType)
                {
                    case "Boolean":
                        qpiditType = "boolean";
                        valueString = (Boolean)messageValue ? "True" : "False";
                        break;
                    case "Byte":
                        qpiditType = "ubyte";
                        valueString = String.Format("0x{0:x}", (Byte)messageValue);
                        break;
                    case "UInt16":
                        qpiditType = "ushort";
                        valueString = String.Format("0x{0:x}", (UInt16)messageValue);
                        break;
                    case "UInt32":
                        qpiditType = "uint";
                        valueString = String.Format("0x{0:x}", (UInt32)messageValue);
                        break;
                    case "UInt64":
                        qpiditType = "ulong";
                        valueString = String.Format("0x{0:x}", (UInt64)messageValue);
                        break;
                    case "SByte":
                        qpiditType = "byte";
                        SByte mySbyte = (SByte)messageValue;
                        if (mySbyte >= 0)
                        {
                            valueString = String.Format("0x{0:x}", mySbyte);
                        }
                        else
                        {
                            mySbyte = (SByte) (-mySbyte);
                            valueString = String.Format("-0x{0:x}", mySbyte);
                        }
                        break;
                    case "Int16":
                        qpiditType = "short";
                        Int16 myInt16 = (Int16)messageValue;
                        if (myInt16 >= 0)
                        {
                            valueString = String.Format("0x{0:x}", myInt16);
                        }
                        else
                        {
                            myInt16 = (Int16)(-myInt16);
                            valueString = String.Format("-0x{0:x}", myInt16);
                        }
                        break;
                    case "Int32":
                        qpiditType = "int";
                        Int32 myInt32 = (Int32)messageValue;
                        if (myInt32 >= 0)
                        {
                            valueString = String.Format("0x{0:x}", myInt32);
                        }
                        else
                        {
                            myInt32 = (Int32)(-myInt32);
                            valueString = String.Format("-0x{0:x}", myInt32);
                        }
                        break;
                    case "Int64":
                        qpiditType = "long";
                        Int64 myInt64 = (Int64)messageValue;
                        if (myInt64 >= 0)
                        {
                            valueString = String.Format("0x{0:x}", myInt64);
                        }
                        else
                        {
                            myInt64 = (Int64)(-myInt64);
                            valueString = String.Format("-0x{0:x}", myInt64);
                        }
                        break;
                    case "Single":
                        byte[] sbytes = BitConverter.GetBytes((Single)messageValue);
                        qpiditType = "float";
                        valueString = "0x" + BytesReversedToString(sbytes);
                        break;
                    case "Double":
                        byte[] dbytes = BitConverter.GetBytes((Double)messageValue);
                        qpiditType = "double";
                        valueString = "0x" + BytesReversedToString(dbytes);
                        break;
                    case "DateTime":
                        // epochTicks is the number of 100uSec ticks between 01/01/0001
                        // and 01/01/1970. Used to adjust between DateTime and unix epoch.
                        const long epochTicks = 621355968000000000;
                        byte[] dtbytes = BitConverter.GetBytes(
                            (((DateTime)messageValue).Ticks - epochTicks) / TimeSpan.TicksPerMillisecond);
                        qpiditType = "timestamp";
                        valueString = "0x" + BytesReversedToString(dtbytes, true);
                        break;
                    case "Guid":
                        qpiditType = "uuid";
                        valueString = messageValue.ToString();
                        break;
                    case "Byte[]":
                        qpiditType = "binary";
                        byte[] binstr = (byte[])messageValue;
                        valueString = SerializeBytes(binstr);
                        break;
                    case "String":
                        qpiditType = "string";
                        valueString = SerializeString(messageValue);
                        break;
                    case "Symbol":
                        qpiditType = "symbol";
                        valueString = SerializeString(messageValue);
                        break;
                    default:
                        qpiditType = "unknown";
                        valueString = String.Format("Unknown AMQP type: {0}", liteType);
                        throw new ApplicationException(valueString);
                }
            }
        }
    }

    /// <summary>
    /// Receive and categorize some number of messages.
    /// </summary>
    class Receiver
    {
        private string brokerUrl;
        private string queueName;
        private string amqpType;
        private Int32 nExpected;
        private Int32 nReceived;
        private List<MessageValue> receivedMessageValues;

        public Receiver(string brokerUrl_, string queueName_, string amqpType_, Int32 expected_)
        {
            brokerUrl = brokerUrl_;
            queueName = queueName_;
            amqpType = amqpType_;
            nExpected = expected_;
            nReceived = 0;
            receivedMessageValues = new List<MessageValue>();
        }

        ~Receiver()
        { }

        public string ReceivedValueList
        {
            get
            {
                StringBuilder sb = new StringBuilder();
                sb.Append("[");
                for (int i = 0; i < receivedMessageValues.Count; i++)
                {
                    if (i > 0) sb.Append(", ");
                    sb.Append(receivedMessageValues[i].ToString());
                }
                sb.Append("]");
                return sb.ToString();
            }
        }


        public void run()
        {
            ManualResetEvent receiverAttached = new ManualResetEvent(false);
            OnAttached onReceiverAttached = (l, a) => { receiverAttached.Set(); };
            Address address = new Address(string.Format("amqp://{0}", brokerUrl));
            Connection connection = new Connection(address);
            Session session = new Session(connection);
            ReceiverLink receiverlink = new ReceiverLink(session,
                                                         "Lite-amqp-types-test-receiver",
                                                         new Source() { Address = queueName },
                                                         onReceiverAttached);
            if (receiverAttached.WaitOne(10000))
            {
                while (nReceived < nExpected)
                {
                    Message message = receiverlink.Receive(10000);
                    if (message != null)
                    {
                        nReceived += 1;
                        receiverlink.Accept(message);
                        MessageValue mv = new MessageValue(message.Body);
                        mv.Decode();

                        if (mv.QpiditTypeName != amqpType)
                        {
                            throw new ApplicationException(string.Format
                                ("Incorrect AMQP type found in message body: expected: {0}; found: {1}",
                                amqpType, mv.QpiditTypeName));
                        }
                        //Console.WriteLine("{0} [{1}]", mv.QpiditTypeName, mv.ToString());
                        receivedMessageValues.Add(mv);
                    }
                    else
                    {
                        throw new ApplicationException(string.Format(
                            "Time out receiving message {0} of {1}", nReceived+1, nExpected));
                    }
                }
            }
            else
            {
                throw new ApplicationException(string.Format(
                    "Time out attaching to test broker {0} queue {1}", brokerUrl, queueName));
            }

            receiverlink.Close();
            session.Close();
            connection.Close();
        }
    }

    class MainProgram
    {
        static int Main(string[] args)
        {
            /*
             * --- main ---
             * Args: 1: Broker address (ip-addr:port)
             *       2: Queue name
             *       3: QPIDIT AMQP type name of expected message body values
             *       4: Expected number of test values to receive
             */
            int exitCode = 0;
            try
            {
                if (args.Length != 4)
                {
                    throw new ApplicationException(
                        "program requires four arguments: brokerAddr queueName amqpType nValues");
                }
                //Trace.TraceLevel = TraceLevel.Frame | TraceLevel.Verbose;
                //Trace.TraceListener = (f, a) => Console.WriteLine(DateTime.Now.ToString("[hh:mm:ss.fff]") + " " + string.Format(f, a));

                Receiver receiver = new Qpidit.Receiver(
                    args[0], args[1], args[2], Int32.Parse(args[3]));
                receiver.run();

                Console.WriteLine(args[2]);
                Console.WriteLine("{0}", receiver.ReceivedValueList);
            }
            catch (Exception e)
            {
                string firstline = new StringReader(e.ToString()).ReadLine();
                Console.Error.WriteLine("AmqpSender error: {0}.", firstline);
                exitCode = 1;
            }

            return exitCode;
        }
    }
}
