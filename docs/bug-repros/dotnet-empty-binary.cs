/**
 * Proton .NET Bug: Empty binary round-trip loses type
 *
 * Sending an empty byte[] (zero-length binary) and receiving it back with
 * Proton .NET results in a different type (null or empty string).
 *
 * Tested with: Apache.Qpid.Proton.Client 1.0.0
 * Requires: Artemis broker on localhost:5672 (user: artemis, pass: artemis)
 *
 * Expected: received byte[] of length 0
 * Actual:   null or wrong type
 */

using Apache.Qpid.Proton.Client;

var client = IClient.Create();
var options = new ConnectionOptions { User = "artemis", Password = "artemis" };

using var conn = client.Connect("localhost", 5672, options);
using var sender = conn.OpenSender("test.bug.empty-binary");
using var receiver = conn.OpenReceiver("test.bug.empty-binary");

var msg = IMessage<object>.Create();
msg.Body = new byte[0];
sender.Send(msg);

var delivery = receiver.Receive(TimeSpan.FromSeconds(10));
var body = delivery.Message().Body;

if (body is byte[] bytes && bytes.Length == 0)
    Console.WriteLine("PASS: received empty byte[]");
else if (body == null)
    Console.WriteLine("FAIL: received null instead of empty byte[]");
else
    Console.WriteLine($"FAIL: received {body.GetType().Name}: {body}");
