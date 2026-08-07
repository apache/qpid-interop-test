/**
 * Proton .NET Bug: AMQP timestamp decoded as Int64 instead of DateTime
 *
 * When receiving a message with an AMQP timestamp body, Proton .NET returns
 * System.Int64 (raw milliseconds) instead of System.DateTime, losing the
 * type information.
 *
 * Tested with: Apache.Qpid.Proton.Client 1.0.0
 * Requires: Artemis broker on localhost:5672 (user: artemis, pass: artemis)
 *
 * Send a timestamp from Python first:
 *
 *   python3 -c "
 *   from proton import Message, timestamp
 *   from proton.handlers import MessagingHandler
 *   from proton.reactor import Container
 *   class S(MessagingHandler):
 *       def on_sendable(self, event):
 *           event.sender.send(Message(body=timestamp(1234567890000)))
 *           event.sender.close()
 *           event.connection.close()
 *   Container(S('amqp://artemis:artemis@localhost:5672/test.bug.ts-type')).run()
 *   "
 *
 * Expected: DateTime or DateTimeOffset
 * Actual:   Int64
 */

using Apache.Qpid.Proton.Client;

var client = IClient.Create();
var options = new ConnectionOptions { User = "artemis", Password = "artemis" };

using var conn = client.Connect("localhost", 5672, options);
using var receiver = conn.OpenReceiver("test.bug.ts-type");

var delivery = receiver.Receive(TimeSpan.FromSeconds(10));
var body = delivery.Message().Body;
Console.WriteLine($"Type: {body.GetType().Name}");
Console.WriteLine($"Value: {body}");

if (body is DateTime || body is DateTimeOffset)
    Console.WriteLine("PASS: received as temporal type");
else
    Console.WriteLine($"FAIL: expected DateTime, got {body.GetType().Name}");
