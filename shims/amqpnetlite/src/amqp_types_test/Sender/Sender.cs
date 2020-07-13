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
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using Amqp;
using Amqp.Framing;
using Amqp.Types;
using Newtonsoft.Json;

namespace Qpidit
{
    /// <summary>
    /// MessageValue holds a QpidIT type name and a json object created from the
    /// CLI string argument, encodes it, and returns the object to be used as the
    /// constructor for a message to be sent.
    /// Complex values List and Map are constructed recursively.
    /// Remaining singleton values like int or long are held directly as objects.
    /// </summary>
    class MessageValue
    {
        // Original type and json object
        private string baseType;
        private object baseValue;

        // has Encode been called?
        private Boolean encoded;

        // Simple objects completely encoded
        // List and Map defined recursively
        private object valueDirect;
        
        /// <summary>
        /// Constructor
        /// </summary>
        /// <param name="type">qpidit type name</param>
        /// <param name="value">json encoded object</param>
        public MessageValue(string type, object value)
        {
            baseType = type;
            baseValue = value;
            encoded = false;
            valueDirect = null;
        }


        /// <summary>
        /// Create a MessageValue without knowing beforehand what
        /// type of system object is being handled.
        /// * Objects created in the list from the command line have a
        ///   known type and are created via the constructor.
        /// * Objects created inside List and Map have only string
        ///   type externally but need an actual type to be figured out.
        /// </summary>
        /// <param name="obj"></param>
        /// <returns></returns>
        public static MessageValue CreateAutoType(object obj)
        {
            return new Qpidit.MessageValue(QpiditTypeOf(obj), obj);
        }


        /// <summary>
        /// Return the native object that represents the encoded
        /// Amqp value.
        /// </summary>
        /// <returns></returns>
        public Object ToObject()
        {
            if (!encoded)
                Encode();

            return valueDirect;
        }


        /// <summary>
        /// Return the Amqp Message that holds this value.
        /// </summary>
        /// <returns></returns>
        public Message ToMessage()
        {
            return new Message(this.ToObject());
        }


        /// <summary>
        /// Get an object's QPIDIT type
        /// </summary>
        /// <param name="obj">a .NET object</param>
        /// <returns>QpidIT type name</returns>
        public static string QpiditTypeOf(object obj)
        {
            string typename = obj.GetType().Name;
            string qpiditType = null;
            if (obj == null)
            {
                qpiditType = "null";
            }
            else
            {
                switch (typename)
                {
                    case "Boolean":
                        qpiditType = "boolean";
                        break;
                    case "Byte":
                        qpiditType = "ubyte";
                        break;
                    case "UInt16":
                        qpiditType = "ushort";
                        break;
                    case "UInt32":
                        qpiditType = "uint";
                        break;
                    case "UInt64":
                        qpiditType = "ulong";
                        break;
                    case "SByte":
                        qpiditType = "byte";
                        break;
                    case "Int16":
                        qpiditType = "short";
                        break;
                    case "Int32":
                        qpiditType = "int";
                        break;
                    case "Int64":
                        qpiditType = "long";
                        break;
                    case "Single":
                        qpiditType = "float";
                        break;
                    case "Double":
                        qpiditType = "double";
                        break;
                    case "DateTime":
                        qpiditType = "timestamp";
                        break;
                    case "Guid":
                        qpiditType = "uuid";
                        break;
                    case "Byte[]":
                        qpiditType = "binary";
                        break;
                    case "String":
                        qpiditType = "string";
                        break;
                    case "Symbol":
                        qpiditType = "symbol";
                        break;
                    case "Array":
                    case "ArrayList":
                    case "Dictionary":
                    case "Dictionary`2":
                         throw new ApplicationException(String.Format(
                            "Unsupported complex AMQP type {0}", typename));
                    default:
                        throw new ApplicationException(String.Format(
                            "Can not translate system type {0} to a QpidIT type", typename));
                }
            }
            return qpiditType;
        }


        public string StripLeading0x(string value)
        {
            if (!value.StartsWith("0x"))
                throw new ApplicationException(String.Format(
                    "EncodeUInt string does not start with '0x' : {0}", value));
            return value.Substring(2);
        }

        public UInt64 EncodeUInt(string value)
        {
            UInt64 result = 0;
            value = StripLeading0x(value);
            result = UInt64.Parse(value, System.Globalization.NumberStyles.HexNumber);
            return result;
        }


        public Int64 EncodeInt(string value)
        {
            Int64 result = 0;
            bool isNegated = value.StartsWith("-");
            if (isNegated)
                value = value.Substring(1);
            value = StripLeading0x(value);
            result = Int64.Parse(value, System.Globalization.NumberStyles.HexNumber);
            if (isNegated)
                result = -result;
            return result;
        }


