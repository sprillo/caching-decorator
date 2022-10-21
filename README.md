# caching-decorator

This package implements a lightweight, "plug and play" python caching decorator.

## Example usage

Say you have a function like the one below, that adds two numbers:

```
def sum(x: int, y: int):
    return x + y
```

This is a very simple function, but it suffices to demonstrate how the caching decorator works. To enhance this function with caching, we simply import the caching module, set the cache directory, and decorate the function with caching, as follows:

```
import caching

caching.set_cache_dir("_cache")

@caching.cached()
def sum(x: int, y: int) -> int:
    return x + y
```

After doing this, every time that the function `sum` is called, the decorator will first determine if the function has been called with these arguments before. If it has, it will retrieve the result from disk (stored in the caching directory, `"_cache"` in this case), avoiding repeated computation. Otherwise, the `sum` function will be called and the result will be written to the cache (thus avoiding future instances of the computation).

## Implementation details

Internally, the caching decorator works by hashing the function's argument names and values into a hexadecimal string of length 128. This determines where the output of the function should be stored.

## What functions can I cache?

The requirements for a function to be able to be decorated with caching are the following:
- The arguments to the function must have an injective `__str__` representation.
- The result of the function must be pickle-able.
- The function must be a deterministic function of its inputs.
- Moreover, the function must be referentially transparent. Informally, this means that it must always return the same result no matter when and where it is called, and it must not affect any global state. This is guaranteed by writing code in a functional style.
- All cached functions must have different names.

## What functions should I _not_ cache?

Examples of functions that are not suitable for caching are:
1. A function that takes a large object as an argument, such as a 1000 x 1000 pandas DataFrame.
2. A function that modifies global state such as appending a value into a global list.
3. A function that behaves randomly.

To make the respective (counter-)examples above suitable for caching, common strategies are:
1. Instead of passing in a large pandas DataFrame object, use string names to refer to datasets, e.g. instead of:
```
def process_dataset(df: pd.DataFrame):
    ...
```
consider:
```
def process_dataset(dataset_name: str):
    df = read_dataset(dataset_name)
    ...
```
2. Do not use a global state to begin with.
3. Pass in the random seed as an argument to the function, and use the random seed within the function to dictate randomness. The function is now deterministic. Note that to avoid modifying global state, the right way to use random seeds locally is via local random number generators as in `rng = numpy.random.default_rng(random_seed)` rather than `numpy.random.seed(random_seed)` (the latter sets the _global_ seed, and is thus bad practice).


## Additional "free" functionality

The caching decorator implements the following additional functionality for "free":
- **Preventing data corruption**: caching is performed atomically. If your program gets killed during execution while writing to the cache (for example, due to power loss), the caching decorator will notice this the next time the function is called with the same arguments and re-run the computation instead of attempting to access corrupted data. Internally, this is implemented via the use of success tokens.
- **Portability of the cache**: If you need to migrate your data to another machine, or share your results with a collaborator, you can just copy the cache over. Since the cache uses relative paths, it is guaranteed to work on another machine.

## Additional use cases

The caching decorator allows the exclusion of arguments via the `exclude` argument. This is a very common use case, for example when a function has arguments such as `verbose`, or `number_of_processes` (for parallelization). In this case, the function is not a function of these arguments, so it is desirable to exclude them from the signature for the purpose of caching. In our previous example, we would do as follows:

```
import caching

caching.set_cache_dir("_cache")

@caching.cached(
    exclude=["number_of_cores", "verbose"]
)
def sum(x: int, y: int, number_of_cores: int, verbose: bool = False) -> int:
    if verbose:
        print(f"Adding up {x} and {y}")
    return x + y
```

Another (less common) use case involves *extending* a cached function with new arguments in a backwards-compatible way. Suppose that we want to extend the `sum` function to add three numbers x, y, z instead of two. We could naively do the following:

```
import caching

caching.set_cache_dir("_cache")

@caching.cached(
    exclude=["number_of_cores", "verbose"]
)
def sum(x: int, y: int, number_of_cores: int, verbose: bool = False, z: int = 0) -> int:
    if verbose:
        print(f"Adding up {x}, {y}, and {z}")
    return x + y + z
```

Doing this would cause all the old values in the cache to be inaccessible since now `z` will get hashed together with `x` and `y`. This can be avoided by using the `exclude_if_default` argument:

```
import caching

caching.set_cache_dir("_cache")

@caching.cached(
    exclude=["number_of_cores", "verbose"],
    exclude_if_default=["z"],
)
def sum(x: int, y: int, number_of_cores: int, verbose: bool = False, z: int = 0) -> int:
    if verbose:
        print(f"Adding up {x}, {y}, and {z}")
    return x + y + z
```

In this case, `z` will not be hashed as part of the function signature if it equals 0, providing backwards compatible cache data (none of the old cached values will be lost).

## Set the logging level

The logging level of the `caching` module can be set with the `caching.set_log_level` function. If you want the highest verbosity, use `caching.set_log_level(9)`, so:

```
import caching

caching.set_cache_dir("_cache")
caching.set_log_level(9)

@caching.cached(
    exclude=["number_of_cores", "verbose"],
    exclude_if_default=["z"],
)
def sum(x: int, y: int, number_of_cores: int, verbose: bool = False, z: int = 0) -> int:
    if verbose:
        print(f"Adding up {x}, {y}, and {z}")
    return x + y + z
```

## Multiprocessing

A final common use case involves making function calls in parallel to "warm up" or "populate" the cache, such as when running experiments overnight. This is safe to do provided that all the parallel function calls have disjoint parameter calls. Otherwise, a race condition may occur where two processes try to write the same value to the cache. In this case, the second process will typically crash when the file goes into write-only mode.

As a concrete example, suppose that we want to "warm up" the cache overnight by computing the sum of all pairs of numbers between 1 and 10. We could do this as follows (as in file `example.py`):

```
import multiprocessing

import caching

caching.set_cache_dir("_cache")
caching.set_log_level(9)

@caching.cached(
    exclude=["verbose"],
    exclude_if_default=["z"],
)
def sum(x: int, y: int, verbose: bool = False, z: int = 0) -> int:
    if verbose:
        print(f"Adding up {x}, {y}, and {z}")
    return x + y + z

def warm_up_cache(num_processes: int):
    map_args = [(x, y) for x in range(1, 11) for y in range(1, 11)]
    with multiprocessing.Pool(num_processes) as pool:
        pool.starmap(sum, map_args)

if __name__ == "__main__":
    warm_up_cache(num_processes=4)
```