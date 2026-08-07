/**
 * Proton .NET Bug: ListTypeEncoder NullReferenceException on null-after-non-null
 *
 * Same root cause as the ProtonJ2 NPE: encoding a list with null after
 * non-null crashes the encoder.
 *
 * Tested with: Apache.Qpid.Proton.Client 1.0.0
 * Requires: Artemis broker on localhost:5672 (user: artemis, pass: artemis)
 *
 * Run: dotnet run
 *
 * Expected: message sent successfully
 * Actual:   NullReferenceException in ListTypeEncoder
 */

using Apache.Qpid.Proton.Client;

var client = IClient.Create();
var options = new ConnectionOptions { User = "artemis", Password = "artemis" };

try
{
    using var conn = client.Connect("localhost", 5672, options);
    using var sender = conn.OpenSender("test.bug.list-null-nre");

    var msg = IMessage<object>.Create();
    msg.Body = new List<object> { "hello", null };
    sender.Send(msg);
    Console.WriteLine("PASS: message sent");
}
catch (Exception e)
{
    Console.WriteLine($"FAIL: {e.GetType().Name}: {e.Message}");
}
