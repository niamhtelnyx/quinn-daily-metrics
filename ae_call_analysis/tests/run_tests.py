#!/usr/bin/env python3
"""
Test runner for AE Call Intelligence System unit tests
"""

import unittest
import sys
import os
import time
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def discover_and_run_tests():
    """Discover and run all unit tests"""
    
    print("🧪 AE CALL INTELLIGENCE - UNIT TEST SUITE")
    print("=" * 60)
    print()
    
    # Discover all tests in the tests directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    loader = unittest.TestLoader()
    start_time = time.time()
    
    # Create test suite
    suite = loader.discover(test_dir, pattern='test_*.py')
    
    # Custom test runner for better output
    class CustomTextTestResult(unittest.TextTestResult):
        def __init__(self, stream, descriptions, verbosity):
            super().__init__(stream, descriptions, verbosity)
            self.test_results = []
            
        def addSuccess(self, test):
            super().addSuccess(test)
            self.test_results.append(('PASS', test))
            
        def addError(self, test, err):
            super().addError(test, err)
            self.test_results.append(('ERROR', test, err))
            
        def addFailure(self, test, err):
            super().addFailure(test, err)
            self.test_results.append(('FAIL', test, err))
            
        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            self.test_results.append(('SKIP', test, reason))
    
    class CustomTestRunner(unittest.TextTestRunner):
        def _makeResult(self):
            return CustomTextTestResult(self.stream, self.descriptions, self.verbosity)
    
    # Run tests with custom runner
    runner = CustomTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    end_time = time.time()
    
    # Print detailed summary
    print("\n" + "=" * 60)
    print("🎯 TEST EXECUTION SUMMARY")
    print("=" * 60)
    
    # Count tests by module
    module_stats = {}
    for test_result in result._makeResult().test_results if hasattr(result, '_makeResult') else []:
        if len(test_result) >= 2:
            test_name = str(test_result[1])
            module_name = test_name.split('.')[0].replace('test_', '')
            if module_name not in module_stats:
                module_stats[module_name] = {'pass': 0, 'fail': 0, 'error': 0, 'skip': 0}
            module_stats[module_name][test_result[0].lower()] += 1
    
    print(f"📊 Tests Run: {result.testsRun}")
    print(f"⏱️ Duration: {end_time - start_time:.2f} seconds")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    
    if result.failures:
        print(f"❌ Failed: {len(result.failures)}")
    if result.errors:
        print(f"💥 Errors: {len(result.errors)}")
    if result.skipped:
        print(f"⏭️ Skipped: {len(result.skipped)}")
    
    print()
    
    # Module breakdown
    if module_stats:
        print("📋 MODULE BREAKDOWN:")
        for module, stats in module_stats.items():
            total = sum(stats.values())
            passed = stats.get('pass', 0)
            print(f"  {module}: {passed}/{total} passed")
    
    # Show failures and errors
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  • {test}")
            print(f"    {traceback.split(chr(10))[-2] if chr(10) in traceback else traceback}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  • {test}")
            print(f"    {traceback.split(chr(10))[-2] if chr(10) in traceback else traceback}")
    
    # Overall status
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED! System is ready for production.")
    else:
        print("⚠️ Some tests failed. Review issues before deployment.")
        
        # Suggest fixes
        if result.failures or result.errors:
            print("\n💡 SUGGESTED ACTIONS:")
            print("  • Check environment variables and configuration")
            print("  • Verify all dependencies are installed")
            print("  • Run individual test modules to isolate issues")
            print("  • Review error messages for specific guidance")
    
    print("=" * 60)
    
    return result.wasSuccessful()

def run_single_module(module_name):
    """Run tests for a single module"""
    print(f"🧪 RUNNING TESTS FOR: {module_name}")
    print("=" * 40)
    
    try:
        # Load the specific test module
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(f'test_{module_name}')
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
        
    except Exception as e:
        print(f"❌ Error running tests for {module_name}: {e}")
        return False

def main():
    """Main test runner entry point"""
    if len(sys.argv) > 1:
        # Run specific module
        module_name = sys.argv[1]
        success = run_single_module(module_name)
    else:
        # Run all tests
        success = discover_and_run_tests()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()