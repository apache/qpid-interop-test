/**
 * ProtonJ2 Bug: ListTypeEncoder NullPointerException on null-after-non-null
 *
 * AMQP lists MAY contain null elements, but ProtonJ2 crashes when encoding
 * a list with a null element following a non-null element.
 *
 * Tested with: protonj2-client 1.1.0
 * Requires: Artemis broker on localhost:5672 (user: artemis, pass: artemis)
 *
 * Build & run:
 *   mvn dependency:copy-dependencies  # or use the pom.xml below
 *   javac -cp target/dependency/* protonj2-list-null-npe.java
 *   java -cp .:target/dependency/* ProtonJ2ListNullNpe
 *
 * Expected: message sent successfully
 * Actual:   NullPointerException in ListTypeEncoder
 */

import org.apache.qpid.protonj2.client.*;
import java.util.*;

public class ProtonJ2ListNullNpe {
    public static void main(String[] args) throws Exception {
        try (Client client = Client.create();
             Connection conn = client.connect("localhost", 5672,
                 new ConnectionOptions().user("artemis").password("artemis"));
             Sender sender = conn.openSender("test.bug.list-null-npe")) {

            List<Object> body = new ArrayList<>();
            body.add("hello");
            body.add(null);

            Message<List<Object>> msg = Message.create(body);
            sender.send(msg);
            System.out.println("PASS: message sent");
        } catch (Exception e) {
            System.out.println("FAIL: " + e.getClass().getSimpleName() + ": " + e.getMessage());
            e.printStackTrace();
        }
    }
}
