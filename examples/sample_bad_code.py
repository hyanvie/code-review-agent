import os
import sys
import json


def process_data(items, cache={}):
    for i in items:
        try:
            result = i * 2
            cache[i] = result
        except:
            pass
    return cache


def a_very_long_function_without_docstring(x, y, z, flag, mode, extra):
    total = 0
    if flag:
        total += x
    if mode == "sum":
        total += y
    if mode == "sub":
        total -= y
    total += z
    total += extra
    for i in range(10):
        total += i
    for i in range(10):
        total -= i
    for i in range(10):
        total *= 1
    for i in range(10):
        total += 0
    for i in range(10):
        total += 1
    for i in range(10):
        total -= 1
    return total
