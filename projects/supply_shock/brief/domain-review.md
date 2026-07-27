# Domain review — Supply Shock

**Review date:** 2026-07-27  
**Reviewer:** AI source-and-model review; independent economics review remains
recommended before public sign-off.

## Claims checked

1. Supply is a relationship between prices and quantities supplied, whereas
   quantity supplied is a point on that relationship.
2. A non-price change such as natural conditions or productive capacity can
   shift the supply curve.
3. Market equilibrium is the intersection where quantity demanded equals
   quantity supplied.
4. With demand fixed, a negative supply shift in the disclosed linear model
   produces a higher equilibrium price and lower equilibrium quantity.
5. A single-product partial-equilibrium result is not an economy-wide
   inflation claim.

## Evidence

- OpenStax, *Principles of Economics 3e*, §3.1, demand, supply, and market
  equilibrium:
  https://openstax.org/books/principles-economics-3e/pages/3-1-demand-supply-and-equilibrium-in-markets-for-goods-and-services
- OpenStax, *Principles of Economics 3e*, Chapter 3 key concepts, including
  natural conditions as supply shifters and the four-step equilibrium method:
  https://openstax.org/books/principles-economics-3e/pages/3-key-concepts-and-summary
- OpenStax, *Principles of Economics 3e*, §24.3, capacity/input shocks and the
  distinction between product-market and aggregate-supply models:
  https://openstax.org/books/principles-economics-3e/pages/24-3-shifts-in-aggregate-supply

## Deterministic checks

- Baseline: `P=100−Q` and `P=Q+20`, giving `P=60`, `Q=40`.
- Shock: `P=100−Q` and `P=Q+40`, giving `P=70`, `Q=30`.
- Demand-adaptation snapshot: `P=90−Q` and `P=Q+40`, giving `P=65`,
  `Q=25`.
- Each displayed market curve contains 81 deterministic samples.
- The three illustrative price paths share the same baseline and immediate
  shock before diverging.

## Assumptions and simplifications

- The example is a fictional single-product, static linear teaching model.
- Demand is held fixed during the initial supply-shift comparison.
- Prices and quantities are dimensionless illustrative values, not measured
  forecasts.
- Adjustment paths are designed scenarios, not estimated time series.
- Inventories, expectations, policy, substitution detail, market power,
  welfare, and distributional effects are not modeled.

## Unresolved review items

- Obtain independent economics review before final domain approval.
- The preview is not the final 1920×1080 website master.
