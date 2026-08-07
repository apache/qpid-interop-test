/**
 * ProtonJ2 Bug: ulong values > 2^63 decoded as negative signed long
 *
 * AMQP ulong is unsigned 64-bit (0 to 2^64-1). ProtonJ2 maps it to Java
 * long (signed), so values > Long.MAX_VALUE wrap to negative.
 *
 * Tested with: protonj2-client 1.1.0
 * Requires: Artemis broker on localhost:5672 (user: artemis, pass: artemis)
 *
 * This test sends from Python (which handles ulong correctly) and receives
 * with ProtonJ2. Run the Python sender first:
 *
 *   python3 -c "
 *   from proton import Message
 *   from proton.handlers import MessagingHandler
 *   from proton.reactor import Container
 *   class S(MessagingHandler):
 *       def on_sendable(self, event):
 *           from proton import ulong
 *           event.sender.send(Message(body=ulong(18446744073709551615)))
 *           event.sender.close()
 *           event.connection.close()
 *   Container(S('amqp://artemis:artemis@localhost:5672/test.bug.ulong')).run()
 *   "
 *
 * Then run this Java receiver.
 *
 * Expected: 18446744073709551615
 * Actual:   -1
 */

import org.apache.qpid.protonj2.client.*;

public class ProtonJ2UlongOverflow {
    public static void main(String[] args) throws Exception {
        try (Client client = Client.create();
             Connection conn = client.connect("localhost", 5672,
                 new ConnectionOptions().user("artemis").password("artemis"));
             Receiver receiver = conn.openReceiver("test.bug.ulong")) {

            Delivery delivery = receiver.receive(10_000);
            Object body = delivery.message().body();
            System.out.println("Type: " + body.getClass().getName());
            System.out.println("Value: " + body);

            if (body instanceof Long && (Long)body < 0) {
                long v = (Long)body;
                System.out.printf("FAIL: got signed %d, should be unsigned %s%n",
                    v, Long.toUnsignedString(v));
            } else {
                System.out.println("PASS");
            }
        }
    }
}
