import caching
import time
from typing import Optional

caching.set_cache_dir("_cache_test")

@caching.cached_computation(output_dirs=["output_dir"])
def my_cached_sum(a: float, b: float, output_dir: Optional[str] = None) -> None:
    res = a + b
    time.sleep(5)
    open(output_dir + "/result.txt", "w").write(str(res))

output_path = my_cached_sum(a=1, b=2)["output_dir"] + "/result.txt" # slow
res = float(open(output_path, "r").read())
print(f"res = {res}")

output_path = my_cached_sum(a=1, b=2)["output_dir"] + "/result.txt" # fast
res = float(open(output_path, "r").read())
print(f"res = {res}")
