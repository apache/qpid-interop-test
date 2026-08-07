/**
 * Proton .NET Bug: Cannot send binary correlation IDs
 *
 * AMQP spec allows correlation-id to be binary, but Proton .NET's encoder
 * rejects byte[] and IProtonBuffer for the correlation-id field.
 *
 * Tested with: Apache.Qpid.Proton.Client 1.0.0
 * Requires: Artemis broker on localhost:5672 (user: artemis, pass: artemis)
 *
 * Expected: binary correlation ID accepted
 * Actual:   encoder error
 */

using Apache.Qpid.Proton.Client;

var client = IClient.Create();
var options = new ConnectionOptions { User = "artemis", Password = "artemis" };

try
{
    using var conn = client.Connect("localhost", 5672, options);
    using var sender = conn.OpenSender("test.bug.binary-corrid");

    var msg = IMessage<object>.Create();
    msg.Body = "test";
    msg.CorrelationId = new byte[] { 0x01, 0x02, 0x03 };
    sender.Send(msg);
    Console.WriteLine("PASS: binary correlation ID accepted");
}
catch (Exception e)
{
    Console.WriteLine($"FAIL: {e.GetType().Name}: {e.Message}");
}
