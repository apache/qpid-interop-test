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
 * QIT .NET Apache Qpid Proton Shim - Main Entry Point
 *
 * Command-line interface for AMQP interoperability testing using Qpid Proton .NET
 */

using System;
using System.CommandLine;
using System.CommandLine.Invocation;

namespace Qit.Shim
{
    class Program
    {
        static int Main(string[] args)
        {
            var rootCommand = new RootCommand("QIT Apache Qpid Proton .NET Shim");

            // Send command
            var sendCommand = new Command("send", "Send AMQP messages");
            var sendBrokerOption = new Option<string>("--broker", "Broker URL") { IsRequired = true };
            var sendQueueOption = new Option<string>("--queue", "Queue name") { IsRequired = true };
            var sendTypeOption = new Option<string>("--type", "AMQP type");
            var sendCountOption = new Option<int>("--count", "Message count") { IsRequired = false };
            var sendDataOption = new Option<string>("--data", "JSON test data");
            var sendJmsModeOption = new Option<bool>("--jms-mode", () => false, "Enable JMS emulation mode");
            var sendHeadersOption = new Option<string>("--headers", () => null, "JSON JMS headers");
            var sendPropertiesOption = new Option<string>("--properties", () => null, "JSON JMS application properties");
            var sendMessageHeaderOption = new Option<string>("--message-header", () => null, "JSON AMQP Header section fields");
            var sendLargeContentOption = new Option<string>("--large-content", () => null, "Large content type (binary or string)");
            var sendSizeOption = new Option<int>("--size", () => 0, "Large content size");
            var sendSeedOption = new Option<int>("--seed", () => 0, "PRNG seed");
            var sendElementsOption = new Option<int>("--elements", () => 0, "Number of collection elements");
            var sendElementSizeOption = new Option<int>("--element-size", () => 0, "Size of each element");

            sendCommand.AddOption(sendBrokerOption);
            sendCommand.AddOption(sendQueueOption);
            sendCommand.AddOption(sendTypeOption);
            sendCommand.AddOption(sendCountOption);
            sendCommand.AddOption(sendDataOption);
            sendCommand.AddOption(sendJmsModeOption);
            sendCommand.AddOption(sendHeadersOption);
            sendCommand.AddOption(sendPropertiesOption);
            sendCommand.AddOption(sendMessageHeaderOption);
            sendCommand.AddOption(sendLargeContentOption);
            sendCommand.AddOption(sendSizeOption);
            sendCommand.AddOption(sendSeedOption);
            sendCommand.AddOption(sendElementsOption);
            sendCommand.AddOption(sendElementSizeOption);

            sendCommand.SetHandler((context) =>
            {
                try
                {
                    var broker = context.ParseResult.GetValueForOption(sendBrokerOption);
                    var queue = context.ParseResult.GetValueForOption(sendQueueOption);
                    var jmsMode = context.ParseResult.GetValueForOption(sendJmsModeOption);
                    var largeContent = context.ParseResult.GetValueForOption(sendLargeContentOption);

                    if (!string.IsNullOrEmpty(largeContent))
                    {
                        var size = context.ParseResult.GetValueForOption(sendSizeOption);
                        var seed = context.ParseResult.GetValueForOption(sendSeedOption);
                        var elements = context.ParseResult.GetValueForOption(sendElementsOption);
                        var elementSize = context.ParseResult.GetValueForOption(sendElementSizeOption);
                        Sender.SendLargeContent(broker, queue, largeContent, size, seed, jmsMode, elements, elementSize);
                    }
                    else
                    {
                        var type = context.ParseResult.GetValueForOption(sendTypeOption);
                        var data = context.ParseResult.GetValueForOption(sendDataOption);
                        var headers = context.ParseResult.GetValueForOption(sendHeadersOption);
                        var properties = context.ParseResult.GetValueForOption(sendPropertiesOption);
                        var messageHeaderStr = context.ParseResult.GetValueForOption(sendMessageHeaderOption);
                        Sender.Send(broker, queue, type, data, jmsMode, headers, properties, messageHeaderStr);
                    }
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"Error: {ex.Message}");
                    Environment.Exit(1);
                }
            });

            // Receive command
            var receiveCommand = new Command("receive", "Receive AMQP messages");
            var receiveBrokerOption = new Option<string>("--broker", "Broker URL") { IsRequired = true };
            var receiveQueueOption = new Option<string>("--queue", "Queue name") { IsRequired = true };
            var receiveCountOption = new Option<int>("--count", "Expected message count");
            var receiveTimeoutOption = new Option<int>("--timeout", () => 30, "Timeout in seconds");
            var receiveLargeContentOption = new Option<string>("--large-content", () => null, "Large content type (binary or string)");
            var receiveSizeOption = new Option<int>("--size", () => 0, "Large content size");
            var receiveSeedOption = new Option<int>("--seed", () => 0, "PRNG seed");
            var receiveElementsOption = new Option<int>("--elements", () => 0, "Number of collection elements");
            var receiveElementSizeOption = new Option<int>("--element-size", () => 0, "Size of each element");

            receiveCommand.AddOption(receiveBrokerOption);
            receiveCommand.AddOption(receiveQueueOption);
            receiveCommand.AddOption(receiveCountOption);
            receiveCommand.AddOption(receiveTimeoutOption);
            receiveCommand.AddOption(receiveLargeContentOption);
            receiveCommand.AddOption(receiveSizeOption);
            receiveCommand.AddOption(receiveSeedOption);
            receiveCommand.AddOption(receiveElementsOption);
            receiveCommand.AddOption(receiveElementSizeOption);

            receiveCommand.SetHandler((context) =>
            {
                try
                {
                    var broker = context.ParseResult.GetValueForOption(receiveBrokerOption);
                    var queue = context.ParseResult.GetValueForOption(receiveQueueOption);
                    var timeout = context.ParseResult.GetValueForOption(receiveTimeoutOption);
                    var largeContent = context.ParseResult.GetValueForOption(receiveLargeContentOption);

                    if (!string.IsNullOrEmpty(largeContent))
                    {
                        var size = context.ParseResult.GetValueForOption(receiveSizeOption);
                        var seed = context.ParseResult.GetValueForOption(receiveSeedOption);
                        var elements = context.ParseResult.GetValueForOption(receiveElementsOption);
                        var elementSize = context.ParseResult.GetValueForOption(receiveElementSizeOption);
                        Receiver.ReceiveLargeContent(broker, queue, largeContent, size, seed, timeout, elements, elementSize);
                    }
                    else
                    {
                        var count = context.ParseResult.GetValueForOption(receiveCountOption);
                        Receiver.Receive(broker, queue, count, timeout);
                    }
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"Error: {ex.Message}");
                    Environment.Exit(1);
                }
            });

            rootCommand.AddCommand(sendCommand);
            rootCommand.AddCommand(receiveCommand);

            return rootCommand.Invoke(args);
        }
    }
}
