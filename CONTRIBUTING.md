# Contributing

Contributions are welcome, especially:

- adversarial fixtures that expose false confidence;
- narrowly specified rules with clear false-positive tradeoffs;
- documentation that makes the non-goals harder to misunderstand;
- tests that preserve the scope notice and `not_evaluated` fields.

A proposed rule should include:

1. the failure mode it catches;
2. the exact declared inputs it relies on;
3. expected `READY`, `REVIEW`, or `BLOCK` behavior;
4. at least one positive and one negative fixture;
5. known exceptions or false positives.

Do not add rules that pretend to verify facts the harness cannot observe.
