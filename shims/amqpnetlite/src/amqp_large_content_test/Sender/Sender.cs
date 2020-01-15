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
using System.Linq;
using System.Text;
using System.Threading;
using Amqp;
using Amqp.Framing;
using Amqp.Types;
using Newtonsoft.Json;

// Large_content_test is driven by a list like this:
//
//  TYPE_MAP = {
//    # List of sizes in Mb
//    'binary': [1, 10, 100],
//    'string': [1, 10, 100],
//    'symbol': [1, 10, 100],
//    # Tuple of two elements: (tot size of list/map in MB, List of no elements in list)
//    # The num elements lists are powers of 2 so that they divide evenly into the size in MB (1024 * 1024 bytes)
//    'list': [[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]], [100, [1, 16, 256, 4096]]],
//    'map': [[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]], [100, [1, 16, 256, 4096]]],
//    #'array': [[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]], [100, [1, 16, 256, 4096]]]
//    }
//
// Sender receives command line args from this map:
//     Sender host queuename binary '[1, 10, 100]'
//     Sender host queuename list '[[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]], [100, [1, 16, 256, 4096]]]'
//
// Sender 
//   1) generates actual .NET objects as specified
//   2) uses the AMQP Lite client to generate messages holding the object
//   3) sends the message(s) to the host/queuename.
//
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
                        qpiditType = "list";
                        break;
                    case "ArrayList":
                        qpiditType = "list";
                        break;
                    case "Dictionary":
                        qpiditType = "map";
                        break;
                    case "Dictionary`2":
                        qpiditType = "map";
                        break;
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
            if (encoded)
                return;

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
            else if (baseValue is ArrayList)
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
                        byte[] binval = Encoding.ASCII.GetBytes(value);
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


    /// <summary>
    /// Classes to parse JSON size arg for map and list types
    /// </summary>
    class MbBlock
    {
        public Int32 mBytes { get; set; }
        public List<Int32> nChunks { get; set; }
    }
    class MbSpec
    {
        public List<MbBlock> MbBlocks { get; set; }

        enum ParseState
        {
            START,
            NEW_MBBLOCK,
            M_BYTES,
            NEW_NCHUNKS,
            NCHUNK,
            END_NCHUNK,
            END_MBBLOCK,
            END
        }

        public MbSpec(string sizeSpec)
        {
            MbBlock curMbBlock = new MbBlock();
            Int32 curInt = 0; ;

            ParseState ps = ParseState.START;

            int pos = -1;
            foreach (char ch in sizeSpec)
            {
                pos += 1;
                //Console.WriteLine("ch = '{0}', position = {1}", ch, pos);
                string err  = "";
                switch (ps)
                {
                    case ParseState.START:
                        if (ch == '[')
                        {
                            MbBlocks = new List<MbBlock>();
                            ps = ParseState.NEW_MBBLOCK;
                        }
                        else
                            err = "no leading '['";
                        break;
                    case ParseState.NEW_MBBLOCK:
                        if (ch == ']')
                        {
                            MbBlocks.Add(curMbBlock);
                            ps = ParseState.END;
                        }
                        else if (ch == '[')
                        {
                            curMbBlock = new MbBlock();
                            ps = ParseState.M_BYTES;
                            curInt = 0;
                        }
                        else if (Char.IsWhiteSpace(ch))
                        {
                            // ignore whitespace
                        }
                        else
                            err = "NEW_MBBLOCK expects '[' or ']'";
                        break;
                    case ParseState.M_BYTES:
                        if (Char.IsDigit(ch))
                        {
                            curInt *= 10;
                            curInt += (int)(ch - '0');
                        }
                        else if (ch == ',')
                        {
                            curMbBlock.mBytes = curInt;
                            curInt = 0;
                            ps = ParseState.NEW_NCHUNKS;
                        }
                        else if (Char.IsWhiteSpace(ch))
                        {
                            // ignore whitespace
                        }
                        else
                            err = "M_BYTES expects digit or ','";
                        break;
                    case ParseState.NEW_NCHUNKS:
                        if (ch == '[')
                        {
                            curMbBlock.nChunks = new List<Int32>();
                            ps = ParseState.NCHUNK;
                        }
                        else if (Char.IsWhiteSpace(ch))
                        {
                            // ignore whitespace
                        }
                        else
                            err = "NEW_NCHUNKS expects digit or '['";
                        break;
                    case ParseState.NCHUNK:
                        if (Char.IsDigit(ch))
                        {
                            curInt *= 10;
                            curInt += (int)(ch - '0');
                        }
                        else if (ch == ',')
                        {
                            curMbBlock.nChunks.Add(curInt);
                            curInt = 0;
                        }
                        else if (Char.IsWhiteSpace(ch))
                        {
                            // ignore whitespace
                        }
                        else if (ch == ']')
                        {
                            curMbBlock.nChunks.Add(curInt);
                            curInt = 0;
                            ps = ParseState.END_NCHUNK;
                        }
                        else
                            err = "NCHUNK expects digit, ',', or ']'";
                        break;
                    case ParseState.END_NCHUNK:
                        if (Char.IsWhiteSpace(ch))
                        {
                            // ignore whitespace
                        }
                        else if (ch == ']')
                        {
                            MbBlocks.Add(curMbBlock);
                            curMbBlock = new MbBlock();
                            ps = ParseState.END_MBBLOCK;
                        }
                        else
                            err = "END_MBBLOCK expects ']'";
                        break;
                    case ParseState.END_MBBLOCK:
                        if (Char.IsWhiteSpace(ch))
                        {
                            // ignore whitespace
                        }
                        else if (ch == ',')
                        {
                            ps = ParseState.NEW_MBBLOCK;
                        }
                        else if (ch == ']')
                        {
                            ps = ParseState.END;
                        }
                        else
                            err = "END_MBBLOCK expects ',', ']', or '['";
                        break;
                    case ParseState.END:
                        err = "illegal characters after JSON end of object";
                        break;
                }

                if (err != "")
                {
                    throw new ApplicationException(String.Format("Size spec parse error at position {0}, state {1}: {2}", pos, ps, err));
                }
            }
        }
    }



    class Sender
    {
        private string brokerUrl;
        private string queueName;
        private string amqpType;
        private string countSpec;
        private Int32 mbFactor;
        private MbSpec mbSpec;

        public Sender(string brokerUrl_, string queueName_, string amqpType_, string countSpec_, Int32 mbFactor_)
        {
            brokerUrl = brokerUrl_;
            queueName = queueName_;
            amqpType = amqpType_;
            countSpec = countSpec_;
            mbFactor = mbFactor_;
        }

        ~Sender()
        { }


        public IEnumerable<Message> AllMessages()
        {
            if (String.Equals(amqpType, "binary", StringComparison.OrdinalIgnoreCase) ||
                String.Equals(amqpType, "string", StringComparison.OrdinalIgnoreCase) ||
                String.Equals(amqpType, "symbol", StringComparison.OrdinalIgnoreCase))
            {
                // Deserialize the count spec list
                var itMsgs = JsonConvert.DeserializeObject<dynamic>(countSpec);
                //if (!(itMsgs is Array))
                //    throw new ApplicationException(String.Format(
                //        "Messages are not formatted as a json list: {0}, but as type: {1}", countSpec, itMsgs.GetType().Name));

                // Generate messages
                if (String.Equals(amqpType, "binary", StringComparison.OrdinalIgnoreCase))
                {
                    foreach (Int32 mbSize in itMsgs)
                    {
                        string binStr = new string(Convert.ToChar(0), mbSize * mbFactor);
                        MessageValue mv = new MessageValue(amqpType, binStr);
                        yield return mv.ToMessage();
                    }
                }
                else if (String.Equals(amqpType, "string", StringComparison.OrdinalIgnoreCase))
                {
                    foreach (Int32 mbSize in itMsgs)
                    {
                        string binStr = new string('s', mbSize * mbFactor);
                        MessageValue mv = new MessageValue(amqpType, binStr);
                        yield return mv.ToMessage();
                    }
                }
                else if (String.Equals(amqpType, "symbol", StringComparison.OrdinalIgnoreCase))
                {
                    foreach (Int32 mbSize in itMsgs)
                    {
                        string binStr = new string('b', mbSize * mbFactor);
                        MessageValue mv = new MessageValue(amqpType, binStr);
                        yield return mv.ToMessage();
                    }
                }
            }
            else if (String.Equals(amqpType, "list", StringComparison.OrdinalIgnoreCase))
            {
                mbSpec = new MbSpec(countSpec);
                foreach (MbBlock mbBlock in mbSpec.MbBlocks)
                {
                    foreach (Int32 eCount in mbBlock.nChunks)
                    {
                        Int32 sizePerEltBytes = (mbBlock.mBytes * mbFactor) / eCount;
                        string[] testList = new string[eCount];
                        for (int i = 0; i < eCount; i++)
                        {
                            testList[i] = new string('L', sizePerEltBytes);
                        }
                        MessageValue mv = new MessageValue(amqpType, testList);
                        yield return mv.ToMessage();
                    }
                }
            }
            else if (String.Equals(amqpType, "map", StringComparison.OrdinalIgnoreCase))
            {
                mbSpec = new MbSpec(countSpec);
                foreach (MbBlock mbBlock in mbSpec.MbBlocks)
                {
                    foreach (Int32 eCount in mbBlock.nChunks)
                    {
                        Int32 sizePerEltBytes = (mbBlock.mBytes * mbFactor) / eCount;
                        Dictionary<string, object> testMap = new Dictionary<string, object>();
                        for (int i = 0; i < eCount; i++)
                        {
                            testMap[i.ToString("000000")] = new string('M', sizePerEltBytes);
                        }
                        MessageValue mv = new MessageValue(amqpType, testMap);
                        yield return mv.ToMessage();
                    }
                }
            }
            // else if (String.Equals(amqpType, "array", StringComparison.OrdinalIgnoreCase))
            //{ /* TODO */ }
            else
            {
                throw new ApplicationException(String.Format(
                    "unsupported amqp type: {0}", amqpType));
            }
        }

        public void run()
        {
            // Send the messages
            ManualResetEvent senderAttached = new ManualResetEvent(false);
            OnAttached onSenderAttached = (l, a) => { senderAttached.Set(); };
            Address address = new Address(string.Format("amqp://{0}", brokerUrl));
            Connection connection = new Connection(address);
            Session session = new Session(connection);
            SenderLink sender = new SenderLink(session,
                                               "Lite-amqp-large-content-test-sender",
                                               new Target() { Address = queueName },
                                               onSenderAttached);
            if (senderAttached.WaitOne(10000))
            {
                foreach (Message message in AllMessages())
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
            const Int32 mbFactor = 1024 * 1024; // command line specifies small(ish) numbers of megabytes. Adjust size of a megabyte here.
            try
            {
                if (args.Length != 4)
                {
                    throw new ApplicationException(
                        "program requires four arguments: brokerAddr queueName amqpType jsonValuesToSend");
                }
                //Trace.TraceLevel = TraceLevel.Frame | TraceLevel.Verbose;
                //Trace.TraceListener = (f, a) => Console.WriteLine(DateTime.Now.ToString("[hh:mm:ss.fff]") + " " + string.Format(f, a));

                Sender sender = new Qpidit.Sender(args[0], args[1], args[2], args[3], mbFactor);
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
