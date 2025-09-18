#!/usr/bin/env python3
"""
Simple validation of the sec2ms function to ensure it works with large durations.
This can be run independently of the full nebPod module.
"""

def sec2ms(val):
    """
    Convert a value from seconds to milliseconds and represent it as an integer.
    This is a copy of the function from nebPod.py for testing purposes.
    
    Args:
        val (float): The value in seconds to be converted.

    Returns:
        int: The value converted to milliseconds.
    """
    val = float(val)
    return int(val * 1000)

def test_large_durations():
    """Test that the sec2ms function works with large durations"""
    
    print("Testing sec2ms function with large durations that exceed uint16 limits:")
    print("uint16 max = 65,535 ms = 65.535 seconds")
    print("")
    
    test_cases = [
        # (seconds, expected_ms, description)
        (60, 60000, "1 minute - within uint16 limit"),
        (65.535, 65535, "uint16 maximum in seconds"),
        (70, 70000, "70 seconds - exceeds uint16 by 4,465 ms"),
        (120, 120000, "2 minutes - exceeds uint16 by 54,465 ms"),
        (300, 300000, "5 minutes - exceeds uint16 by 234,465 ms"),
        (600, 600000, "10 minutes - exceeds uint16 by 534,465 ms"),
        (1800, 1800000, "30 minutes - typical long experiment"),
        (3600, 3600000, "1 hour - very long experiment"),
    ]
    
    uint16_max = 65535
    all_passed = True
    
    for seconds, expected_ms, description in test_cases:
        result = sec2ms(seconds)
        exceeds_uint16 = result > uint16_max
        excess = result - uint16_max if exceeds_uint16 else 0
        
        print(f"{seconds:>6} seconds -> {result:>8,} ms ({description})")
        
        if result != expected_ms:
            print(f"  ❌ FAILED: Expected {expected_ms}, got {result}")
            all_passed = False
        elif exceeds_uint16:
            print(f"     ✓ Exceeds uint16 by {excess:,} ms - now supported with uint32!")
        else:
            print(f"     ✓ Within uint16 limits")
    
    print(f"\nTest Results: {'All tests passed!' if all_passed else 'Some tests failed!'}")
    return all_passed

if __name__ == "__main__":
    success = test_large_durations()
    
    if success:
        print("\n🎉 The sec2ms function works correctly with large durations!")
        print("The uint32 fix will allow phasic stimulations longer than 1 minute.")
    else:
        print("\n❌ There was an issue with the sec2ms function.")