        /// <summary>
        /// Generate the object used to create a message
        /// </summary>
        public void Encode()
        {
            if (baseValue is Array)
            {
                // List
                if (! String.Equals(baseType, "list", StringComparison.OrdinalIgnoreCase))
                {
                    throw new ApplicationException(String.Format(
                        "Sender asked to encode a {0} but received a list: {1}", baseType, baseValue.ToString()));
                }
                valueDirect = new Amqp.Types.List();
                foreach (object item in (Array)baseValue)
                {
                    MessageValue itemValue = MessageValue.CreateAutoType(item);
                    itemValue.Encode();
                    ((Amqp.Types.List)valueDirect).Add(itemValue.ToObject());
                }
            }
            if (baseValue is ArrayList)
            {
                // List
                if (! String.Equals(baseType, "list", StringComparison.OrdinalIgnoreCase))
                {
                    throw new ApplicationException(String.Format(
                        "Sender asked to encode a {0} but received a list: {1}", baseType, baseValue.ToString()));
                }
                valueDirect = new Amqp.Types.List();
                foreach (object item in (ArrayList)baseValue)
                {
                    MessageValue itemValue = MessageValue.CreateAutoType(item);
                    itemValue.Encode();
                    ((Amqp.Types.List)valueDirect).Add(itemValue.ToObject());
                }
            }
            else if (baseValue is Dictionary<string, object>)
            {
                // Map
                if (!String.Equals(baseType, "map", StringComparison.OrdinalIgnoreCase))
                {
                    throw new ApplicationException(String.Format(
                        "Sender asked to encode a {0} but received a map: {1}", baseType, baseValue.ToString()));
                }
                valueDirect = new Amqp.Types.Map();
                Dictionary<string, object> myDict = new Dictionary<string, object>();
                myDict = (Dictionary<string, object>)baseValue;
                foreach (var key in myDict.Keys)
                {
                    MessageValue itemValue = MessageValue.CreateAutoType(myDict[key]);
                    ((Amqp.Types.Map)valueDirect)[key] = itemValue.ToObject();
                }
            }
            else if (baseValue is String)
            {
                string value;
                UInt64 valueUInt64;
                Int64 valueInt64;

                switch (baseType)
                {
                    case "null":
                        valueDirect = null;
                        break;
                    case "boolean":
                        value = (string)baseValue;
                        bool mybool = String.Equals(value, "true", StringComparison.OrdinalIgnoreCase);
                        valueDirect = mybool;
                        break;
                    case "ubyte":
                        value = (string)baseValue;
                        valueUInt64 = EncodeUInt(value);
                        Byte mybyte = (Byte)(valueUInt64 & 0xff);
                        valueDirect = mybyte;
                        break;
                    case "ushort":
                        value = (string)baseValue;
                        valueUInt64 = EncodeUInt(value);
                        UInt16 myuint16 = (UInt16)(valueUInt64 & 0xffff);
                        valueDirect = myuint16;
                        break;
                    case "uint":
                        value = (string)baseValue;
                        valueUInt64 = EncodeUInt(value);
                        UInt32 myuint32 = (UInt32)(valueUInt64 & 0xffffffff);
                        valueDirect = myuint32;
                        break;
                    case "ulong":
                        value = (string)baseValue;
                        valueUInt64 = EncodeUInt(value);
                        valueDirect = valueUInt64;
                        break;
                    case "byte":
                        value = (string)baseValue;
                        valueInt64 = EncodeInt(value);
                        SByte mysbyte = (SByte)(valueInt64 & 0xff);
                        valueDirect = mysbyte;
                        break;
                    case "short":
                        value = (string)baseValue;
                        valueInt64 = EncodeInt(value);
                        Int16 myint16 = (Int16)(valueInt64 & 0xffff);
                        valueDirect = myint16;
                        break;
                    case "int":
                        value = (string)baseValue;
                        valueInt64 = EncodeInt(value);
                        Int32 myint32 = (Int32)(valueInt64 & 0xffffffff);
                        valueDirect = myint32;
                        break;
                    case "long":
                        value = (string)baseValue;
                        valueInt64 = EncodeInt(value);
                        valueDirect = valueInt64;
                        break;
                    case "float":
                        value = StripLeading0x((string)baseValue);
                        UInt32 num32 = UInt32.Parse(value, System.Globalization.NumberStyles.AllowHexSpecifier);
                        byte[] floatVals = BitConverter.GetBytes(num32);
                        float flt = BitConverter.ToSingle(floatVals, 0);
                        valueDirect = flt;
                        break;
                    case "double":
                        value = StripLeading0x((string)baseValue);
                        UInt64 num64 = UInt64.Parse(value, System.Globalization.NumberStyles.AllowHexSpecifier);
                        byte[] doubleVals = BitConverter.GetBytes(num64);
                        double dbl = BitConverter.ToDouble(doubleVals, 0);
                        valueDirect = dbl;
                        break;
                    case "timestamp":
                        // epochTicks is the number of 100uSec ticks between 01/01/0001
                        // and 01/01/1970. Used to adjust between DateTime and unix epoch.
                        const long epochTicks = 621355968000000000;
                        value = StripLeading0x((string)baseValue);
                        Int64 dtticks = Int64.Parse(value, System.Globalization.NumberStyles.AllowHexSpecifier);
                        dtticks *= TimeSpan.TicksPerMillisecond;
                        dtticks += epochTicks;
                        DateTime dt = new DateTime(dtticks, DateTimeKind.Utc);
                        valueDirect = dt;
                        break;
                    case "uuid":
                        value = (string)baseValue;
                        Guid guid = new Guid(value);
                        valueDirect = guid;
                        break;
                    case "binary":
                        // TODO: fix this
                        value = (string)baseValue;
                        byte[] binval = Convert.FromBase64String(value);
                        valueDirect = binval;
                        break;
                    case "string":
                        valueDirect = (string)baseValue;
                        break;
                    case "symbol":
                        Symbol sym = new Symbol((string)baseValue);
                        valueDirect = sym;
                        break;
                    case "list":
                        throw new ApplicationException(String.Format(
                            "Sender asked to encode a list but received a string: {0}", baseValue));
                    case "map":
                        throw new ApplicationException(String.Format(
                            "Sender asked to encode a map but received a string: {0}", baseValue));
                    case "decimal32":
                    case "decimal64":
                    case "decimal128":
                        throw new ApplicationException(String.Format(
                            "AMQP.Net Lite does not support AMQP decimal type: {0}", baseType));
                    default:
                        throw new ApplicationException(String.Format(
                            "Sender can not encode base type: {0}", baseType));
                }
            }
            else
            {
                throw new ApplicationException(String.Format(
                    "Sender can not encode object type {0}", baseValue.GetType().Name));
            }
            encoded = true;
        }
    }

