#!/usr/bin/env python3
"""
Test script to compare V2 (sync) vs V3 (async) performance
Tests parallel processing capabilities with mock calls
"""

import asyncio
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

def log_test(msg):
    """Test logging with timestamp"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[TEST {timestamp}] {msg}")

def simulate_sync_call_processing(call_id, delay_seconds=2):
    """Simulate synchronous call processing (like V2)"""
    log_test(f"🔄 Sync processing call {call_id}")
    
    # Simulate API calls
    time.sleep(0.5)  # Google Drive fetch
    time.sleep(delay_seconds)  # AI analysis (variable)
    time.sleep(0.3)  # Salesforce update
    time.sleep(0.2)  # Slack notification
    
    log_test(f"✅ Sync completed call {call_id}")
    return f"call_{call_id}_result"

async def simulate_async_call_processing(call_id, delay_seconds=2):
    """Simulate asynchronous call processing (like V3)"""
    log_test(f"🔄 Async processing call {call_id}")
    
    # Simulate async API calls
    await asyncio.sleep(0.5)  # Google Drive fetch
    await asyncio.sleep(delay_seconds)  # AI analysis (variable)  
    await asyncio.sleep(0.3)  # Salesforce update
    await asyncio.sleep(0.2)  # Slack notification
    
    log_test(f"✅ Async completed call {call_id}")
    return f"call_{call_id}_result"

def test_sync_processing(num_calls=5):
    """Test synchronous processing (V2 style)"""
    log_test(f"🐌 Starting SYNC test with {num_calls} calls")
    start_time = time.time()
    
    results = []
    for i in range(1, num_calls + 1):
        # Vary AI processing time (1-4 seconds)
        ai_delay = 1 + (i % 4)
        result = simulate_sync_call_processing(i, ai_delay)
        results.append(result)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    log_test(f"🐌 SYNC Results:")
    log_test(f"   ⏱️ Total time: {total_time:.2f} seconds")
    log_test(f"   📈 Throughput: {(num_calls / total_time * 60):.1f} calls/minute")
    log_test(f"   ✅ Processed: {len(results)}")
    
    return {
        'method': 'sync',
        'total_time': total_time,
        'calls_processed': len(results),
        'calls_per_minute': num_calls / total_time * 60
    }

async def test_async_processing(num_calls=5, max_concurrent=3):
    """Test asynchronous processing (V3 style)"""
    log_test(f"⚡ Starting ASYNC test with {num_calls} calls (max {max_concurrent} concurrent)")
    start_time = time.time()
    
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(call_id):
        async with semaphore:
            # Vary AI processing time (1-4 seconds)
            ai_delay = 1 + (call_id % 4)
            return await simulate_async_call_processing(call_id, ai_delay)
    
    # Process all calls concurrently
    tasks = [process_with_semaphore(i) for i in range(1, num_calls + 1)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    log_test(f"⚡ ASYNC Results:")
    log_test(f"   ⏱️ Total time: {total_time:.2f} seconds")
    log_test(f"   📈 Throughput: {(num_calls / total_time * 60):.1f} calls/minute")
    log_test(f"   ✅ Processed: {len(results)}")
    
    return {
        'method': 'async',
        'total_time': total_time,
        'calls_processed': len(results),
        'calls_per_minute': num_calls / total_time * 60
    }

async def test_error_isolation(num_calls=5):
    """Test error isolation in async processing"""
    log_test(f"🚨 Testing error isolation with {num_calls} calls")
    
    async def process_call_with_errors(call_id):
        try:
            if call_id == 3:  # Simulate error in call 3
                await asyncio.sleep(0.5)
                raise Exception(f"Simulated error in call {call_id}")
            
            await asyncio.sleep(1 + call_id * 0.2)  # Variable processing time
            return f"success_call_{call_id}"
            
        except Exception as e:
            log_test(f"❌ Error in call {call_id}: {str(e)}")
            return f"error_call_{call_id}"
    
    start_time = time.time()
    
    # Process with error handling
    results = await asyncio.gather(*[
        process_call_with_errors(i) for i in range(1, num_calls + 1)
    ], return_exceptions=True)
    
    end_time = time.time()
    
    successes = [r for r in results if isinstance(r, str) and 'success' in r]
    errors = [r for r in results if isinstance(r, str) and 'error' in r]
    exceptions = [r for r in results if isinstance(r, Exception)]
    
    log_test(f"🚨 Error Isolation Results:")
    log_test(f"   ⏱️ Total time: {end_time - start_time:.2f} seconds")
    log_test(f"   ✅ Successes: {len(successes)}")
    log_test(f"   ❌ Handled errors: {len(errors)}")
    log_test(f"   🚨 Exceptions: {len(exceptions)}")

def test_real_google_drive_calls():
    """Test with actual Google Drive calls (requires .env setup)"""
    log_test("📁 Testing with real Google Drive calls")
    
    try:
        # Import V3 functions
        from V3_ASYNC_PRODUCTION import get_enhanced_google_drive_calls
        
        calls, status = get_enhanced_google_drive_calls()
        log_test(f"📁 {status}")
        
        if calls:
            log_test(f"📋 Sample calls found:")
            for i, call in enumerate(calls[:3]):  # Show first 3
                log_test(f"   {i+1}. {call['title'][:50]}...")
        
        return len(calls)
        
    except Exception as e:
        log_test(f"❌ Error testing real calls: {str(e)}")
        return 0

async def run_performance_comparison():
    """Run comprehensive performance comparison"""
    log_test("🏁 Starting Performance Comparison: V2 Sync vs V3 Async")
    log_test("=" * 60)
    
    # Test scenarios
    scenarios = [
        {'calls': 3, 'name': 'Light Load'},
        {'calls': 5, 'name': 'Medium Load'}, 
        {'calls': 10, 'name': 'Heavy Load'}
    ]
    
    results = []
    
    for scenario in scenarios:
        num_calls = scenario['calls']
        name = scenario['name']
        
        log_test(f"\n📊 Testing {name} ({num_calls} calls)")
        log_test("-" * 40)
        
        # Test sync version
        sync_result = test_sync_processing(num_calls)
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Test async version  
        async_result = await test_async_processing(num_calls, max_concurrent=3)
        
        # Calculate improvement
        improvement = sync_result['calls_per_minute'] / async_result['calls_per_minute'] if async_result['calls_per_minute'] > 0 else 0
        time_savings = sync_result['total_time'] - async_result['total_time']
        
        log_test(f"\n📈 {name} Summary:")
        log_test(f"   🐌 Sync: {sync_result['total_time']:.1f}s, {sync_result['calls_per_minute']:.1f} calls/min")
        log_test(f"   ⚡ Async: {async_result['total_time']:.1f}s, {async_result['calls_per_minute']:.1f} calls/min")
        log_test(f"   🚀 Improvement: {improvement:.1f}x faster, saves {time_savings:.1f} seconds")
        
        results.append({
            'scenario': name,
            'sync': sync_result,
            'async': async_result,
            'improvement': improvement,
            'time_savings': time_savings
        })
    
    # Test error isolation
    log_test(f"\n🚨 Error Isolation Test")
    log_test("-" * 40)
    await test_error_isolation(5)
    
    # Test with real data
    log_test(f"\n📁 Real Data Test")
    log_test("-" * 40)
    real_calls_count = test_real_google_drive_calls()
    
    # Final summary
    log_test(f"\n🏆 FINAL RESULTS")
    log_test("=" * 60)
    
    for result in results:
        scenario = result['scenario']
        improvement = result['improvement']
        savings = result['time_savings']
        
        log_test(f"📊 {scenario}: {improvement:.1f}x faster, saves {savings:.1f}s")
    
    avg_improvement = sum(r['improvement'] for r in results) / len(results)
    log_test(f"\n🎯 Average Performance Improvement: {avg_improvement:.1f}x")
    log_test(f"📁 Real calls available for testing: {real_calls_count}")
    
    # Recommendations
    log_test(f"\n💡 RECOMMENDATIONS:")
    if avg_improvement > 2:
        log_test("   ✅ Async upgrade provides significant performance benefits")
        log_test("   🚀 Recommended for production deployment")
    else:
        log_test("   ⚠️ Performance gains are modest")
        log_test("   🤔 Consider overhead vs benefits for your use case")

if __name__ == "__main__":
    # Run the performance comparison
    asyncio.run(run_performance_comparison())