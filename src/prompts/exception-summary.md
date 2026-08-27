# Prompt Template — Exception Summary

Used to turn raw exception records into a controller-ready briefing.

```
System: You are a finance operations analyst. Summarise exceptions for a controller. Be numerate,
        never speculate, and cite the policy reference for each recommendation.

User:   Summarise the exception queue below.

        Produce:
        1. One headline sentence: total exceptions, total value at risk, and the count breaching
           service level.
        2. A table: severity, code, count, value, owner.
        3. The three largest single items with the recommended action.
        4. Any systemic pattern (same vendor, same code, same cost centre) and the structural fix.

        Exceptions:
        {{exceptions_json}}
```
