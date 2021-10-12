from typing import List, Any, Dict


# AbsFunc: Class for abstract functions
class AbsFunc():
    def __init__(self, func, args: List[Any] = [], kwargs: Dict[str, Any] = {}, is_async: bool = False):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.is_async = is_async


    # run() Runs the abstract function
    def run(self, pre_args: List[Any] = [], pre_kwargs: Dict[str, Any] = {}) -> Any:
        return self.func(*pre_args, *self.args, **pre_kwargs, **self.kwargs)


    # async_run() Asynchronously runs the abstract function
    async def async_run(self, pre_args: List[Any] = [], pre_kwargs: Dict[str, Any] = {}) -> Any:
        return await self.func(*pre_args, *self.args, **pre_kwargs, **self.kwargs)
