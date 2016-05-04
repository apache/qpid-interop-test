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
package org.apache.qpid.interop_test.obj_util;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.ObjectInput;
import java.io.ObjectInputStream;
import java.io.Serializable;

public class BytesToJavaObj {
    String hexObjStr = null;
    Serializable obj = null;

    public BytesToJavaObj(String hexObjStr) {
        this.hexObjStr = hexObjStr;
    }

    public String run() {
        byte[] bytes = hexStrToByteArray(this.hexObjStr);
        this.obj = byteArrayToObject(bytes);
        if (this.obj != null) {
            return this.obj.getClass().getName() + ":" + this.obj.toString();
        }
        return "<null>";
    }

    protected Serializable byteArrayToObject(byte[] bytes) {
        ByteArrayInputStream bis = new ByteArrayInputStream(bytes);
        ObjectInput in = null;
        try {
            in = new ObjectInputStream(bis);
            return (Serializable) in.readObject();
        } catch (ClassNotFoundException e) {
            e.printStackTrace(System.out);
        } catch (IOException e) {
            e.printStackTrace(System.out);
        } finally {
            try {
                bis.close();
            } catch (IOException e) {} // ignore
            try {
                in.close();
            } catch (IOException e) {} // ignore
        }
        return null;
    }

    protected byte[] hexStrToByteArray(String hexStr) {
        int len = hexStr.length();
        byte[] data = new byte[len / 2];
        for(int i=0; i<len; i+=2) {
            data[i/2] = (byte)((Character.digit(hexStr.charAt(i), 16) << 4) + Character.digit(hexStr.charAt(i+1), 16));
        }
        return data;
    }

    // ========= main ==========

    public static void main(String[] args) {
        if (args.length != 1) {
            System.out.println("BytesToJavaObj: Incorrect argument count");
            System.out.println("BytesToJavaObj: Expected argument: \"<java_serialized_obj_str_hex>\"");
            System.exit(1);
        }
        BytesToJavaObj btjo = new BytesToJavaObj(args[0]);
        System.out.println(btjo.run());
    }
}
