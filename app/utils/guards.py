from guardrails import Guard
from guardrails.hub import NSFWText
import re


guard = Guard().use(
    NSFWText, threshold=0.9, validation_method="sentence", on_fail="exception"
)

# # Load the schema
# guard2 = Guard.for_rail("nsfw_guard.rail")


# # Test strings
# test_inputs = [
#     "hello, how are you?",         # should pass
#     "you are a bitch",             # should raise exception
#     "I love Pikachu",              # should raise exception
#     "this is a safe message",      # should pass
#     "pokemon is cool",             # should raise exception
# ]

# import traceback

# for text in test_inputs:
#     print(f"\nInput: {text}")
#     try:
#         result = guard2.validate(text)
#         print("✅ Passed:", result)
#     except Exception as e:
#         print("❌ Blocked:", e)
#         traceback.print_exc()