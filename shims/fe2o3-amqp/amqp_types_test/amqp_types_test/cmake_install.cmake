# Install script for directory: /mnt/d/Developments/workspace_python/qpid-interop-test/shims/fe2o3-amqp/amqp_types_test

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/usr/local")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  EXECUTE_PROCESS (
        COMMAND cargo +stable install --path ./ --target-dir /mnt/d/Developments/workspace_python/qpid-interop-test/shims/fe2o3-amqp/amqp_types_test/amqp_types_test --root /usr/local/libexec/qpid_interop_test/shims/fe2o3-amqp/amqp_types_test
        COMMAND chmod +x /usr/local/libexec/qpid_interop_test/shims/fe2o3-amqp/amqp_types_test/bin/sender
        /usr/local/libexec/qpid_interop_test/shims/fe2o3-amqp/amqp_types_test/bin/receiver
        WORKING_DIRECTORY /mnt/d/Developments/workspace_python/qpid-interop-test/shims/fe2o3-amqp/amqp_types_test
        )
endif()

