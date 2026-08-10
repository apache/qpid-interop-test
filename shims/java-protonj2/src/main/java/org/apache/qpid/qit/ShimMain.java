/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * QIT ProtonJ2 Shim - Main Entry Point
 */
package org.apache.qpid.qit;

public class ShimMain {
    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: shim <command> [options]");
            System.err.println("Commands: send, receive");
            System.exit(1);
        }

        String command = args[0];
        
        try {
            switch (command) {
                case "send":
                    Sender.main(args);
                    break;
                case "receive":
                    Receiver.main(args);
                    break;
                default:
                    System.err.println("Unknown command: " + command);
                    System.exit(1);
            }
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace(System.err);
            System.exit(1);
        }
    }
}
