/**
 * ProtonJ2 Bug: AMQP timestamp decoded as java.lang.Long instead of Date
 *
 * When receiving a message with an AMQP timestamp body, ProtonJ2 returns
 * a Long (raw milliseconds) instead of java.util.Date, losing the type
 * information. The receiver cannot distinguish a timestamp from a long.
 *
 * Tested with: protonj2-client 1.1.0
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
 *   Container(S('amqp://artemis:artemis@localhost:5672/test.bug.timestamp')).run()
 *   "
 *
 * Expected: java.util.Date
 * Actual:   java.lang.Long
 */

import org.apache.qpid.protonj2.client.*;

public class ProtonJ2TimestampType {
    public static void main(String[] args) throws Exception {
        try (Client client = Client.create();
             Connection conn = client.connect("localhost", 5672,
                 new ConnectionOptions().user("artemis").password("artemis"));
             Receiver receiver = conn.openReceiver("test.bug.timestamp")) {

            Delivery delivery = receiver.receive(10_000);
            Object body = delivery.message().body();
            String typeName = body.getClass().getName();
            System.out.println("Type: " + typeName);
            System.out.println("Value: " + body);

            if (body instanceof java.util.Date) {
                System.out.println("PASS: received as Date");
            } else {
                System.out.println("FAIL: expected java.util.Date, got " + typeName);
            }
        }
    }
}
