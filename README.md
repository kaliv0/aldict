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

- add_alias
<br>(pass <i>key</i> as first parameter and <i>alias(es)</i> as variadic params)
```python
ad = AliasDict({"a": 1, "b": 2})
ad.add_alias("a", "aa")
ad.add_alias("b", "bb", "Bbb")
assert ad["a"] == ad["aa"] == 1
assert ad["b"] == ad["bb"] == ad["Bbb"] == 2
```
- remove_alias
<br>(pass <i>alias(es)</i> to be removed as variadic parameters)
```python
ad.remove_alias("aa")
ad.remove_alias("bb", "Bbb")
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
- aliased_keys
<br>(read <i>keys</i> with corresponding <i>alias(es)</i>)
```python
assert dict(ad.aliased_keys()) == {'a': ['aa', 'ab', 'A'], 'b': ['bb', 'B']}
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
- origin_keys
<br>(get original <i>keys</i> only)
```python
assert list(ad.origin_keys()) == ['x', 'y']
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
