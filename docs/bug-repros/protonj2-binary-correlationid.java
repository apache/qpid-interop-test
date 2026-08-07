/**
 * ProtonJ2 Bug: Cannot send binary correlation IDs
 *
 * AMQP spec allows correlation-id to be: message-id-ulong, message-id-uuid,
 * message-id-binary, or message-id-string. ProtonJ2 rejects byte[] as a
 * correlation ID value.
 *
 * Also: when receiving a binary correlation ID (sent by another client),
 * ProtonJ2 decodes it as a UTF-8 string instead of preserving the binary.
 *
 * Tested with: protonj2-client 1.1.0
 */

import org.apache.qpid.protonj2.client.*;

public class ProtonJ2BinaryCorrelationId {
    public static void main(String[] args) throws Exception {
        try (Client client = Client.create();
             Connection conn = client.connect("localhost", 5672,
                 new ConnectionOptions().user("artemis").password("artemis"));
             Sender sender = conn.openSender("test.bug.binary-corrid")) {

            Message<String> msg = Message.create("test");
            try {
                msg.correlationId(new byte[] {0x01, 0x02, 0x03});
                sender.send(msg);
                System.out.println("PASS: binary correlation ID accepted");
            } catch (Exception e) {
                System.out.println("FAIL: " + e.getClass().getSimpleName() + ": " + e.getMessage());
            }
        }
    }
}
