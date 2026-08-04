/*
 * QIT .NET Apache Qpid Proton Shim - Receiver
 */

using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Apache.Qpid.Proton.Client;
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

                    messages.Add(new MessageResult
                    {
                        Index = i,
                        Type = decoded.Type,
                        Value = decoded.Value
                    });
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
