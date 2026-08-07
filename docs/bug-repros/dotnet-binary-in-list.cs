/**
 * Proton .NET Bug: byte[] encoded as array-of-ubyte instead of binary in lists
 *
 * When byte[] appears inside a List<object>, Proton .NET encodes it as an
 * AMQP array<ubyte> instead of AMQP binary. Other clients then receive an
 * array of integers rather than a binary blob.
 *
 * Root cause: byte[] implements IList<byte>, so the encoder picks the array
 * code path over the binary code path.
 *
 * Tested with: Apache.Qpid.Proton.Client 1.0.0
 * Requires: Artemis broker on localhost:5672 (user: artemis, pass: artemis)
 *
 * Run .NET sender, then receive with Python:
 *   python3 -c "
 *   from proton.handlers import MessagingHandler
 *   from proton.reactor import Container
 *   class R(MessagingHandler):
 *       def on_message(self, event):
 *           body = event.message.body
 *           elem = body[0] if body else None
 *           print(f'Type: {type(elem).__name__}, Value: {elem}')
 *           event.connection.close()
 *   Container(R('amqp://artemis:artemis@localhost:5672/test.bug.binary-list')).run()
 *   "
 *
 * Expected: Python receives bytes (b'\x01\x02\x03')
 * Actual:   Python receives list or array ([1, 2, 3])
 */

using Apache.Qpid.Proton.Client;

var client = IClient.Create();
var options = new ConnectionOptions { User = "artemis", Password = "artemis" };

using var conn = client.Connect("localhost", 5672, options);
using var sender = conn.OpenSender("test.bug.binary-list");

var msg = IMessage<object>.Create();
msg.Body = new List<object> { new byte[] { 0x01, 0x02, 0x03 } };
sender.Send(msg);
Console.WriteLine("Sent list containing byte[] — check receiver for type");
