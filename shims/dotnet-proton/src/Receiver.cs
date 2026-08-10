/*
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
 */

/*
 * QIT .NET Apache Qpid Proton Shim - Receiver
 */

using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Apache.Qpid.Proton.Buffer;
using Apache.Qpid.Proton.Client;
using Apache.Qpid.Proton.Types;
using Apache.Qpid.Proton.Types.Messaging;
using Newtonsoft.Json;

namespace Qit.Shim
{
    public static class Receiver
    {
        public static void Receive(string broker, string queue, int count, int timeout)
        {
            try
            {
                var messages = new List<MessageResult>();

                // Parse broker URL
                var brokerUri = ParseBrokerUrl(broker);

                // Create client and connect
                IClient client = IClient.Create();

                ConnectionOptions options = new ConnectionOptions
                {
                    User = "artemis",
                    Password = "artemis"
                };

                using IConnection connection = client.Connect(brokerUri.Host, brokerUri.Port, options);
                using IReceiver receiver = connection.OpenReceiver(queue);

                // Receive messages with timeout
                var timeoutMs = timeout * 1000;
                for (int i = 0; i < count; i++)
                {
                    IDelivery delivery = receiver.Receive(TimeSpan.FromMilliseconds(timeoutMs));

                    if (delivery == null)
                    {
                        break;  // Timeout
                    }

                    IMessage<object> message = delivery.Message();

                    // Check for JMS message type annotation
                    sbyte jmsType = -1;
                    if (message.HasAnnotation("x-opt-jms-msg-type"))
                    {
                        jmsType = Convert.ToSByte(message.GetAnnotation("x-opt-jms-msg-type"));
                    }

                    DecodedMessage decoded;
                    if (jmsType >= 0)
                    {
                        // Decode as JMS message
                        decoded = DecodeJmsMessage(message.Body, jmsType);
                    }
                    else
                    {
                        bool isAmqpValue = false;
                        var advanced = message as IAdvancedMessage<object>;
                        if (advanced != null)
                        {
                            var sections = advanced.GetBodySections();
                            if (sections != null)
                            {
                                foreach (var section in sections)
                                {
                                    if (section is AmqpValue)
                                        isAmqpValue = true;
                                    break;
                                }
                            }
                        }
                        decoded = TypeCodec.Decode(message.Body, isAmqpValue);
                    }

                    var msgResult = new MessageResult
                    {
                        Index = i,
                        Type = decoded.Type,
                        Value = decoded.Value
                    };

                    // Extract JMS headers
                    var hdrs = new Dictionary<string, object>();
                    if (message.CorrelationId != null)
                    {
                        if (message.CorrelationId is byte[] corrBytes)
                        {
                            hdrs["JMSCorrelationID"] = new Dictionary<string, string>
                            {
                                { "type", "bytes" },
                                { "value", BitConverter.ToString(corrBytes).Replace("-", "").ToLower() }
                            };
                        }
                        else if (message.CorrelationId is IProtonBuffer buf)
                        {
                            var bytes = new byte[buf.ReadableBytes];
                            buf.CopyInto(buf.ReadOffset, bytes, 0, bytes.Length);
                            hdrs["JMSCorrelationID"] = new Dictionary<string, string>
                            {
                                { "type", "bytes" },
                                { "value", BitConverter.ToString(bytes).Replace("-", "").ToLower() }
                            };
                        }
                        else
                        {
                            hdrs["JMSCorrelationID"] = message.CorrelationId.ToString();
                        }
                    }
                    if (message.ReplyTo != null)
                    {
                        string replyType = "queue";
                        string replyAddr = message.ReplyTo;
                        if (message.HasAnnotation("x-opt-jms-reply-to"))
                        {
                            var rt = Convert.ToSByte(message.GetAnnotation("x-opt-jms-reply-to"));
                            if (rt == 1) replyType = "topic";
                        }
                        else if (replyAddr.StartsWith("topic://"))
                        {
                            replyType = "topic";
                            replyAddr = replyAddr.Substring(8);
                        }
                        else if (replyAddr.StartsWith("queue://"))
                        {
                            replyAddr = replyAddr.Substring(8);
                        }
                        hdrs["JMSReplyTo"] = new Dictionary<string, string>
                        {
                            { "type", replyType },
                            { "value", replyAddr }
                        };
                    }
                    if (message.Subject != null)
                    {
                        hdrs["JMSType"] = message.Subject;
                    }
                    if (hdrs.Count > 0)
                    {
                        msgResult.Headers = hdrs;
                    }

                    // Extract JMS application properties
                    var props = new Dictionary<string, object>();
                    message.ForEachProperty((name, value) =>
                    {
                        if (value is bool b)
                        {
                            var boolProp = new Dictionary<string, object>
                            {
                                { "type", "boolean" },
                                { "value", b }
                            };
                            props[name] = boolProp;
                            return;
                        }
                        Dictionary<string, string> prop;
                        if (value is sbyte sb)
                        {
                            prop = new Dictionary<string, string>
                            {
                                { "type", "byte" },
                                { "value", $"0x{(sb & 0xFF):x2}" }
                            };
                        }
                        else if (value is short s)
                        {
                            prop = new Dictionary<string, string>
                            {
                                { "type", "short" },
                                { "value", $"0x{(s & 0xFFFF):x4}" }
                            };
                        }
                        else if (value is int i)
                        {
                            prop = new Dictionary<string, string>
                            {
                                { "type", "int" },
                                { "value", $"0x{(uint)i:x8}" }
                            };
                        }
                        else if (value is long l)
                        {
                            prop = new Dictionary<string, string>
                            {
                                { "type", "long" },
                                { "value", $"0x{(ulong)l:x16}" }
                            };
                        }
                        else if (value is float f)
                        {
                            var bits = BitConverter.SingleToInt32Bits(f);
                            prop = new Dictionary<string, string>
                            {
                                { "type", "float" },
                                { "value", $"0x{(uint)bits:x8}" }
                            };
                        }
                        else if (value is double d)
                        {
                            var bits = BitConverter.DoubleToInt64Bits(d);
                            prop = new Dictionary<string, string>
                            {
                                { "type", "double" },
                                { "value", $"0x{(ulong)bits:x16}" }
                            };
                        }
                        else if (value is string str)
                        {
                            prop = new Dictionary<string, string>
                            {
                                { "type", "string" },
                                { "value", str }
                            };
                        }
                        else
                        {
                            prop = new Dictionary<string, string>
                            {
                                { "type", "string" },
                                { "value", value?.ToString() ?? "" }
                            };
                        }
                        props[name] = prop;
                    });
                    if (props.Count > 0)
                    {
                        msgResult.Properties = props;
                    }

                    // Extract AMQP Header section fields
                    msgResult.MessageHeader = new Dictionary<string, object>
                    {
                        { "durable", message.Durable },
                        { "priority", (int)message.Priority },
                        { "ttl", (long)message.TimeToLive },
                        { "first_acquirer", message.FirstAcquirer },
                        { "delivery_count", (int)message.DeliveryCount },
                    };

                    messages.Add(msgResult);
                }

                // Output result
                var result = new
                {
                    messages,
                    stats = new { received = messages.Count }
                };

                Console.WriteLine(JsonConvert.SerializeObject(result, Formatting.Indented));

                if (messages.Count < count)
                {
                    Environment.Exit(1);
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Receive error: {ex.Message}");
                Environment.Exit(1);
            }
        }

        public static void ReceiveLargeContent(string broker, string queue, string contentType, int size, int seed, int timeout, int elements = 0, int elementSize = 0)
        {
            try
            {
                var brokerUri = ParseBrokerUrl(broker);

                IClient client = IClient.Create();
                ConnectionOptions options = new ConnectionOptions
                {
                    User = "artemis",
                    Password = "artemis"
                };

                using IConnection connection = client.Connect(brokerUri.Host, brokerUri.Port, options);
                using IReceiver receiver = connection.OpenReceiver(queue);

                IDelivery delivery = receiver.Receive(TimeSpan.FromSeconds(timeout));
                if (delivery == null)
                {
                    Console.WriteLine(JsonConvert.SerializeObject(new { match = false, error = "no message received" }));
                    Environment.Exit(1);
                }

                IMessage<object> message = delivery.Message();

                object receivedBody = message.Body;
                bool matched;
                int receivedSize;
                int? firstMismatchOffset = null;

                if (contentType == "binary")
                {
                    byte[] expected = LcgHelper.LcgGenerateBytes((uint)seed, size);
                    byte[] received;
                    if (receivedBody is byte[] byteArray)
                        received = byteArray;
                    else if (receivedBody is IProtonBuffer buf)
                    {
                        received = new byte[buf.ReadableBytes];
                        buf.CopyInto(buf.ReadOffset, received, 0, received.Length);
                    }
                    else
                    {
                        Console.WriteLine(JsonConvert.SerializeObject(new { match = false, error = "expected binary body but got " + (receivedBody?.GetType().Name ?? "null") }));
                        Environment.Exit(1);
                        return;
                    }

                    receivedSize = received.Length;
                    if (received.Length != expected.Length)
                    {
                        matched = false;
                    }
                    else
                    {
                        matched = true;
                        for (int i = 0; i < expected.Length; i++)
                        {
                            if (received[i] != expected[i])
                            {
                                matched = false;
                                firstMismatchOffset = i;
                                break;
                            }
                        }
                    }
                }
                else if (contentType == "string")
                {
                    string expected = LcgHelper.LcgGenerateString((uint)seed, size);
                    string received = receivedBody as string ?? receivedBody?.ToString() ?? "";

                    receivedSize = received.Length;
                    if (received.Length != expected.Length)
                    {
                        matched = false;
                    }
                    else
                    {
                        matched = true;
                        for (int i = 0; i < expected.Length; i++)
                        {
                            if (received[i] != expected[i])
                            {
                                matched = false;
                                firstMismatchOffset = i;
                                break;
                            }
                        }
                    }
                }
                else if (contentType == "list" || contentType == "array" || contentType == "map" || contentType == "described")
                {
                    var expected = LcgHelper.GenerateCollectionElements((uint)seed, elements, elementSize);
                    var received = new List<string>();

                    if (contentType == "list")
                    {
                        if (receivedBody is IList list)
                        {
                            foreach (var item in list)
                                received.Add(item?.ToString() ?? "");
                        }
                        else
                        {
                            Console.WriteLine(JsonConvert.SerializeObject(new { match = false, error = "expected list, got " + (receivedBody?.GetType().Name ?? "null") }));
                            Environment.Exit(1);
                            return;
                        }
                    }
                    else if (contentType == "array")
                    {
                        if (receivedBody is string[] strArr)
                        {
                            received.AddRange(strArr);
                        }
                        else if (receivedBody is object[] objArr)
                        {
                            foreach (var o in objArr) received.Add(o?.ToString() ?? "");
                        }
                        else if (receivedBody is IList arrList)
                        {
                            foreach (var item in arrList) received.Add(item?.ToString() ?? "");
                        }
                        else
                        {
                            Console.WriteLine(JsonConvert.SerializeObject(new { match = false, error = "expected array, got " + (receivedBody?.GetType().Name ?? "null") }));
                            Environment.Exit(1);
                            return;
                        }
                    }
                    else if (contentType == "map")
                    {
                        if (receivedBody is IDictionary dict)
                        {
                            var keys = LcgHelper.GenerateMapKeys(elements);
                            foreach (var key in keys)
                            {
                                received.Add(dict.Contains(key) ? dict[key]?.ToString() ?? "" : "");
                            }
                        }
                        else
                        {
                            Console.WriteLine(JsonConvert.SerializeObject(new { match = false, error = "expected map, got " + (receivedBody?.GetType().Name ?? "null") }));
                            Environment.Exit(1);
                            return;
                        }
                    }
                    else if (contentType == "described")
                    {
                        object inner = receivedBody;
                        // Check if it's a described type (IDescribedType) and unwrap
                        if (receivedBody is IDescribedType desc)
                            inner = desc.Described;

                        if (inner is IList descList)
                        {
                            foreach (var item in descList) received.Add(item?.ToString() ?? "");
                        }
                        else
                        {
                            Console.WriteLine(JsonConvert.SerializeObject(new { match = false, error = "expected described list, got " + (inner?.GetType().Name ?? "null") }));
                            Environment.Exit(1);
                            return;
                        }
                    }

                    // Compare element by element
                    var collResult = new Dictionary<string, object>
                    {
                        { "elements", received.Count },
                        { "element_size", elementSize }
                    };

                    if (received.Count != elements)
                    {
                        collResult["match"] = false;
                    }
                    else
                    {
                        bool collMatched = true;
                        for (int i = 0; i < elements; i++)
                        {
                            if (expected[i] != received[i])
                            {
                                collMatched = false;
                                collResult["first_mismatch_element"] = i;
                                int minLen = Math.Min(expected[i].Length, received[i].Length);
                                int offset = minLen;
                                for (int j = 0; j < minLen; j++)
                                {
                                    if (expected[i][j] != received[i][j])
                                    {
                                        offset = j;
                                        break;
                                    }
                                }
                                collResult["first_mismatch_offset"] = offset;
                                break;
                            }
                        }
                        collResult["match"] = collMatched;
                    }

                    Console.WriteLine(JsonConvert.SerializeObject(collResult));
                    if (!(bool)collResult["match"])
                        Environment.Exit(1);
                    return;
                }
                else
                {
                    Console.WriteLine(JsonConvert.SerializeObject(new { match = false, error = $"unknown content type: {contentType}" }));
                    Environment.Exit(1);
                    return;
                }

                var result = new Dictionary<string, object>
                {
                    { "match", matched },
                    { "size", receivedSize },
                    { "expected_size", size }
                };
                if (firstMismatchOffset.HasValue)
                    result["first_mismatch_offset"] = firstMismatchOffset.Value;

                Console.WriteLine(JsonConvert.SerializeObject(result));

                if (!matched)
                    Environment.Exit(1);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Receive error: {ex.Message}");
                Environment.Exit(1);
            }
        }

        private static (string Host, int Port) ParseBrokerUrl(string broker)
        {
            var uri = new Uri(broker.StartsWith("amqp://") ? broker : $"amqp://{broker}");
            return (uri.Host, uri.Port > 0 ? uri.Port : 5672);
        }

        private static DecodedMessage DecodeJmsMessage(object body, sbyte jmsType)
        {
            // JMS message type constants
            const sbyte JMS_MESSAGE = 0;
            const sbyte JMS_TEXT_MESSAGE = 5;
            const sbyte JMS_BYTES_MESSAGE = 3;
            const sbyte JMS_MAP_MESSAGE = 2;
            const sbyte JMS_STREAM_MESSAGE = 4;

            if (jmsType == JMS_TEXT_MESSAGE)
            {
                // TextMessage: body is string in AmqpValue section
                return new DecodedMessage
                {
                    Type = "text",  // Use 'text' to match JMS shim output
                    Value = body as string
                };
            }
            else if (jmsType == JMS_BYTES_MESSAGE)
            {
                // BytesMessage: body is binary in Data section
                if (body is byte[] bytes)
                {
                    return new DecodedMessage
                    {
                        Type = "bytes",
                        Value = BitConverter.ToString(bytes).Replace("-", "").ToLower()
                    };
                }
                return new DecodedMessage { Type = "bytes", Value = "" };
            }
            else if (jmsType == JMS_MESSAGE)
            {
                // Empty message
                return new DecodedMessage
                {
                    Type = "null",
                    Value = null
                };
            }

            if (jmsType == JMS_MAP_MESSAGE)
            {
                if (body is IDictionary dict && dict.Count > 0)
                {
                    var enumerator = dict.GetEnumerator();
                    enumerator.MoveNext();
                    return TypeCodec.Decode(enumerator.Value);
                }
                return new DecodedMessage { Type = "none", Value = null };
            }

            if (jmsType == JMS_STREAM_MESSAGE)
            {
                if (body is IList list && list.Count > 0)
                {
                    return TypeCodec.Decode(list[0]);
                }
                return new DecodedMessage { Type = "none", Value = null };
            }

            // Unknown JMS type, fall back to regular AMQP decoding
            return TypeCodec.Decode(body);
        }
    }
}