    class Sender
    {
        private string brokerUrl;
        private string queueName;
        private string amqpType;
        private string jsonMessages;

        public Sender(string brokerUrl_, string queueName_, string amqpType_, string jsonMessages_)
        {
            brokerUrl = brokerUrl_;
            queueName = queueName_;
            amqpType = amqpType_;
            jsonMessages = jsonMessages_;
        }

        ~Sender()
        { }


        public void run()
        {
            List<Message> messagesToSend = new List<Message>();

            // Deserialize the json message list
            var itMsgs = JsonConvert.DeserializeObject<dynamic>(jsonMessages);
            //if (!(itMsgs is Array))
            //    throw new ApplicationException(String.Format(
            //        "Messages are not formatted as a json list: {0}, but as type: {1}", jsonMessages, itMsgs.GetType().Name));

            // Generate messages
            foreach (object itMsg in itMsgs)
            {
                MessageValue mv = new MessageValue(amqpType, itMsg.ToString());
                mv.Encode();
                messagesToSend.Add(mv.ToMessage());
            }

            // Send the messages
            ManualResetEvent senderAttached = new ManualResetEvent(false);
            OnAttached onSenderAttached = (l, a) => { senderAttached.Set(); };
            Address address = new Address(string.Format("amqp://{0}", brokerUrl));
            Connection connection = new Connection(address);
            Session session = new Session(connection);
            SenderLink sender = new SenderLink(session,
                                               "Lite-amqp-types-test-sender",
                                               new Target() { Address = queueName },
                                               onSenderAttached);
            if (senderAttached.WaitOne(10000))
            {
                foreach (Message message in messagesToSend)
                {
                    sender.Send(message);
                }
            }
            else
            {
                throw new ApplicationException(string.Format(
                    "Time out attaching to test broker {0} queue {1}", brokerUrl, queueName));
            }

            sender.Close();
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
             *       3: AMQP type
             *       4: Test value(s) as JSON string
             */
            int exitCode = 0;
            try
            {
                if (args.Length != 4)
                {
                    throw new ApplicationException(
                        "program requires four arguments: brokerAddr queueName amqpType jsonValuesToSend");
                }
                //Trace.TraceLevel = TraceLevel.Frame | TraceLevel.Verbose;
                //Trace.TraceListener = (f, a) => Console.WriteLine(DateTime.Now.ToString("[hh:mm:ss.fff]") + " " + string.Format(f, a));

                Sender sender = new Qpidit.Sender(args[0], args[1], args[2], args[3]);
                sender.run();
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
