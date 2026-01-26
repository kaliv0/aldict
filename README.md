<p align="center">
  <img src="https://github.com/kaliv0/aldict/blob/main/assets/alter-ego.jpg?raw=true" width="250" alt="Alter Ego">
</p>

---
# Aldict

[![tests](https://img.shields.io/github/actions/workflow/status/kaliv0/aldict/ci.yml)](https://github.com/kaliv0/aldict/actions/workflows/ci.yml)
![Python 3.x](https://img.shields.io/badge/python-^3.10-blue?style=flat-square&logo=Python&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/aldict.svg)](https://pypi.org/project/aldict/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](https://github.com/kaliv0/aldict/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/aldict)](https://pepy.tech/projects/aldict)

Multi-key dictionary, supports adding and manipulating key-aliases pointing to shared values

---
## How to use

- initialize with aliases
<br>(one-liner with <i>aliases</i> dict mapping <i>original key</i> to <i>alias keys</i>)
```python
ad = AliasDict({"a": 1, "b": 2}, aliases={"a": ["aa", "aaa"], "b": "bb"})
assert ad["a"] == ad["aa"] == ad["aaa"] == 1
assert ad["b"] == ad["bb"] == 2
```
- add_alias
<br>(pass <i>key</i> as first parameter and <i>alias(es)</i> as variadic params, list or tuple)
```python
ad = AliasDict({"a": 1, "b": 2})
ad.add_alias("a", "aa")
ad.add_alias("b", "bb", "Bbb")
ad.add_alias("a", ["aaa", "aaaa"])  
ad.add_alias("b", ("bbb",))  

assert ad["a"] == ad["aa"] == ad["aaa"] == ad["aaaa"] == 1
assert ad["b"] == ad["bb"] == ad["Bbb"] == ad["bbb"] == 2
```
- remove_alias
<br>(pass <i>alias(es)</i> to be removed as variadic params, list or tuple)
```python
ad.remove_alias("aa")
ad.remove_alias("bb", "Bbb")
ad.remove_alias(["aaa", "aaaa"])  
ad.remove_alias(("bbb",))  
assert len(ad.aliases()) == 0
```
- clear_aliases
<br>(remove all <i>aliases</i> at once)
```python
ad.clear_aliases()
assert len(ad.aliases()) == 0
```
- update alias
<br>(point <i>alias</i> to different <i>key</i>)
```python
ad = AliasDict({"a": 1, "b": 2})
ad.add_alias("a", "ab")
assert list(ad.items()) == [('a', 1), ('b', 2), ('ab', 1)]

ad.add_alias("b", "ab")
assert list(ad.items()) == [('a', 1), ('b', 2), ('ab', 2)]
```
- read all aliases
```python
ad = AliasDict({"a": 1, "b": 2})
ad.add_alias("a", "aa")
ad.add_alias("b", "bb", "B")
ad.add_alias("a", "ab", "A")
assert list(ad.aliases()) == ['aa', 'bb', 'B', 'ab', 'A']
```
- keys_with_aliases
<br>(read <i>keys</i> with corresponding <i>alias(es)</i>)
```python
assert dict(ad.keys_with_aliases()) == {'a': ['aa', 'ab', 'A'], 'b': ['bb', 'B']}
```
- read dictviews
<br>(<i>dict.keys()</i> and <i>dict.items()</i> include <i>aliased</i> versions)
```python
ad = AliasDict({"x": 10, "y": 20})
ad.add_alias("x", "Xx")
ad.add_alias("y", "Yy", "xyz")

ad.keys()
ad.values()
ad.items()

# dict_keys(['x', 'y', 'Xx', 'Yy', 'xyz'])
# dict_values([10, 20])
# dict_items([('x', 10), ('y', 20), ('Xx', 10), ('Yy', 20), ('xyz', 20)])
```
- remove key and aliases
```python
ad.pop("y")
assert list(ad.items()) == [('x', 10), ('Xx', 10)]
```
- origin_len
<br>(get original dict <i>length</i> without aliases)
```python
ad = AliasDict({"a": 1, "b": 2})
ad.add_alias("a", "aa")
assert list(ad.keys()) == ["a", "b", "aa"]
assert len(ad) == 3
assert ad.origin_len() == 2
```
- origin_keys
<br>(get original <i>keys</i> only)
```python
assert list(ad.origin_keys()) == ['x', 'y']
```
- origin_key
<br>(get original <i>key</i> for an <i>alias</i>)
```python
ad = AliasDict({"a": 1, "b": 2})
ad.add_alias("a", "aa")
assert ad.origin_key("aa") == "a"
assert ad.origin_key("a") is None  # not an alias
```
- is_alias
<br>(check if <i>key</i> is an <i>alias</i>)
```python
ad = AliasDict({"a": 1, "b": 2})
ad.add_alias("a", "aa")
assert ad.is_alias("aa") is True
assert ad.is_alias("a") is False
```
- has_aliases
<br>(check if <i>key</i> has any <i>aliases</i>)
```python
ad = AliasDict({"a": 1, "b": 2})
ad.add_alias("a", "aa")
assert ad.has_aliases("a") is True
assert ad.has_aliases("b") is False
```
- copy
```python
ad = AliasDict({"a": 1, "b": 2})
ad.add_alias("a", "aa")
ad_copy = ad.copy()
assert ad_copy == ad
assert ad_copy is not ad
```
- merge with | and |= operators
```python
ad1 = AliasDict({"a": 1}, aliases={"a": ["aa"]})
ad2 = AliasDict({"b": 2}, aliases={"b": ["bb"]})

merged = ad1 | ad2
assert merged["aa"] == 1
assert merged["bb"] == 2

ad1 |= {"c": 3}
assert ad1["c"] == 3
```
- fromkeys
```python
ad = AliasDict.fromkeys(["a", "b", "c"], 0, aliases={"a": ["aa"]})
assert ad["a"] == ad["aa"] == 0
```
