import discord
from typing import List, Set, Dict, Any, Optional, Callable, Union


# DataGroups: a class with different operations on lists, sets, dictionaries, etc...
class DataGroups():
    FIRST_ARR = 1
    SECOND_ARR = 2
    BOTH_ARR = 0

    #lst_comp(cls, a, b) Compares if the values in 'a' and 'b' are the same
    # requires: all elements in 'a' have the same type
    #           all elements in 'b' have the same type
    #           the type for the elements in 'a' has the same type as the elements in 'b'
    @classmethod
    def lst_comp(cls, a: List[Any], b: List[Any]) -> bool:
        same = True
        len_a = len(a)
        len_b = len(b)

        if (len_a == len_b):
            for i in range(len_a):
                if (a != b):
                    same = False
                    break
        else:
            same = False

        return same


    # lst_common(cls, a, b, equal) Finds the entries in 'a' and 'b' that are in
    #   common
    # requires: all elements in 'a' have the same type
    #           all elements in 'b' have the same type
    #           the type for the elements in 'a' has the same type as the elements in 'b'
    @classmethod
    def lst_common(cls, a: List[Any], b: List[Any], equal: Optional[Callable[[Any, Any], bool]] = None) -> List[Any]:
        common = []

        for a_i in a:
            for b_i in b:
                eq = False
                try:
                    if (equal is not None):
                        eq = equal(a_i, b_i)
                    else:
                        eq = (a_i == b_i)
                except:
                    pass

                if (eq):
                    common.append(a_i)

        return common


    # lst_diff(cls, a, b, equal, result) Finds the difference between the lists
    #   'a' and 'b'
    # requires: all elements in 'a' have the same type
    #           all elements in 'b' have the same type
    #           the type for the elements in 'a' has the same type as the elements in 'b'
    #           'result' is either FIRST_ARR, SECOND_ARR or BOTH_ARR
    @classmethod
    def lst_diff(cls, a: List[Any], b: List[Any], equal: Optional[Callable[[Any, Any], bool]] = None,
                 result: int = BOTH_ARR) -> Union[Dict[str, List[Any]], List[Any]]:
        a_lst = list(a)
        b_lst = list(b)
        common = cls.lst_common(a_lst, b_lst, equal = equal)
        a_len = len(a)
        b_len = len(b)
        c_len = len(common)

        i = 0
        j = 0

        while (i < c_len):
            j = 0
            while (j < a_len):
                eq = False
                try:
                    if (equal is not None):
                        eq = equal(common[i], a_lst[j])
                    else:
                        eq = (common[i] == a_lst[j])
                except:
                    pass

                if (eq):
                    a_lst.pop(j)
                    a_len -= 1
                else:
                    j += 1

            j = 0
            while (j < b_len):
                eq = False
                try:
                    if (equal is not None):
                        eq = equal(common[i], b_lst[j])
                    else:
                        eq = (common[i] == b_lst[j])
                except:
                    pass

                if (eq):
                    b_lst.pop(j)
                    b_len -= 1
                else:
                    j += 1
            i += 1

        if (result == cls.BOTH_ARR):
            return {"a": a_lst, "b": b_lst}
        elif (result == cls.FIRST_ARR):
            return a_lst
        else:
            return b_lst


    # set_diff(cls, a, b, result) Finds the entries in 'a' and 'b' that are not
    #   in common
    # requires: all elements in 'a' have the same type
    #           all elements in 'b' have the same type
    #           the type for the elements in 'a' has the same type as the elements in 'b'
    #           'result' is either FIRST_ARR, SECOND_ARR or BOTH_ARR
    @classmethod
    def set_diff(cls, a: Set[Any], b: Set[Any], result: int = BOTH_ARR) -> Union[Dict[str, Set[Any]], Set[Any]]:
        a_set = set(a)
        b_set = set(b)

        if (result == cls.BOTH_ARR or result == cls.FIRST_ARR):
            a_diff = a_set.difference(b_set)

        if (result == cls.BOTH_ARR or result == cls.SECOND_ARR):
            b_diff = b_set.difference(a_set)

        a_lst = list(a_diff)
        b_lst = list(b_diff)

        if (result == cls.BOTH_ARR):
            return {"a": a_lst, "b": b_lst}
        elif (result == cls.FIRST_ARR):
            return a_lst
        else:
            return b_lst


    # key_in_dict(cls, dict, key) Checks if a specific 'key' is in 'dict'
    @classmethod
    def key_in_dict(cls, dict: Dict[Any, Any], key: Any) -> bool:
        return (key in dict.keys())


    # get_max(cls, lst, comparison) Gets the largest value from 'lst'
    @classmethod
    def get_max(cls, lst: List[Any], comparison: Optional[Callable[[Any, Any], int]] = None) -> Any:
        if (lst):
            maximum = lst[0]
        else:
            maximum = None

        for e in lst:
            if ((comparison is not None and comparison(e, maximum) > 0) or
                (comparison is None and e > maximum)):
                maximum = e

        return maximum
