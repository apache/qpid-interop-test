/*
 * QIT .NET Apache Qpid Proton Shim - Sender
 */

using System;
using System.Collections.Generic;
using Apache.Qpid.Proton.Client;
using Newtonsoft.Json;

namespace Qit.Shim
{
    public static class Sender
    {
        public static void Send(string broker, string queue, string type, string data, bool jmsMode = false)
        {
            try
            {
                var testData = JsonConvert.DeserializeObject<List<TestMessage>>(data);
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

                    if (type == "map")
                    {
                        var subType = testMsg.Type ?? "string";
                        var key = $"{subType}_{testMsg.Index:D3}";
                        var encodedValue = TypeCodec.Encode(subType, testMsg.Value);
                        message.Body = new Dictionary<string, object> { { key, encodedValue } };
                    }
                    else if (type == "list")
                    {
                        var subType = testMsg.Type ?? "string";
                        var encodedValue = TypeCodec.Encode(subType, testMsg.Value);
                        message.Body = new List<object> { encodedValue };
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
    }
}
