Canonical source
================

.. combined-code-block:: objective-c

   .. literalizer-group:: objective-c

      .. code-block:: objective-c

         @interface NativeCounter : NSObject {
           NSInteger _count;
         }
         - (BOOL)accept:(NSString *)userId timestamp:(double)timestamp;
         - (NSInteger)count;
         @end
         @implementation NativeCounter
         - (BOOL)accept:(NSString *)userId timestamp:(double)timestamp {
           _count++;
           return [userId isEqualToString:@"user_1"] && timestamp == 100.0;
         }
         - (NSInteger)count {
           return _count;
         }
         @end
         static void checkResult(BOOL actual, NSArray *expected) {
           NSCAssert(actual == [expected[0] boolValue], @"wrong native result");
         }
         static void consumeObject(id value) {
           NSCAssert([value integerValue] == 42, @"wrong generic call value");
         }
         int main(void) {
           @autoreleasepool {

      .. literalizer:: data.json
         :language: objective-c
         :variable-name: rows
         :include-delimiters:
         :include-preamble:
         :pre-indent-level: 2

      .. literalizer-call:: scalar.json
         :language: objective-c
         :target-function: consumeObject
         :parameter-names: value
         :per-element:
         :pre-indent-level: 2

      .. literalizer-invocation:: no-args.json
         :language: objective-c
         :invocation-file: constructor.json
         :variable-name: counter
         :per-element:
         :include-preamble:
         :pre-indent-level: 2

      .. literalizer-invocation:: calls.json
         :language: objective-c
         :invocation-file: recipe.json
         :zip-file: expected.json
         :per-element:
         :include-preamble:
         :pre-indent-level: 2

      .. literalinclude:: prefix.m
         :language: objective-c

      .. literalizer:: data.json
         :language: objective-c
         :pre-indent-level: 3

      .. code-block:: objective-c

             ];
             NSCAssert([counter count] == 2, @"receiver identity changed");
             NSCAssert([rows[0][@"count"] integerValue] == 42, @"data changed");
             NSCAssert([entries isEqual:rows], @"inline data changed");
           }
           return 0;
         }
