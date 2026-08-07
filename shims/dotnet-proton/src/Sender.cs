/*
 * QIT .NET Apache Qpid Proton Shim - Sender
 */

using System;
using System.Collections.Generic;
using Apache.Qpid.Proton.Buffer;
using Apache.Qpid.Proton.Client;
using Apache.Qpid.Proton.Types;
using Apache.Qpid.Proton.Types.Messaging;
using Newtonsoft.Json;

namespace Qit.Shim
{
    public static class LcgHelper
    {
        public static byte[] LcgGenerateBytes(uint seed, int size)
        {
            uint state = seed & 0x7FFFFFFF;
            var result = new byte[size];
            for (int i = 0; i < size; i++)
            {
                state = (uint)((state * 1103515245u + 12345u) & 0x7FFFFFFF);
                result[i] = (byte)((state >> 16) & 0xFF);
            }
            return result;
        }

        public static string LcgGenerateString(uint seed, int size)
        {
            var raw = LcgGenerateBytes(seed, size);
            var chars = new char[size];
            for (int i = 0; i < size; i++)
                chars[i] = (char)(32 + (raw[i] % 95));
            return new string(chars);
        }

        public static List<string> GenerateCollectionElements(uint seed, int count, int elemSize)
        {
            int total = count * elemSize;
            string full = LcgGenerateString(seed, total);
            var result = new List<string>();
            for (int i = 0; i < count; i++)
                result.Add(full.Substring(i * elemSize, elemSize));
            return result;
        }

        public static List<string> GenerateMapKeys(int count)
        {
            var keys = new List<string>();
            for (int i = 0; i < count; i++)
                keys.Add($"key_{i:D4}");
            return keys;
        }
    }

