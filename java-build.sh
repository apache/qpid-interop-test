#!/bin/bash

# JARS
#JMS_API=${HOME}/.m2/repository/org/apache/geronimo/specs/geronimo-jms_1.1_spec/1.1.1/geronimo-jms_1.1_spec-1.1.1.jar:${HOME}/.m2/repository/org/apache/qpid/qpid-jms-client/0.4.0-SNAPSHOT/qpid-jms-client-0.4.0-SNAPSHOT.jar
#JSON_API=../../jars/javax.json-api-1.0.jar
#CLASSPATH=${JMS_API}:${JSON_API}
CLASSPATH=

BASEPATH=org/apache/qpid/interop_test/obj_util
SRCPATH=src/main/java/${BASEPATH}
TARGETPATH=target

mkdir -p ${TARGETPATH}/classes
javac -cp ${CLASSPATH} -Xlint:unchecked -d ${TARGETPATH}/classes ${SRCPATH}/JavaObjToBytes.java ${SRCPATH}/BytesToJavaObj.java
jar -cf ${TARGETPATH}/JavaObjUtils.jar -C ${TARGETPATH}/classes ${BASEPATH}/JavaObjToBytes.class -C ${TARGETPATH}/classes ${BASEPATH}/BytesToJavaObj.class
