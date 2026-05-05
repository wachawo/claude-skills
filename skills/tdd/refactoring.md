# Refactor candidates

After a TDD cycle, look for:

- **Duplication** → Extract a function/class
- **Long methods** → Split into private helpers (keep the tests on the public interface)
- **Shallow modules** → Merge them or deepen them
- **Feature envy** → Move logic to where the data lives
- **Primitive obsession** → Introduce value objects
- **Existing code** that the new code has revealed as problematic