    public static class Sender
    {
        public static void Send(string broker, string queue, string type, string data, bool jmsMode = false, string headersJson = null, string propertiesJson = null, string messageHeaderJson = null)
        {
            try
            {
                var testData = JsonConvert.DeserializeObject<List<TestMessage>>(data);
                Dictionary<string, Dictionary<string, string>> headers = null;
                if (!string.IsNullOrEmpty(headersJson))
                {
                    headers = JsonConvert.DeserializeObject<Dictionary<string, Dictionary<string, string>>>(headersJson);
                }
                Dictionary<string, Dictionary<string, string>> properties = null;
                if (!string.IsNullOrEmpty(propertiesJson))
                {
                    properties = JsonConvert.DeserializeObject<Dictionary<string, Dictionary<string, string>>>(propertiesJson);
                }
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
                using ISender sender = connection.OpenSender(queue);

                // Send all messages
                foreach (var testMsg in testData)
                {
                    var message = IMessage<object>.Create();
                    message.MessageId = testMsg.Index.ToString();

                    if (jmsMode && type == "map")
                    {
                        var subType = testMsg.Type ?? "string";
                        var key = $"{subType}_{testMsg.Index:D3}";
                        var encodedValue = TypeCodec.Encode(subType, testMsg.Value);
                        message.Body = new Dictionary<string, object> { { key, encodedValue } };
                    }
                    else if (jmsMode && type == "list")
                    {
                        var subType = testMsg.Type ?? "string";
                        var encodedValue = TypeCodec.Encode(subType, testMsg.Value);
                        message.Body = new List<object> { encodedValue };
                    }
                    else if (type == "array" || type == "described")
                    {
                        var encoded = TypeCodec.EncodeComplex(type, testMsg.Value);
                        var advanced = (IAdvancedMessage<object>)message;
                        advanced.AddBodySection(new AmqpValue(encoded));
                    }
                    else if (TypeCodec.IsComplexType(type))
                    {
                        message.Body = TypeCodec.EncodeComplex(type, testMsg.Value);
                    }
                    else
                    {
                        message.Body = TypeCodec.Encode(type, testMsg.Value);
                    }

                    // Add JMS annotations if in JMS mode
                    if (jmsMode)
                    {
                        sbyte jmsType = GetJmsMessageType(type);
                        if (jmsType >= 0)
                        {
                            // NOTE: Key MUST be symbol, value MUST be signed byte
                            // This matches Qpid JMS Client wire format
                            message.SetAnnotation("x-opt-jms-msg-type", jmsType);
                        }
                    }

                    // Apply JMS headers
                    if (headers != null)
                    {
                        if (headers.ContainsKey("JMSCorrelationID"))
                        {
                            var h = headers["JMSCorrelationID"];
                            if (h["type"] == "string")
                            {
                                message.CorrelationId = h["value"];
                            }
                            else if (h["type"] == "bytes")
                            {
                                // .NET Proton client cannot send binary correlation IDs —
                                // neither byte[] nor IProtonBuffer is accepted by the encoder
                                Console.Error.WriteLine("Send error: .NET Proton does not support binary correlation IDs");
                                Environment.Exit(1);
                            }
                        }
                        if (headers.ContainsKey("JMSReplyTo"))
                        {
                            var h = headers["JMSReplyTo"];
                            message.ReplyTo = h["value"];
                            sbyte replyType = (sbyte)(h["type"] == "topic" ? 1 : 0);
                            message.SetAnnotation("x-opt-jms-reply-to", replyType);
                        }
                        if (headers.ContainsKey("JMSType"))
                        {
                            var h = headers["JMSType"];
                            message.Subject = h["value"];
                        }
                    }

                    // Apply JMS application properties
                    if (properties != null)
                    {
                        foreach (var kvp in properties)
                        {
                            var name = kvp.Key;
                            var prop = kvp.Value;
                            var propType = prop["type"];
                            var propValue = prop["value"];

                            object typedValue = propType switch
                            {
                                "boolean" => bool.Parse(propValue),
                                "byte" => (sbyte)Convert.ToInt32(propValue, 16),
                                "short" => unchecked((short)Convert.ToInt32(propValue, 16)),
                                "int" => unchecked((int)Convert.ToUInt32(propValue, 16)),
                                "long" => unchecked((long)Convert.ToUInt64(propValue, 16)),
                                "float" => BitConverter.Int32BitsToSingle(unchecked((int)Convert.ToUInt32(propValue, 16))),
                                "double" => BitConverter.Int64BitsToDouble(unchecked((long)Convert.ToUInt64(propValue, 16))),
                                "string" => propValue,
                                _ => propValue
                            };

                            message.SetProperty(name, typedValue);
                        }
                    }

                    // Apply AMQP Header section fields
                    if (!string.IsNullOrEmpty(messageHeaderJson))
                    {
                        var mh = JsonConvert.DeserializeObject<Dictionary<string, object>>(messageHeaderJson);
                        if (mh.ContainsKey("durable"))
                            message.Durable = Convert.ToBoolean(mh["durable"]);
                        if (mh.ContainsKey("priority"))
                            message.Priority = (byte)Convert.ToInt32(mh["priority"]);
                        if (mh.ContainsKey("ttl"))
                            message.TimeToLive = Convert.ToUInt32(mh["ttl"]);
                        if (mh.ContainsKey("first_acquirer"))
                            message.FirstAcquirer = Convert.ToBoolean(mh["first_acquirer"]);
                    }

                    sender.Send(message);

                    messages.Add(new MessageResult
                    {
                        Index = testMsg.Index,
                        Type = type,
                        Value = testMsg.Value
                    });
                }

                // Output result
                var result = new
                {
                    messages,
                    stats = new { sent = messages.Count }
                };

                Console.WriteLine(JsonConvert.SerializeObject(result, Formatting.Indented));
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Send error: {ex.Message}");
                Environment.Exit(1);
            }
        }

        public static void SendLargeContent(string broker, string queue, string contentType, int size, int seed, bool jmsMode, int elements = 0, int elementSize = 0)
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
                using ISender sender = connection.OpenSender(queue);

                var message = IMessage<object>.Create();
                sbyte jmsMsgType = -1;

