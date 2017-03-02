package main

import (
	"fmt"
	"io"
	"log"
	"os"
	"strconv"
	"time"

	"qpid.apache.org/amqp"
	"qpid.apache.org/electron"

	"qpid.apache.org/amqp_types_test"
	"strings"
)

func printReceiverUsage(w io.Writer) {
	usage := `
 * --- main ---
 * Args: 1: Broker address (ip-addr:port)
 *       2: Queue name
 *       3: QPIDIT AMQP type name of expected message body values
 *       4: Expected number of test values to receive`

	fmt.Fprintln(w, strings.TrimLeft(usage, "\n"))
}

func main() {
	//fmt.Println(os.Args)
	//return
	if len(os.Args) != 1+4 {
		printReceiverUsage(os.Stderr)
		os.Exit(1)
	}

	//Trace.TraceLevel = TraceLevel.Frame | TraceLevel.Verbose;
	//Trace.TraceListener = (f, a) => Console.WriteLine(DateTime.Now.ToString("[hh:mm:ss.fff]") + " " + string.Format(f, a));
	count, err := strconv.Atoi(os.Args[4])
	if err != nil {
		fmt.Fprintf(os.Stderr, "Go Receiver error: %v", err)
		os.Exit(1)
	}
	_, err = receive(os.Args[1], os.Args[2], os.Args[3], count)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Go Receiver error: %v", err)
		os.Exit(1)
	}
	//fmt.Printf("%s\n", os.Args[2])
	//fmt.Printf("%v", values)
}

func receive(addr, queue, type_ string, count int) ([]string, error) {
	url, err := amqp.ParseURL(addr)
	amqp_types_test.Must(err)
	url.Path = queue
	c, err := amqp_types_test.Connect(url)
	amqp_types_test.Must(err)

	options := make([]electron.LinkOption, 0)
	options = append(options, electron.Source(url.Path))
	r, err := c.Receiver(options...)
	amqp_types_test.Must(err)

	data := make([]interface{}, 0)
	for i := 0; i < count; i++ {
		m, err := r.ReceiveTimeout(10 * time.Second) // C# uses --timeout value here
		switch err {
		case nil:
			receivedType, value := amqp_types_test.Load(type_, m.Message.Body())
			if type_ != receivedType {
				log.Fatalf("Receiver got value of type %s while %s was expected", receivedType, type_)
			}
			data = append(data, value)
			err = m.Accept()
			amqp_types_test.Must(err)
			//case electron.Timeout:
		default:
			log.Fatalf("receiving failed %v", err)
		}
	}

	fmt.Printf("%s\n%s\n", type_, amqp_types_test.String(data))
	c.Close(nil)
	return []string{""}, nil
}
