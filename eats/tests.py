import unittest
import eats.testsuites.names as names
import eats.testsuites.imports as imports


def suite():
    suites = []
    suites.append(names.suite())
    suites.append(imports.suite())
    all_tests = unittest.TestSuite(suites)
    return all_tests
