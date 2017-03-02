package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"

	"qpid.apache.org/amqp"
	"qpid.apache.org/electron"

	"qpid.apache.org/amqp_types_test"
	"strings"
)

func printSenderUsage(w io.Writer) {
	usage := `
 * --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: AMQP type
 *       4: Test value(s) as JSON string`

	fmt.Fprintln(w, strings.TrimLeft(usage, "\n"))
}

func main() {
	f, err := os.Create("/lastlog.txt")
	if err != nil {
		log.Fatal(err)
	}
	fmt.Fprint(f, os.Args)

	if len(os.Args) != 1+4 {
		printSenderUsage(os.Stderr)
		os.Exit(1)
	}

	//Trace.TraceLevel = TraceLevel.Frame | TraceLevel.Verbose;
	//Trace.TraceListener = (f, a) => Console.WriteLine(DateTime.Now.ToString("[hh:mm:ss.fff]") + " " + string.Format(f, a));

	err = sender(os.Args[1], os.Args[2], os.Args[3], os.Args[4])
	if err != nil {
		fmt.Fprintf(os.Stderr, "%v", err)
		os.Exit(1)
	}
}

func sender(addr, queue, type_, value string) error {
	var values []interface{}
	err := json.Unmarshal([]byte(value), &values)
	if err != nil {
		log.Fatal(err)
	}

	url, err := amqp.ParseURL(addr)
	amqp_types_test.Must(err)
	url.Path = queue
	c, err := amqp_types_test.Connect(url)
	amqp_types_test.Must(err)

	options := make([]electron.LinkOption, 0)
	options = append(options, electron.Target(url.Path))
	s, err := c.Sender(options...)
	amqp_types_test.Must(err)

	for _, v := range values {
		m := amqp.NewMessage()
		m.Marshal(amqp_types_test.Parse(type_, v))
		outcome := s.SendSync(m)
		if outcome.Error != nil {
			log.Fatal(outcome.Error)
		}
		//if glog.V(2) {
		//	glog.Info(outcome.Error)
		//	glog.Info(outcome.Status)
		//	glog.Info(outcome.Value)
		//}
		//wait(senderControlOptions.Count, senderReceiverControlOptions.Duration)
		//
		//<-time.After(time.Duration(controlOptions.CloseSleep) * time.Second)
	}
	c.Close(nil)

	/*
	 List<Message> messagesToSend = new List<Message>();

	            // Deserialize the json message list
	            JavaScriptSerializer jss = new JavaScriptSerializer();
	            var itMsgs = jss.Deserialize<dynamic>(jsonMessages);
	            //if (!(itMsgs is Array))
	            //    throw new ApplicationException(String.Format(
	            //        "Messages are not formatted as a json list: {0}, but as type: {1}", jsonMessages, itMsgs.GetType().Name));

	            // Generate messages
	            foreach (object itMsg in itMsgs)
	            {
	                MessageValue mv = new MessageValue(amqpType, itMsg);
	                mv.Encode();
	                messagesToSend.Add(mv.ToMessage());
	            }

	            // Send the messages
	            ManualResetEvent senderAttached = new ManualResetEvent(false);
	            OnAttached onSenderAttached = (l, a) => { senderAttached.Set(); };
	            Address address = new Address(string.Format("amqp://{0}", brokerUrl));
	            Connection connection = new Connection(address);
	            Session session = new Session(connection);
	            SenderLink sender = new SenderLink(session,
	                                               "Lite-amqp-types-test-sender",
	                                               new Target() { Address = queueName },
	                                               onSenderAttached);
	            if (senderAttached.WaitOne(10000))
	            {
	                foreach (Message message in messagesToSend)
	                {
	                    sender.Send(message);
	                }
	            }
	            else
	            {
	                throw new ApplicationException(string.Format(
	                    "Time out attaching to test broker {0} queue {1}", brokerUrl, queueName));
	            }

	            sender.Close();
	            session.Close();
	            connection.Close();
	        }
	*/
	return nil
}
