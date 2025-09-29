import sys
import os

print("--- sys.path ---")
for p in sys.path:
    print(p)

print("\n--- Current Working Directory ---")
print(os.getcwd())

print("\n--- Directory Listing ---")
print(os.listdir('.'))