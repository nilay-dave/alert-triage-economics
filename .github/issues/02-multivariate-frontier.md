# Compute the frontier for two signals at once
labels: enhancement

One signal per rule. Real tuning usually combines conditions: raise the distance
threshold and exclude a service account, lower the entropy bar but only outside
business hours.

With two signals the frontier is a surface rather than a curve, and the useful
output is its Pareto front: the set of threshold pairs where no other pair
removes more volume at the same detection cost.

## What to do

- Accept a corpus with several signal columns per rule.
- Compute the Pareto front over the threshold grid rather than a single curve.
- Report the front, and the volume removable at zero loss along it, which will be strictly better than either signal alone.

## The hard part

The bootstrap cost multiplies with the grid. The existing noise cap helps, but
the honest answer may be a coarser grid with the resolution stated rather than a
fine one that takes an hour.

## Why this is the most requested thing

It is what a tuning engineer actually does. The single signal frontier is the
simplification that made v1 shippable.
