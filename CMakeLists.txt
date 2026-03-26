cmake_minimum_required(VERSION 3.10)

project(consistentHash)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED True)



add_library(consistentHash_lib
    ConsistentHash.cpp
)


# 主可执行文件
add_executable(consistentHash main.cpp)

target_link_libraries(consistentHash consistentHash_lib)
