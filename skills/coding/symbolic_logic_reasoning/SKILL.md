# Symbolic Logic Reasoning

## When to use this skill
Solve Symbolic Logic Reasoning (SLR) tasks, specifically formulating a Prolog rule to classify eastbound vs. westbound trains based on their composition.

## Approach
1. **Analyze Train Composition**: Review the ground facts (like `has_car`, `car_color`, `car_len`, `has_wall`) for positive (eastbound) and negative (westbound) examples.
2. **Find Mappings**: Locate a property or combination of properties that is true for all eastbound trains and false for all westbound trains.
3. **Formulate Prolog Rule**: Formulate the rule as `eastbound(T) :- Body.` (e.g. `eastbound(Train) :- has_car(Train, Car), car_len(Car, short).`).
4. **Minimize Body Literals**: Make the rule body as short and general as possible without sacrificing accuracy.

## Known constraints
- The rule must perfectly separate positive and negative examples.
- Must use only predefined predicates and constants.

## Examples
### Good rule pattern
`eastbound(Train):- has_car(Train, Car1), car_color(Car1, yellow).`
