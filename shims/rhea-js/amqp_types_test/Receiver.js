#!/usr/bin/env node
/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */

"use strict";

//Check if the environment is Node.js and if not log an error and exit.
if (typeof process !== 'object' || typeof require !== 'function') {
    console.error("Receiver.js should be run in Node.js");
    process.exit(-1);
}

var uuid = require("node-uuid");

var args = process.argv.slice(2);
if (args.length !== 4) {
    console.error("ERROR: Sender.js needs 4 arguments:");
    console.error(" 1. Broker address (ip-addr:port)");
    console.error(" 2. Queue name");
    console.error(" 3. AMQP type");
    console.error(" 4. Number of expected values");
    process.exit(-1);
}

function Receiver(brokerAddr, brokerPort, queueName, amqpType, numTestValues) {
    this.amqpType = amqpType;
    this.received = 0;
    this.expected = numTestValues;
    this.receivedValueList = [];
    this.container = require('rhea');

    this.container.connect({'host':brokerAddr, 'port':brokerPort, 'reconnect':false}).open_receiver(queueName);

    this.processMessage = function(msgBody) {
//        console.log("processMessage: amqpType=" + this.amqpType + "; msgBody=" + msgBody);
        switch(this.amqpType) {
        case "null": this.receivedValueList.push(this.decodeNull(msgBody)); break;
        case "boolean": this.receivedValueList.push(this.decodeBoolean(msgBody)); break;
        case "ubyte":
        case "ushort":
        case "uint":
        case "ulong":
        case "decimal32":
        case "decimal64":
        case "decimal128": this.receivedValueList.push(this.decodeUnsigned(msgBody)); break;
        case "timestamp": this.receivedValueList.push(this.decodeTimestamp(msgBody)); break;
        case "byte":
        case "short":
        case "int":
        case "long": this.receivedValueList.push(this.decodeSigned(msgBody)); break;
        case "float": this.receivedValueList.push(this.decodeFloat(msgBody)); break;
        case "double": this.receivedValueList.push(this.decodeDouble(msgBody)); break;
        case "char": this.receivedValueList.push(this.decodeChar(msgBody)); break;
        case "uuid": this.receivedValueList.push(this.decodeUuid(msgBody)); break;
        case "binary": this.receivedValueList.push(this.decodeBinary(msgBody)); break;
        case "string": this.receivedValueList.push(this.decodeString(msgBody)); break;
        case "symbol": this.receivedValueList.push(this.decodeSymbol(msgBody)); break;
        case "list":
        case "map":
        case "array": throw "Unsupported complex AMQP type: \"" + this.amqpType + "\"";
        default: throw "Unknown AMQP type: " + this.amqpType;
        }
    };

    this.decodeNull = function (msgBody) {
        return "None";
    };

    this.decodeBoolean = function(msgBody) {
        return msgBody ? "True" : "False";
    };

    this.decodeUnsigned = function(msgBody) {
        return "0x" +   msgBody.toString(Buffer.isBuffer(msgBody) ? 'hex' : 16);
    };

    this.decodeTimestamp = function(msgBody) {
        return "0x" + msgBody.getTime().toString(16);
    }

    this.decodeSigned = function(msgBody) {
        if (Buffer.isBuffer(msgBody)) {
            if (msgBody[0] & 0x80) { // sign bit set
                msgBody[0] &= 0x80;
                return "-0x" + msgBody.toString('hex');
            } else {
                return "0x" + msgBody.toString('hex');
            }
        } else {
            if (msgBody < 0) {
                return "-0x" + (-msgBody).toString(16);
            } else {
                return "0x" + msgBody.toString(16);
            }
        }
    };

    this.decodeFloat = function(msgBody) {
        // Buffer.writeFloatBE() does not support -NaN (ignores sign)
        var buf = new Buffer(4);
        buf.writeFloatBE(msgBody);
        return "0x" + buf.toString('hex');
    };

    this.decodeDouble = function(msgBody) {
        // Buffer.writeDoubleBE() does not support -NaN (ignores sign)
        var buf = new Buffer(8);
        buf.writeDoubleBE(msgBody);
        return "0x" + buf.toString('hex');
    };

    // UTF32BE char per AMQP spec
    this.decodeChar = function(msgBody) {
        if (msgBody >= 32 && msgBody <=126) { // printable single ASCII char
            return String.fromCharCode(msgBody);
        } else {
            return "0x" + msgBody.toString(16);
        }
    };

    this.decodeUuid = function(msgBody) {
        return uuid.unparse(msgBody);
    };

    this.decodeBinary = function(msgBody) {
        var buff = new Buffer(msgBody)
        return buff.toString('base64');
    };

    this.decodeString = function(msgBody) {
        return msgBody;
    };

    this.decodeSymbol = function(msgBody) {
        return msgBody;
    };

    this.buffer2HexString = function(buff, pad) {
        var hexStr = "";
        var first = true;
        for (var i = 0; i < buff.length; i++) {
            if (pad || buff[i] > 0) {
                hexStr += (pad || !first) ? ("0" + buff[i].toString(16)).substr(-2) : buff[i].toString(16);
                first = false;
            }
        }
        return hexStr;
    };

    this.printResult = function() {
        console.log(this.amqpType);
        console.log(JSON.stringify(this.receivedValueList));
    };

    this.container.on('message', function (context) {
        if (receiver.expected === 0 || receiver.received < receiver.expected) {
            receiver.processMessage(context.message.body);
            if (++receiver.received === receiver.expected) {
                context.receiver.detach();
                context.connection.close();
                receiver.printResult();
            }
        }
    });

    this.container.on('disconnected', function(context){
    	console.error('Unable to connet to broker')
    });
}

var colonPos = args[0].indexOf(":");
var receiver = new Receiver(args[0].slice(0, colonPos), args[0].slice(colonPos+1), args[1], args[2], parseInt(args[3], 10));