                if (contentType == "binary")
                {
                    message.Body = LcgHelper.LcgGenerateBytes((uint)seed, size);
                    jmsMsgType = 3; // JMS_BYTES_MESSAGE
                }
                else if (contentType == "string")
                {
                    message.Body = LcgHelper.LcgGenerateString((uint)seed, size);
                    jmsMsgType = 5; // JMS_TEXT_MESSAGE
                }
                else if (contentType == "list")
                {
                    var elems = LcgHelper.GenerateCollectionElements((uint)seed, elements, elementSize);
                    message.Body = new List<object>(elems);
                    jmsMsgType = 4; // JMS_STREAM_MESSAGE
                }
                else if (contentType == "array")
                {
                    var elems = LcgHelper.GenerateCollectionElements((uint)seed, elements, elementSize);
                    message.Body = elems.ToArray();
                }
                else if (contentType == "map")
                {
                    var elems = LcgHelper.GenerateCollectionElements((uint)seed, elements, elementSize);
                    var keys = LcgHelper.GenerateMapKeys(elements);
                    var map = new Dictionary<string, object>();
                    for (int i = 0; i < elements; i++)
                        map[keys[i]] = elems[i];
                    message.Body = map;
                    jmsMsgType = 2; // JMS_MAP_MESSAGE
                }
                else if (contentType == "described")
                {
                    var elems = LcgHelper.GenerateCollectionElements((uint)seed, elements, elementSize);
                    // Use DescribedValue (implements IDescribedType) with a symbol descriptor
                    var described = new DescribedValue(
                        Symbol.Lookup("test.large.described"),
                        new List<object>(elems));
                    message.Body = described;
                }
                else
                {
                    Console.Error.WriteLine($"Unknown large-content type: {contentType}");
                    Environment.Exit(1);
                }

                if (jmsMode && jmsMsgType >= 0)
                    message.SetAnnotation("x-opt-jms-msg-type", jmsMsgType);

                sender.Send(message);

                if (contentType == "binary" || contentType == "string")
                {
                    Console.WriteLine(JsonConvert.SerializeObject(new { sent = true, size }));
                }
                else
                {
                    Console.WriteLine(JsonConvert.SerializeObject(new { sent = true, elements, element_size = elementSize }));
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Send error: {ex.Message}");
                Environment.Exit(1);
            }
        }

        private static (string Host, int Port) ParseBrokerUrl(string broker)
        {
            var uri = new Uri(broker.StartsWith("amqp://") ? broker : $"amqp://{broker}");
            return (uri.Host, uri.Port > 0 ? uri.Port : 5672);
        }

        private static sbyte GetJmsMessageType(string amqpType)
        {
            // JMS message type constants (from Qpid JMS Client)
            const sbyte JMS_MESSAGE = 0;        // Empty message
            const sbyte JMS_MAP_MESSAGE = 2;    // Map
            const sbyte JMS_BYTES_MESSAGE = 3;  // Binary data
            const sbyte JMS_STREAM_MESSAGE = 4; // List/stream
            const sbyte JMS_TEXT_MESSAGE = 5;   // String/text

            return amqpType switch
            {
                "string" => JMS_TEXT_MESSAGE,
                "binary" => JMS_BYTES_MESSAGE,
                "null" => JMS_MESSAGE,
                "map" => JMS_MAP_MESSAGE,
                "list" => JMS_STREAM_MESSAGE,
                _ => -1
            };
        }
    }

    public class TestMessage
    {
        [JsonProperty("index")]
        public int Index { get; set; }

        [JsonProperty("type")]
        public string Type { get; set; } = "string";

        [JsonProperty("value")]
        public object Value { get; set; }
    }

    public class MessageResult
    {
        [JsonProperty("index")]
        public int Index { get; set; }

        [JsonProperty("type")]
        public string Type { get; set; }

        [JsonProperty("value")]
        public object Value { get; set; }

        [JsonProperty("headers", NullValueHandling = NullValueHandling.Ignore)]
        public Dictionary<string, object> Headers { get; set; }

        [JsonProperty("properties", NullValueHandling = NullValueHandling.Ignore)]
        public Dictionary<string, object> Properties { get; set; }

        [JsonProperty("message_header", NullValueHandling = NullValueHandling.Ignore)]
        public Dictionary<string, object> MessageHeader { get; set; }
    }
}
