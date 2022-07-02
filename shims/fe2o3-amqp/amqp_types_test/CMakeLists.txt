project(qpid-interop-test-fe2o3-amqp-shims-amqp-types-test)

cmake_minimum_required(VERSION 3.16.3 FATAL_ERROR)

set(CARGO_BUILD_ROOT ${CMAKE_CURRENT_BINARY_DIR})
set(MAKE_INSTALL_ROOT
    ${CMAKE_INSTALL_PREFIX}/libexec/qpid_interop_test/shims/fe2o3-amqp/amqp_types_test)

add_custom_target(
    fe2o3_amqp_amqp_types_test_Sender
    ALL
    COMMAND cargo +${RUST_TOOLCHAIN} install --path ./ --target-dir
    ${CARGO_BUILD_ROOT}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT Build fe2o3-amqp sender
)

install(DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/release/"
    DESTINATION "${MAKE_INSTALL_ROOT}")
