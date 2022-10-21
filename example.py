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

def warm_up_cache(num_processes: int) -> None:
    map_args = [(x, y) for x in range(1, 11) for y in range(1, 11)]
    with multiprocessing.Pool(num_processes) as pool:
        pool.starmap(sum, map_args)

if __name__ == "__main__":
    warm_up_cache(num_processes=4)
