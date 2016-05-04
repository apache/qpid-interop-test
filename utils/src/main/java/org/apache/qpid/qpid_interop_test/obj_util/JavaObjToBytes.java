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

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectOutput;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
//import java.util.Arrays;

public class JavaObjToBytes {
    String javaClassName = null;
    String ctorArgStr = null;
    Serializable obj = null;

    public JavaObjToBytes(String javaClassName, String ctorArgStr) {
        this.javaClassName = javaClassName;
        this.ctorArgStr = ctorArgStr;
    }

    public byte[] run() {
        createJavaObject();
        return serializeJavaOjbect();
    }

    protected void createJavaObject() {
        try {
            Class<?> c = Class.forName(this.javaClassName);
            if (this.javaClassName.compareTo("java.lang.Character") == 0) {
                Constructor ctor = c.getConstructor(char.class);
                if (this.ctorArgStr.length() == 1) {
                    // Use first character of string
                    obj = (Serializable)ctor.newInstance(this.ctorArgStr.charAt(0));
                } else if (this.ctorArgStr.length() == 4 || this.ctorArgStr.length() == 6) {
                    // Format '\xNN' or '\xNNNN'
                    obj = (Serializable)ctor.newInstance((char)Integer.parseInt(this.ctorArgStr.substring(2), 16));
                } else {
                    throw new Exception("JavaObjToBytes.createJavaObject() Malformed char string: \"" + this.ctorArgStr + "\"");
                }
            } else {
                // Use string constructor
                Constructor ctor = c.getConstructor(String.class);
                obj = (Serializable)ctor.newInstance(this.ctorArgStr);
            }
        }
        catch (ClassNotFoundException e) {
            e.printStackTrace(System.out);
        }
        catch (NoSuchMethodException e) {
            e.printStackTrace(System.out);
        }
        catch (InstantiationException e) {
            e.printStackTrace(System.out);
        }
        catch (IllegalAccessException e) {
            e.printStackTrace(System.out);
        }
        catch (InvocationTargetException e) {
            e.printStackTrace(System.out);
        }
        catch (Exception e) {
            e.printStackTrace(System.out);
        }
    }

    protected byte[] serializeJavaOjbect() {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        ObjectOutput out = null;
        try {
            out = new ObjectOutputStream(bos);
            out.writeObject(this.obj);
            return bos.toByteArray();
        } catch (IOException e) {
            e.printStackTrace(System.out);
        } finally {
            try {
                if (out != null) {
                    out.close();
                }
            } catch (IOException e) {} // ignore
            try {
                bos.close();
            } catch (IOException e) {} // ignore
        }
        return null;
    }

    // ========= main ==========

    public static void main(String[] args) {
        if (args.length != 1) {
            System.out.println("JavaObjToBytes: Incorrect argument count");
            System.out.println("JavaObjToBytes: Expected argument: \"<java_class_name>:<ctor_arg_str>\"");
            System.exit(1);
        }
        int colonIndex = args[0].indexOf(":");
        if (colonIndex < 0) {
            System.out.println("Error: Incorect argument format: " + args[0]);
            System.exit(-1);
        }
        String javaClassName = args[0].substring(0, colonIndex);
        String ctorArgStr = args[0].substring(colonIndex+1);
        JavaObjToBytes jotb = new JavaObjToBytes(javaClassName, ctorArgStr);
        byte[] bytes = jotb.run();
        System.out.println(args[0]);
        for (byte b: bytes) {
            System.out.print(String.format("%02x", b));
        }
        System.out.println();
    }
}

