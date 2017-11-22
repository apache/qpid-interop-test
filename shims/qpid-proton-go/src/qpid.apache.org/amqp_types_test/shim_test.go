/*
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
*/

// Quick self-contained sanity check that sender and receiver can pass data directly to each other
// Mostly useful for initial shim development. The testcases are pulled from the actual QIT test.

// $ GOPATH=/qpid-proton/proton-c/bindings/go/:/qpid-interop-test/shims/qpid-proton-go/ go test qpid.apache.org/amqp_types_test

package amqp_types_test_test

import (
	"encoding/json"
	"fmt"
	"log"
	"testing"

	"qpid.apache.org/amqp"

	. "qpid.apache.org/amqp_types_test"
)

func TestMessageDecodeEncode(t *testing.T) {
	for _, in := range [][]string{
		[]string{"string", `["aString"]`},
		[]string{"string", `["aString","secondString"]`},

		[]string{"null", `["None"]`},
		[]string{"boolean", `["True"]`},
		[]string{"ubyte", `["0xff"]`},
		[]string{"ushort", `["0xffff"]`},
		[]string{"uint", `["0xffffffff"]`},
		[]string{"ulong", `["0xffffffffffffffff"]`},
		[]string{"byte", `["-0x80"]`},
		[]string{"short", `["-0x8000"]`},
		[]string{"int", `["-0x80000000"]`},
		[]string{"long", `["-0x8000000000000000"]`},

		[]string{"float", `["0xff7fffff"]`},
		[]string{"float", `["3.14"]`},
		[]string{"double", `["0xffefffffffffffff"]`},
		[]string{"double", `["3.14"]`},

		//[]string{"decimal32", `["0xff7fffff"]`},
		//[]string{"decimal64", `["0xffefffffffffffff"]`},
		//[]string{"decimal128", `["0xff0102030405060708090a0b0c0d0e0f"]`},
		[]string{"char", `["G"]`},
		[]string{"char", `["0x16b5"]`},
		[]string{"timestamp", `["0xdc6acfac00"]`}, // in milliseconds since 1970
		[]string{"timestamp", `["0x15fe0dd4a94"]`},
		[]string{"uuid", `["00010203-0405-0607-0809-0a0b0c0d0e0f"]`},
		[]string{"binary", `["\\x01\\x02\\x03\\x04\\x05abcde\\x80\\x81\\xfe\\xff"]`},
		[]string{"string", `["Hello, World!"]`},
		[]string{"symbol", `["myDomain.123"]`},
		[]string{"binary", `["someData"]`},

		[]string{"string", `[]`},
		[]string{"list", `[[]]`},
		[]string{"map", `[{}]`},

		[]string{"list", `[[[],[]]]`},
		[]string{"list", `[["string:v"]]`},
		[]string{"map", `[{"string:k":"string:v"}]`},
		[]string{"map", `[{"string:k":[]}]`},
		[]string{"map", `[{"string:k":{"string:k":"string:v"}}]`},

		[]string{"list", `[[[],[[],[[],[],[]],[]],[]]]`},
		[]string{"list", `[["ubyte:1"]]`},
		[]string{"list", `[["int:-2"]]`},
		[]string{"list", `[["float:3.14"]]`},
		[]string{"list", `[["string:a"]]`},
		[]string{"list", `[["ulong:12345"]]`},
		[]string{"list", `[["short:-2500"]]`},
		[]string{"list", `[["symbol:a.b.c"]]`},
		[]string{"list", `[["none:"]]`},
		//[]string{"list", `[["none"]]`},  // FIXME: which none is correct?
		[]string{"list", `[["boolean:True"]]`},
		[]string{"list", `[["long:1234"]]`},
		[]string{"list", `[["char:A"]]`},

		[]string{"map", `[{"string:one":"ubyte:1"}]`},
		//[]string{"map", `[{["string:AAA","ushort:5951"]:"string:list value"}]"]`},
		[]string{"map", `[{"string:None":"none:"}]`},
		[]string{"map", `[{"none:":"string:None"}]`},
	} {
		log.Println(in) // useful for debugging
		through := make([]interface{}, 0)
		var j []interface{}
		err := json.Unmarshal([]byte(in[1]), &j)
		Must(err)
		for _, jj := range j {
			Must(err)
			result := Parse(in[0], jj)

			m := amqp.NewMessage()
			m.Marshal(result)

			type_, value := Load(in[0], m.Body())
			if type_ != in[0] {
				t.Errorf("Detected type %v does not match expected type '%v'", type_, in[0])
			}
			through = append(through, value)
		}
		fmt.Printf("%+v\n", through) // useful for debugging
		result := String(through)
		if in[1] != result {
			t.Errorf("Expected `%s`, actual `%s`.", in[1], result)
		}
	}
}
