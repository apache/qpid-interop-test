/*
 * QIT .NET Apache Qpid Proton Shim - Main Entry Point
 *
 * Command-line interface for AMQP interoperability testing using Qpid Proton .NET
 */

using System;
using System.CommandLine;

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
            var sendTypeOption = new Option<string>("--type", "AMQP type") { IsRequired = true };
            var sendCountOption = new Option<int>("--count", "Message count") { IsRequired = false };
            var sendDataOption = new Option<string>("--data", "JSON test data") { IsRequired = true };
            var sendJmsModeOption = new Option<bool>("--jms-mode", () => false, "Enable JMS emulation mode");
            var sendHeadersOption = new Option<string>("--headers", () => null, "JSON JMS headers");

            sendCommand.AddOption(sendBrokerOption);
            sendCommand.AddOption(sendQueueOption);
            sendCommand.AddOption(sendTypeOption);
            sendCommand.AddOption(sendCountOption);
            sendCommand.AddOption(sendDataOption);
            sendCommand.AddOption(sendJmsModeOption);
            sendCommand.AddOption(sendHeadersOption);

            sendCommand.SetHandler((broker, queue, type, count, data, jmsMode, headers) =>
            {
                try
                {
                    Sender.Send(broker, queue, type, data, jmsMode, headers);
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"Error: {ex.Message}");
                    Environment.Exit(1);
                }
            }, sendBrokerOption, sendQueueOption, sendTypeOption, sendCountOption, sendDataOption, sendJmsModeOption, sendHeadersOption);

            // Receive command
            var receiveCommand = new Command("receive", "Receive AMQP messages");
            var receiveBrokerOption = new Option<string>("--broker", "Broker URL") { IsRequired = true };
            var receiveQueueOption = new Option<string>("--queue", "Queue name") { IsRequired = true };
            var receiveCountOption = new Option<int>("--count", "Expected message count") { IsRequired = true };
            var receiveTimeoutOption = new Option<int>("--timeout", () => 30, "Timeout in seconds");

            receiveCommand.AddOption(receiveBrokerOption);
            receiveCommand.AddOption(receiveQueueOption);
            receiveCommand.AddOption(receiveCountOption);
            receiveCommand.AddOption(receiveTimeoutOption);

            receiveCommand.SetHandler((broker, queue, count, timeout) =>
            {
                try
                {
                    Receiver.Receive(broker, queue, count, timeout);
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"Error: {ex.Message}");
                    Environment.Exit(1);
                }
            }, receiveBrokerOption, receiveQueueOption, receiveCountOption, receiveTimeoutOption);

            rootCommand.AddCommand(sendCommand);
            rootCommand.AddCommand(receiveCommand);

            return rootCommand.Invoke(args);
        }
    }
}
