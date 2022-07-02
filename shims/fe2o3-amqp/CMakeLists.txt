# Building fe2o3-amqp shim requires
# * cargo
#
# Define -DBUILD_FE2O3_AMQP=ON (or OFF) at the cmake command line
# to force a build or not.

project(qpid-interop-test-fe2o3-amqp-shims)

cmake_minimum_required(VERSION 3.16.3 FATAL_ERROR)

set(build_fe2o3_amqp_default ON)
set(RUST_TOOLCHAIN stable)

# Check prerequisites
# 1. Find cargo
find_program(CARGO cargo)
if (CARGO STREQUAL "CARGO-NOTFOUND")
    message(STATUS "cargo not found")
    set(build_fe2o3_amqp_default OFF)
endif()

# Set option that controls the build process
option(BUILD_FE2O3_AMQP "Build fe2o3-amqp shim" ${build_fe2o3_amqp_default})
message(STATUS "BUILD_FE2O3_AMQP = ${BUILD_FE2O3_AMQP}")

if (BUILD_FE2O3_AMQP)
    add_subdirectory(amqp_types_test)
endif()

